from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

from fastapi import HTTPException, status
from sqlalchemy import case, func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, raiseload, selectinload

from app.core.errors import bad_request
from app.models.inventory import Item, ItemLoan
from app.models.reminders import Reminder
from app.schemas.reminders import (
    ReminderCreate,
    ReminderDetailResponse,
    ReminderItemSummary,
    ReminderListQuery,
    ReminderListResponse,
    ReminderLoanSummary,
    ReminderSummaryResponse,
    ReminderUpdate,
)

try:
    from app.core.errors import not_found
except ImportError:

    def not_found(message: str) -> HTTPException:
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={"message": message})


REMINDER_STATUS_PENDING = "pending"
REMINDER_STATUS_DONE = "done"
REMINDER_STATUS_DISMISSED = "dismissed"
REMINDER_SOURCE_MANUAL = "manual"
REMINDER_SOURCE_LOAN_RETURN = "loan_return"
REMINDER_PRIORITIES = {"low", "normal", "high"}
DEFAULT_UPCOMING_DAYS = 7
MAX_UPCOMING_DAYS = 90


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def server_today() -> date:
    return datetime.now(timezone.utc).date()


def commit_or_bad_request(db: Session, message: str) -> None:
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise bad_request(message) from exc


def require_reminder(db: Session, reminder_id: int) -> Reminder:
    reminder = db.scalar(
        select(Reminder)
        .where(Reminder.id == reminder_id)
        .options(raiseload("*"))
    )
    if reminder is None:
        raise not_found("提醒不存在")
    return reminder


def require_editable_reminder(db: Session, reminder_id: int) -> Reminder:
    reminder = require_reminder(db, reminder_id)
    if reminder.archived_at is not None:
        raise bad_request("已归档的提醒不能操作")
    return reminder


def require_active_item(db: Session, item_id: int) -> Item:
    item = db.get(Item, item_id)
    if item is None or item.is_archived:
        raise bad_request("关联物品不存在")
    return item


def validate_priority(priority: str) -> str:
    normalized_priority = priority.strip()
    if normalized_priority not in REMINDER_PRIORITIES:
        raise bad_request("提醒优先级不合法")
    return normalized_priority


def compute_due_state(
    status: str,
    due_date: date | None = None,
    remind_at: date | None = None,
    today: date | None = None,
    upcoming_days: int = DEFAULT_UPCOMING_DAYS,
) -> str:
    current_date = today or server_today()
    if status == REMINDER_STATUS_DONE:
        return REMINDER_STATUS_DONE
    if status == REMINDER_STATUS_DISMISSED:
        return REMINDER_STATUS_DISMISSED
    if due_date is not None and due_date < current_date:
        return "overdue"

    window_end = current_date + timedelta(days=upcoming_days)
    if due_date is not None and due_date <= window_end:
        return "upcoming"
    if remind_at is not None and remind_at <= current_date:
        return "upcoming"
    if remind_at is not None and remind_at <= window_end:
        return "upcoming"
    if due_date is not None or remind_at is not None:
        return "scheduled"
    return "none"


def create_reminder(
    db: Session,
    payload: ReminderCreate,
    actor_id: int | None = None,
) -> ReminderDetailResponse:
    title = payload.title.strip()
    if title == "":
        raise bad_request("提醒标题不能为空")
    priority = validate_priority(payload.priority)
    if payload.item_id is not None:
        require_active_item(db, payload.item_id)

    reminder = Reminder(
        title=title,
        description=payload.description,
        source_type=REMINDER_SOURCE_MANUAL,
        item_id=payload.item_id,
        due_date=payload.due_date,
        remind_at=payload.remind_at,
        status=REMINDER_STATUS_PENDING,
        priority=priority,
        created_by_user_id=actor_id,
    )
    db.add(reminder)
    commit_or_bad_request(db, "提醒保存失败")
    return get_reminder_detail(db, reminder.id)


def sync_loan_return_reminder(
    db: Session,
    *,
    item: Item,
    loan: ItemLoan,
    actor_id: int | None,
) -> None:
    if loan.expected_return_date is None:
        return
    reminder = db.scalar(
        select(Reminder).where(
            Reminder.source_type == REMINDER_SOURCE_LOAN_RETURN,
            Reminder.loan_id == loan.id,
            Reminder.archived_at.is_(None),
        )
    )
    if reminder is None:
        reminder = Reminder(
            title=f"Return {item.name}",
            description=loan.loan_note,
            source_type=REMINDER_SOURCE_LOAN_RETURN,
            item_id=item.id,
            loan_id=loan.id,
            status=REMINDER_STATUS_PENDING,
            priority="normal",
            created_by_user_id=actor_id,
        )
        db.add(reminder)
    reminder.item_id = item.id
    reminder.due_date = loan.expected_return_date
    reminder.remind_at = loan.expected_return_date
    reminder.updated_at = utcnow()


