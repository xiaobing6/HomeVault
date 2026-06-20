from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from datetime import date, datetime, timedelta, timezone

import pytest
from fastapi import HTTPException
from sqlalchemy import event, select
from sqlalchemy.orm import Session

from app.models.auth import User
from app.models.configuration import Category, HomeSpace, ItemStatus, LocationNode, Residence
from app.models.inventory import Item, ItemLoan
from app.models.reminders import Reminder
from app.schemas.inventory import ItemListQuery, LoanCreate, LoanReturn
from app.schemas.reminders import ReminderCreate, ReminderListQuery, ReminderUpdate
from app.services.inventory import create_loan, list_items, return_loan
from app.services import reminders as reminder_service
from app.services.reminders import (
    archive_reminder,
    complete_reminder,
    create_reminder,
    dismiss_reminder,
    get_reminder_detail,
    list_reminders,
    reopen_reminder,
    server_today,
    update_reminder,
)


FIXED_TODAY = date(2026, 6, 20)


@contextmanager
def count_select_statements(db_session: Session) -> Iterator[list[str]]:
    statements: list[str] = []

    def before_cursor_execute(conn, cursor, statement, parameters, context, executemany) -> None:
        if statement.lstrip().upper().startswith("SELECT"):
            statements.append(statement)

    bind = db_session.get_bind()
    event.listen(bind, "before_cursor_execute", before_cursor_execute)
    try:
        yield statements
    finally:
        event.remove(bind, "before_cursor_execute", before_cursor_execute)


def test_server_today_uses_utc_date(monkeypatch: pytest.MonkeyPatch) -> None:
    class FixedDateTime(datetime):
        @classmethod
        def now(cls, tz=None):
            assert tz is timezone.utc
            return cls(2099, 1, 2, 3, 4, tzinfo=tz)

    monkeypatch.setattr(reminder_service, "datetime", FixedDateTime)

    assert reminder_service.server_today() == date(2099, 1, 2)


@pytest.fixture()
def reminder_seed(db_session: Session) -> dict[str, object]:
    user = User(id=10, username="editor", password_hash="hash", display_name="Editor")
    home = HomeSpace(name="Home")
    residence = Residence(name="Main", home_space=home)
    location = LocationNode(residence=residence, name="Shelf", node_type="shelf")
    category = Category(code="documents", name="Documents")
    status = ItemStatus(code="in_stock", name="In stock", semantic="in_inventory", is_system=True)
    item = Item(name="Passport", category=category, status=status, location_node=location)
    db_session.add_all([user, item])
    db_session.commit()
    return {"user": user, "item": item}


