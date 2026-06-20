from __future__ import annotations

from datetime import date, timedelta

import pytest
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.auth import User
from app.models.configuration import Category, HomeSpace, ItemStatus, LocationNode, Residence
from app.models.inventory import Item, ItemLoan
from app.models.reminders import Reminder
from app.schemas.reminders import ReminderCreate, ReminderListQuery, ReminderUpdate
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
) -> None:
    item = reminder_seed["item"]
    detail = create_reminder(
        db_session,
        ReminderCreate(title="Check passport", item_id=item.id, due_date=date.today() + timedelta(days=2)),
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


def test_overdue_filter_uses_due_date(db_session: Session, reminder_seed: dict[str, object]) -> None:
    item = reminder_seed["item"]
    create_reminder(
        db_session,
        ReminderCreate(title="Late", item_id=item.id, due_date=date.today() - timedelta(days=1)),
        actor_id=10,
    )
    create_reminder(
        db_session,
        ReminderCreate(title="Soon", item_id=item.id, due_date=date.today() + timedelta(days=1)),
        actor_id=10,
    )

    listed = list_reminders(db_session, ReminderListQuery(overdue=True))

    assert listed.total == 1
    assert listed.items[0].title == "Late"
    assert listed.items[0].due_state == "overdue"


def test_create_rejects_archived_item(db_session: Session, reminder_seed: dict[str, object]) -> None:
    item = reminder_seed["item"]
    item.is_archived = True
    db_session.commit()

    with pytest.raises(HTTPException) as exc_info:
        create_reminder(db_session, ReminderCreate(title="Nope", item_id=item.id), actor_id=10)

    assert exc_info.value.status_code == 400
