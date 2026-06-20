from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_permission
from app.models.auth import User
from app.schemas.reminders import ReminderCreate, ReminderDetailResponse, ReminderListQuery, ReminderListResponse, ReminderUpdate
from app.services.reminders import (
    archive_reminder,
    complete_reminder,
    create_reminder,
    dismiss_reminder,
    get_reminder_detail,
    list_reminders,
    reopen_reminder,
    update_reminder,
)

READ_PERMISSION = "items:view"
EDIT_PERMISSION = "items:edit"

router = APIRouter(tags=["reminders"])


@router.get("/reminders", response_model=ReminderListResponse)
def reminders(
    query: ReminderListQuery = Depends(),
    db: Session = Depends(get_db),
    user: User = Depends(require_permission(READ_PERMISSION)),
) -> ReminderListResponse:
    return list_reminders(db, query)


@router.post("/reminders", response_model=ReminderDetailResponse, status_code=status.HTTP_201_CREATED)
def create_household_reminder(
    payload: ReminderCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission(EDIT_PERMISSION)),
) -> ReminderDetailResponse:
    return create_reminder(db, payload, actor_id=user.id)


@router.get("/reminders/{reminder_id}", response_model=ReminderDetailResponse)
def reminder_detail(
    reminder_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission(READ_PERMISSION)),
) -> ReminderDetailResponse:
    return get_reminder_detail(db, reminder_id)


@router.patch("/reminders/{reminder_id}", response_model=ReminderDetailResponse)
def update_household_reminder(
    reminder_id: int,
    payload: ReminderUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission(EDIT_PERMISSION)),
) -> ReminderDetailResponse:
    return update_reminder(db, reminder_id, payload, actor_id=user.id)


@router.post("/reminders/{reminder_id}/complete", response_model=ReminderDetailResponse)
def complete_household_reminder(
    reminder_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission(EDIT_PERMISSION)),
) -> ReminderDetailResponse:
    return complete_reminder(db, reminder_id, actor_id=user.id)


@router.post("/reminders/{reminder_id}/dismiss", response_model=ReminderDetailResponse)
def dismiss_household_reminder(
    reminder_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission(EDIT_PERMISSION)),
) -> ReminderDetailResponse:
    return dismiss_reminder(db, reminder_id, actor_id=user.id)


@router.post("/reminders/{reminder_id}/reopen", response_model=ReminderDetailResponse)
def reopen_household_reminder(
    reminder_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission(EDIT_PERMISSION)),
) -> ReminderDetailResponse:
    return reopen_reminder(db, reminder_id)


@router.delete("/reminders/{reminder_id}", response_model=ReminderDetailResponse)
def archive_household_reminder(
    reminder_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission(EDIT_PERMISSION)),
) -> ReminderDetailResponse:
    return archive_reminder(db, reminder_id)