def test_create_list_update_complete_dismiss_reopen_and_archive_reminder(
    db_session: Session,
    reminder_seed: dict[str, object],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(reminder_service, "server_today", lambda: FIXED_TODAY)
    item = reminder_seed["item"]
    detail = create_reminder(
        db_session,
        ReminderCreate(title="Check passport", item_id=item.id, due_date=FIXED_TODAY + timedelta(days=2)),
        actor_id=10,
    )
    listed = list_reminders(db_session, ReminderListQuery(upcoming_days=7))
    updated = update_reminder(db_session, detail.id, ReminderUpdate(title="Check passport folder"), actor_id=10)
    completed = complete_reminder(db_session, detail.id, actor_id=10)
    reopened = reopen_reminder(db_session, detail.id)
    dismissed = dismiss_reminder(db_session, detail.id, actor_id=10)
    archived = archive_reminder(db_session, detail.id)

    assert detail.status == "pending"
    assert detail.due_state == "upcoming"
    assert listed.total == 1
    assert updated.title == "Check passport folder"
    assert completed.status == "done"
    assert completed.completed_by_user_id == 10
    assert reopened.status == "pending"
    assert dismissed.status == "dismissed"
    assert archived.archived_at is not None


def test_overdue_filter_uses_fixed_service_date(
    db_session: Session,
    reminder_seed: dict[str, object],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(reminder_service, "server_today", lambda: FIXED_TODAY)
    item = reminder_seed["item"]
    create_reminder(
        db_session,
        ReminderCreate(title="Late", item_id=item.id, due_date=FIXED_TODAY - timedelta(days=1)),
        actor_id=10,
    )
    create_reminder(
        db_session,
        ReminderCreate(title="Soon", item_id=item.id, due_date=FIXED_TODAY + timedelta(days=1)),
        actor_id=10,
    )

    listed = list_reminders(db_session, ReminderListQuery(overdue=True))

    assert listed.total == 1
    assert listed.items[0].title == "Late"
    assert listed.items[0].due_state == "overdue"


def test_list_reminders_returns_summaries_without_inventory_graph_overfetch(
    db_session: Session,
    reminder_seed: dict[str, object],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(reminder_service, "server_today", lambda: FIXED_TODAY)
    item = reminder_seed["item"]
    loan = ItemLoan(
        item=item,
        borrower_name="Taylor",
        expected_return_date=FIXED_TODAY + timedelta(days=3),
    )
    reminder = Reminder(
        title="Return followup",
        description="",
        source_type="loan_return",
        item=item,
        loan=loan,
        due_date=FIXED_TODAY + timedelta(days=3),
        status="pending",
        priority="normal",
        created_by_user_id=10,
    )
    db_session.add(reminder)
    db_session.commit()
    db_session.expire_all()

    with count_select_statements(db_session) as statements:
        listed = list_reminders(db_session, ReminderListQuery())

    assert listed.total == 1
    assert listed.items[0].item is not None
    assert listed.items[0].item.name == "Passport"
    assert listed.items[0].loan is not None
    assert listed.items[0].loan.borrower_name == "Taylor"
    assert len(statements) <= 5


def test_search_matches_linked_item_name(db_session: Session, reminder_seed: dict[str, object]) -> None:
    item = reminder_seed["item"]
    create_reminder(
        db_session,
        ReminderCreate(title="Renew document", description="Check folder", item_id=item.id),
        actor_id=10,
    )

    listed = list_reminders(db_session, ReminderListQuery(search="Passport"))

    assert listed.total == 1
    assert listed.items[0].title == "Renew document"
    assert listed.items[0].item is not None
    assert listed.items[0].item.name == "Passport"


def test_create_rejects_archived_item(db_session: Session, reminder_seed: dict[str, object]) -> None:
    item = reminder_seed["item"]
    item.is_archived = True
    db_session.commit()

    with pytest.raises(HTTPException) as exc_info:
        create_reminder(db_session, ReminderCreate(title="Nope", item_id=item.id), actor_id=10)

    assert exc_info.value.status_code == 400


def test_complete_reminder_preserves_first_completion_metadata(
    db_session: Session,
    reminder_seed: dict[str, object],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    item = reminder_seed["item"]
    detail = create_reminder(db_session, ReminderCreate(title="Check passport", item_id=item.id), actor_id=10)
    first_now = datetime(2026, 6, 20, 1, 0)
    second_now = datetime(2026, 6, 20, 2, 0)
    clock = iter([first_now, second_now])
    monkeypatch.setattr(reminder_service, "utcnow", lambda: next(clock))

    complete_reminder(db_session, detail.id, actor_id=10)
    complete_reminder(db_session, detail.id, actor_id=None)
    db_session.expire_all()
    saved = db_session.get(Reminder, detail.id)

    assert saved is not None
    assert saved.status == "done"
    assert saved.completed_at == first_now
    assert saved.completed_by_user_id == 10


def test_dismiss_reminder_preserves_first_dismissal_metadata(
    db_session: Session,
    reminder_seed: dict[str, object],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    item = reminder_seed["item"]
    detail = create_reminder(db_session, ReminderCreate(title="Check passport", item_id=item.id), actor_id=10)
    first_now = datetime(2026, 6, 20, 1, 0)
    second_now = datetime(2026, 6, 20, 2, 0)
    clock = iter([first_now, second_now])
    monkeypatch.setattr(reminder_service, "utcnow", lambda: next(clock))

    dismiss_reminder(db_session, detail.id, actor_id=10)
    dismiss_reminder(db_session, detail.id, actor_id=None)
    db_session.expire_all()
    saved = db_session.get(Reminder, detail.id)

    assert saved is not None
    assert saved.status == "dismissed"
    assert saved.dismissed_at == first_now
    assert saved.dismissed_by_user_id == 10


def test_archive_reminder_preserves_first_archive_timestamp(
    db_session: Session,
    reminder_seed: dict[str, object],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    item = reminder_seed["item"]
    detail = create_reminder(db_session, ReminderCreate(title="Check passport", item_id=item.id), actor_id=10)
    first_now = datetime(2026, 6, 20, 1, 0)
    second_now = datetime(2026, 6, 20, 2, 0)
    clock = iter([first_now, second_now])
    monkeypatch.setattr(reminder_service, "utcnow", lambda: next(clock))

    archive_reminder(db_session, detail.id)
    archive_reminder(db_session, detail.id)
    db_session.expire_all()
    saved = db_session.get(Reminder, detail.id)

    assert saved is not None
    assert saved.archived_at == first_now


def test_loan_with_expected_return_date_creates_and_completes_reminder(
    db_session: Session,
    reminder_seed: dict[str, object],
) -> None:
    item = reminder_seed["item"]
    expected_return_date = server_today() + timedelta(days=3)

    detail = create_loan(
        db_session,
        item.id,
        LoanCreate(borrower_name="Taylor", expected_return_date=expected_return_date),
        actor_id=10,
    )
    loan_id = detail.loans[0].id
    reminder = db_session.scalar(select(Reminder).where(Reminder.loan_id == loan_id))

    assert reminder is not None
    assert reminder.source_type == "loan_return"
    assert reminder.item_id == item.id
    assert reminder.due_date == expected_return_date
    assert reminder.status == "pending"

    returned = return_loan(
        db_session,
        item.id,
        loan_id,
        LoanReturn(location_node_id=item.location_node_id, target_status_id=item.status_id),
        actor_id=10,
    )
    db_session.refresh(reminder)

    assert returned.loans[0].returned_at is not None
    assert reminder.status == "done"
    assert reminder.completed_by_user_id == 10


def test_item_list_reminder_filters(db_session: Session, reminder_seed: dict[str, object]) -> None:
    item = reminder_seed["item"]
    today = server_today()
    create_reminder(
        db_session,
        ReminderCreate(title="Late", item_id=item.id, due_date=today - timedelta(days=1)),
        actor_id=10,
    )

    overdue = list_items(db_session, ItemListQuery(has_overdue_reminder=True))
    upcoming = list_items(db_session, ItemListQuery(has_upcoming_reminder=True, reminder_upcoming_days=7))
    pending = list_items(db_session, ItemListQuery(has_pending_reminder=True))

    assert overdue.total == 1
    assert overdue.items[0].id == item.id
    assert upcoming.total == 0
    assert pending.total == 1