def complete_loan_return_reminder(
    db: Session,
    *,
    loan_id: int,
    actor_id: int | None,
) -> None:
    reminder = db.scalar(
        select(Reminder).where(
            Reminder.source_type == REMINDER_SOURCE_LOAN_RETURN,
            Reminder.loan_id == loan_id,
            Reminder.status == REMINDER_STATUS_PENDING,
            Reminder.archived_at.is_(None),
        )
    )
    if reminder is None:
        return
    now = utcnow()
    reminder.status = REMINDER_STATUS_DONE
    reminder.completed_at = now
    reminder.completed_by_user_id = actor_id
    reminder.updated_at = now


def get_reminder_detail(db: Session, reminder_id: int) -> ReminderDetailResponse:
    reminder = load_reminder_for_response(db, reminder_id)
    if reminder is None:
        raise not_found("提醒不存在")
    return build_reminder_detail_response(reminder)


def list_reminders(db: Session, query: ReminderListQuery) -> ReminderListResponse:
    today = server_today()
    stmt = select(Reminder)
    if not query.include_archived:
        stmt = stmt.where(Reminder.archived_at.is_(None))
    if query.status is not None:
        stmt = stmt.where(Reminder.status == query.status)
    if query.source_type is not None:
        stmt = stmt.where(Reminder.source_type == query.source_type)
    if query.item_id is not None:
        stmt = stmt.where(Reminder.item_id == query.item_id)
    if query.loan_id is not None:
        stmt = stmt.where(Reminder.loan_id == query.loan_id)
    if query.overdue is True:
        stmt = stmt.where(
            Reminder.status == REMINDER_STATUS_PENDING,
            Reminder.due_date.is_not(None),
            Reminder.due_date < today,
        )
    elif query.overdue is False:
        stmt = stmt.where(
            or_(
                Reminder.status != REMINDER_STATUS_PENDING,
                Reminder.due_date.is_(None),
                Reminder.due_date >= today,
            )
        )
    if query.upcoming_days is not None:
        window_end = today + timedelta(days=query.upcoming_days)
        stmt = stmt.where(
            Reminder.status == REMINDER_STATUS_PENDING,
            or_(Reminder.due_date.is_(None), Reminder.due_date >= today),
            or_(
                Reminder.due_date <= window_end,
                Reminder.remind_at <= window_end,
            ),
        )
    if query.search:
        search = f"%{query.search.strip()}%"
        if search != "%%":
            stmt = stmt.where(
                or_(
                    Reminder.title.ilike(search),
                    Reminder.description.ilike(search),
                    Reminder.item.has(Item.name.ilike(search)),
                )
            )

    total = db.scalar(select(func.count()).select_from(stmt.order_by(None).subquery())) or 0
    stmt = (
        apply_list_sort(stmt, query.sort)
        .options(*reminder_response_options())
        .limit(query.page_size)
        .offset((query.page - 1) * query.page_size)
    )
    reminders = db.scalars(stmt).unique().all()
    return ReminderListResponse(
        items=[build_reminder_summary_response(reminder) for reminder in reminders],
        total=total,
        page=query.page,
        page_size=query.page_size,
    )


def update_reminder(
    db: Session,
    reminder_id: int,
    payload: ReminderUpdate,
    actor_id: int | None = None,
) -> ReminderDetailResponse:
    reminder = require_editable_reminder(db, reminder_id)
    fields = payload.model_fields_set
    if reminder.source_type == REMINDER_SOURCE_LOAN_RETURN and ({"item_id", "due_date"} & fields):
        raise bad_request("借出提醒的关联借出和到期日由借出流程维护")

    if "title" in fields and payload.title is not None:
        title = payload.title.strip()
        if title == "":
            raise bad_request("提醒标题不能为空")
        reminder.title = title
    if "description" in fields:
        reminder.description = payload.description or ""
    if "item_id" in fields:
        if payload.item_id is not None:
            require_active_item(db, payload.item_id)
        reminder.item_id = payload.item_id
    if "due_date" in fields:
        reminder.due_date = payload.due_date
    if "remind_at" in fields:
        reminder.remind_at = payload.remind_at
    if "priority" in fields and payload.priority is not None:
        reminder.priority = validate_priority(payload.priority)

    commit_or_bad_request(db, "提醒保存失败")
    return get_reminder_detail(db, reminder.id)


def complete_reminder(
    db: Session,
    reminder_id: int,
    actor_id: int | None = None,
) -> ReminderDetailResponse:
    reminder = require_editable_reminder(db, reminder_id)
    if reminder.status != REMINDER_STATUS_DONE:
        reminder.status = REMINDER_STATUS_DONE
        reminder.completed_at = utcnow()
        reminder.completed_by_user_id = actor_id
        reminder.dismissed_at = None
        reminder.dismissed_by_user_id = None
    commit_or_bad_request(db, "提醒保存失败")
    return get_reminder_detail(db, reminder.id)


