from __future__ import annotations

from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.base import Base
from app.models.auth import User
from app.models.configuration import Category, HomeSpace, ItemStatus, LocationNode, Residence
from app.models.inventory import Item, ItemLoan


def test_reminder_table_is_registered() -> None:
    assert "reminders" in set(Base.metadata.tables)


def test_reminder_model_persists_manual_and_loan_links(db_session: Session) -> None:
    from app.models.reminders import Reminder

    user = User(username="editor", password_hash="hash", display_name="Editor")
    home = HomeSpace(name="Home")
    residence = Residence(name="Main", home_space=home)
    location = LocationNode(residence=residence, name="Shelf", node_type="shelf")
    category = Category(code="documents", name="Documents")
    status = ItemStatus(code="in_stock", name="In stock", semantic="in_inventory", is_system=True)
    item = Item(name="Passport", category=category, status=status, location_node=location)
    loan = ItemLoan(item=item, borrower_name="Taylor", expected_return_date=date(2026, 7, 1))
    reminder = Reminder(
        title="Return Passport",
        description="Check with Taylor",
        source_type="loan_return",
        item=item,
        loan=loan,
        due_date=date(2026, 7, 1),
        remind_at=date(2026, 6, 25),
        status="pending",
        priority="high",
        created_by_user=user,
    )
    db_session.add(reminder)
    db_session.commit()

    saved = db_session.scalar(select(Reminder).where(Reminder.title == "Return Passport"))

    assert saved is not None
    assert saved.item.name == "Passport"
    assert saved.loan.borrower_name == "Taylor"
    assert saved.created_by_user.username == "editor"
    assert saved.status == "pending"
    assert saved.priority == "high"
    assert saved.archived_at is None