def dismiss_reminder(
    db: Session,
    reminder_id: int,
    actor_id: int | None = None,
) -> ReminderDetailResponse:
    reminder = require_editable_reminder(db, reminder_id)
    if reminder.status != REMINDER_STATUS_DISMISSED:
        reminder.status = REMINDER_STATUS_DISMISSED
        reminder.dismissed_at = utcnow()
        reminder.dismissed_by_user_id = actor_id
        reminder.completed_at = None
        reminder.completed_by_user_id = None
    commit_or_bad_request(db, "提醒保存失败")
    return get_reminder_detail(db, reminder.id)


def reopen_reminder(db: Session, reminder_id: int) -> ReminderDetailResponse:
    reminder = require_editable_reminder(db, reminder_id)
    reminder.status = REMINDER_STATUS_PENDING
    reminder.completed_at = None
    reminder.completed_by_user_id = None
    reminder.dismissed_at = None
    reminder.dismissed_by_user_id = None
    commit_or_bad_request(db, "提醒保存失败")
    return get_reminder_detail(db, reminder.id)


def archive_reminder(db: Session, reminder_id: int) -> ReminderDetailResponse:
    reminder = require_reminder(db, reminder_id)
    if reminder.archived_at is None:
        reminder.archived_at = utcnow()
    commit_or_bad_request(db, "提醒保存失败")
    return get_reminder_detail(db, reminder.id)


def reminder_response_options() -> tuple:
    return (
        raiseload("*"),
        selectinload(Reminder.item)
        .load_only(Item.id, Item.name, Item.is_archived)
        .raiseload("*"),
        selectinload(Reminder.loan)
        .load_only(ItemLoan.id, ItemLoan.borrower_name, ItemLoan.expected_return_date, ItemLoan.returned_at)
        .raiseload("*"),
    )


def load_reminder_for_response(db: Session, reminder_id: int) -> Reminder | None:
    return db.scalar(
        select(Reminder)
        .where(Reminder.id == reminder_id)
        .options(*reminder_response_options())
    )


def apply_list_sort(stmt, sort: str):
    if sort == "due_desc":
        return stmt.order_by(Reminder.due_date.is_(None), Reminder.due_date.desc(), Reminder.id.desc())
    if sort == "created_asc":
        return stmt.order_by(Reminder.created_at.asc(), Reminder.id.asc())
    if sort == "created_desc":
        return stmt.order_by(Reminder.created_at.desc(), Reminder.id.desc())
    if sort == "updated_asc":
        return stmt.order_by(Reminder.updated_at.asc(), Reminder.id.asc())
    if sort == "updated_desc":
        return stmt.order_by(Reminder.updated_at.desc(), Reminder.id.desc())
    if sort == "priority_desc":
        priority_rank = case(
            (Reminder.priority == "high", 0),
            (Reminder.priority == "normal", 1),
            (Reminder.priority == "low", 2),
            else_=3,
        )
        return stmt.order_by(
            priority_rank,
            Reminder.due_date.is_(None),
            Reminder.due_date.asc(),
            Reminder.id.asc(),
        )
    return stmt.order_by(Reminder.due_date.is_(None), Reminder.due_date.asc(), Reminder.id.asc())


def build_reminder_summary_response(reminder: Reminder) -> ReminderSummaryResponse:
    today = server_today()
    return ReminderSummaryResponse(
        id=reminder.id,
        title=reminder.title,
        description=reminder.description,
        source_type=reminder.source_type,
        item_id=reminder.item_id,
        loan_id=reminder.loan_id,
        due_date=reminder.due_date,
        remind_at=reminder.remind_at,
        status=reminder.status,
        priority=reminder.priority,
        due_state=compute_due_state(reminder.status, reminder.due_date, reminder.remind_at, today=today),
        days_until_due=(reminder.due_date - today).days if reminder.due_date is not None else None,
        created_by_user_id=reminder.created_by_user_id,
        completed_by_user_id=reminder.completed_by_user_id,
        dismissed_by_user_id=reminder.dismissed_by_user_id,
        completed_at=reminder.completed_at,
        dismissed_at=reminder.dismissed_at,
        archived_at=reminder.archived_at,
        created_at=reminder.created_at,
        updated_at=reminder.updated_at,
        item=build_reminder_item_summary(reminder),
        loan=build_reminder_loan_summary(reminder),
    )


def build_reminder_detail_response(reminder: Reminder) -> ReminderDetailResponse:
    summary = build_reminder_summary_response(reminder)
    return ReminderDetailResponse(**summary.model_dump())


def build_reminder_item_summary(reminder: Reminder) -> ReminderItemSummary | None:
    if reminder.item is None:
        return None
    return ReminderItemSummary(
        id=reminder.item.id,
        name=reminder.item.name,
        is_archived=reminder.item.is_archived,
    )


def build_reminder_loan_summary(reminder: Reminder) -> ReminderLoanSummary | None:
    if reminder.loan is None:
        return None
    return ReminderLoanSummary(
        id=reminder.loan.id,
        borrower_name=reminder.loan.borrower_name,
        expected_return_date=reminder.loan.expected_return_date,
        returned_at=reminder.loan.returned_at,
    )
