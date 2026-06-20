# HomeVault Phase 4A Reminders Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build Phase 4A as a persisted reminder center with reminder lifecycle actions, loan-return reminder automation, reminder detail modal, and item-list reminder filters.

**Architecture:** Add reminders as a separate backend slice with its own SQLAlchemy model, Pydantic schemas, service module, and FastAPI router. The inventory service only imports the reminder service at the loan and list-filter boundaries, while the frontend gets a dedicated reminders API/store/page and small inventory filter extensions.

**Tech Stack:** FastAPI, SQLAlchemy 2, Alembic, Pydantic, pytest, Vue 3, TypeScript, Pinia, Vue Router, Element Plus, Vite.

---

## Source Specs

- `docs/superpowers/specs/2026-06-20-home-vault-phase-4a-reminders-design.md`
- `docs/superpowers/specs/2026-06-19-home-vault-phase-3-inventory-design.md`
- `docs/superpowers/plans/2026-06-19-home-vault-phase-3-inventory.md`

## Scope Check

This plan implements only Phase 4A. It does not add global audit log UI, full user/role management, import/export, external notifications, recurrence, QR code workflows, mobile screens, or the inactive residence-name uniqueness migration. Those remain split into Phase 4B and Phase 4C.

## File Structure

Backend files:

- Create `backend/app/models/reminders.py`: persisted `Reminder` model and relationships to items, loans, and users.
- Modify `backend/app/models/inventory.py`: add `Item.reminders` and `ItemLoan.reminders` relationships.
- Modify `backend/app/models/__init__.py`: export `Reminder`.
- Create `backend/alembic/versions/20260620_0005_reminders.py`: reminder table, indexes, check constraints, downgrade.
- Create `backend/app/schemas/reminders.py`: reminder query, create/update payloads, summaries, detail responses.
- Create `backend/app/services/reminders.py`: reminder CRUD, status transitions, due-state computation, loan reminder sync helpers.
- Modify `backend/app/schemas/inventory.py`: add reminder filter fields to `ItemListQuery`.
- Modify `backend/app/services/inventory.py`: apply reminder filters and call loan reminder sync helpers from loan workflows.
- Create `backend/app/api/routes/reminders.py`: REST routes under `/api/reminders`.
- Modify `backend/app/api/router.py`: include the reminders router.
- Test `backend/tests/test_reminder_models.py`: metadata, persistence, migration.
- Test `backend/tests/test_reminder_schemas.py`: Pydantic bounds and serialization.
- Test `backend/tests/test_reminder_services.py`: service behavior, due-state filters, loan sync, item filters.
- Test `backend/tests/test_reminder_api.py`: API contract and permissions.

Frontend files:

- Create `frontend/src/api/reminders.ts`: typed reminder API client.
- Create `frontend/src/stores/reminders.ts`: Pinia store for list/detail/form actions.
- Create `frontend/src/pages/ReminderCenterPage.vue`: reminder center table, filters, counters, create action.
- Create `frontend/src/components/reminders/ReminderDetailModal.vue`: modal detail and lifecycle actions.
- Create `frontend/src/components/reminders/ReminderFormDialog.vue`: create/edit manual reminders.
- Modify `frontend/src/api/inventory.ts`: add reminder filter fields to `ItemFilters`.
- Modify `frontend/src/components/items/ItemFilterPanel.vue`: add pending/upcoming/overdue quick filters.
- Modify `frontend/src/router/index.ts`: add `/reminders` route guarded by `items:view`.
- Modify `frontend/src/layouts/AppLayout.vue`: add reminder navigation item.

Verification files:

- Use temporary smoke scripts and screenshots under `output/playwright/` or `output/smoke/` when browser tooling is available. Do not commit generated smoke output.

---

## Cross-Cutting Contracts

Use these constants consistently:

```python
REMINDER_STATUS_PENDING = "pending"
REMINDER_STATUS_DONE = "done"
REMINDER_STATUS_DISMISSED = "dismissed"
REMINDER_SOURCE_MANUAL = "manual"
REMINDER_SOURCE_LOAN_RETURN = "loan_return"
REMINDER_PRIORITY_LOW = "low"
REMINDER_PRIORITY_NORMAL = "normal"
REMINDER_PRIORITY_HIGH = "high"
DEFAULT_UPCOMING_DAYS = 7
MAX_UPCOMING_DAYS = 90
```

Use these response due states:

```python
REMINDER_DUE_STATE_DONE = "done"
REMINDER_DUE_STATE_DISMISSED = "dismissed"
REMINDER_DUE_STATE_OVERDUE = "overdue"
REMINDER_DUE_STATE_UPCOMING = "upcoming"
REMINDER_DUE_STATE_SCHEDULED = "scheduled"
REMINDER_DUE_STATE_NONE = "none"
```

Use these backend messages:

```python
REMINDER_NOT_FOUND = "\u63d0\u9192\u4e0d\u5b58\u5728"
REMINDER_TITLE_REQUIRED = "\u63d0\u9192\u6807\u9898\u4e0d\u80fd\u4e3a\u7a7a"
REMINDER_ITEM_NOT_FOUND = "\u5173\u8054\u7269\u54c1\u4e0d\u5b58\u5728"
REMINDER_LOAN_NOT_FOUND = "\u5173\u8054\u501f\u51fa\u8bb0\u5f55\u4e0d\u5b58\u5728"
REMINDER_ARCHIVED = "\u5df2\u5f52\u6863\u7684\u63d0\u9192\u4e0d\u80fd\u64cd\u4f5c"
REMINDER_LOAN_OWNED_FIELD = "\u501f\u51fa\u63d0\u9192\u7684\u5173\u8054\u501f\u51fa\u548c\u5230\u671f\u65e5\u7531\u501f\u51fa\u6d41\u7a0b\u7ef4\u62a4"
```

Route permissions:

```python
READ_PERMISSION = "items:view"
EDIT_PERMISSION = "items:edit"
```

---

## Task 1: Reminder Model And Migration

**Files:**
- Create: `backend/app/models/reminders.py`
- Modify: `backend/app/models/inventory.py`
- Modify: `backend/app/models/__init__.py`
- Create: `backend/alembic/versions/20260620_0005_reminders.py`
- Test: `backend/tests/test_reminder_models.py`

- [ ] **Step 1: Write failing model tests**

Create `backend/tests/test_reminder_models.py`:

```python
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
```

- [ ] **Step 2: Run model tests to verify failure**

Run from `backend`:

```powershell
python -m pytest tests/test_reminder_models.py -v
```

Expected: FAIL because `app.models.reminders` and `reminders` metadata do not exist.

- [ ] **Step 3: Add the Reminder model**

Create `backend/app/models/reminders.py`:

```python
from __future__ import annotations

from datetime import date, datetime, timezone

from sqlalchemy import CheckConstraint, Date, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Reminder(Base):
    __tablename__ = "reminders"
    __table_args__ = (
        CheckConstraint("status IN ('pending', 'done', 'dismissed')", name="ck_reminders_status"),
        CheckConstraint("source_type IN ('manual', 'loan_return')", name="ck_reminders_source_type"),
        CheckConstraint("priority IN ('low', 'normal', 'high')", name="ck_reminders_priority"),
        Index("ix_reminders_pending_due_date", "status", "due_date"),
        Index("ix_reminders_pending_remind_at", "status", "remind_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String(160), nullable=False, index=True)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    source_type: Mapped[str] = mapped_column(String(40), default="manual", nullable=False, index=True)
    item_id: Mapped[int | None] = mapped_column(ForeignKey("items.id", ondelete="SET NULL"), nullable=True, index=True)
    loan_id: Mapped[int | None] = mapped_column(ForeignKey("item_loans.id", ondelete="SET NULL"), nullable=True, index=True)
    due_date: Mapped[date | None] = mapped_column(Date, nullable=True, index=True)
    remind_at: Mapped[date | None] = mapped_column(Date, nullable=True, index=True)
    status: Mapped[str] = mapped_column(String(40), default="pending", nullable=False, index=True)
    priority: Mapped[str] = mapped_column(String(40), default="normal", nullable=False)
    created_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    completed_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    dismissed_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    dismissed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)

    item: Mapped[object | None] = relationship("Item", back_populates="reminders", lazy="selectin")
    loan: Mapped[object | None] = relationship("ItemLoan", back_populates="reminders", lazy="selectin")
    created_by_user: Mapped[object | None] = relationship("User", foreign_keys=[created_by_user_id], lazy="selectin")
    completed_by_user: Mapped[object | None] = relationship("User", foreign_keys=[completed_by_user_id], lazy="selectin")
    dismissed_by_user: Mapped[object | None] = relationship("User", foreign_keys=[dismissed_by_user_id], lazy="selectin")
```

- [ ] **Step 4: Add inventory relationships**

Modify `backend/app/models/inventory.py`:

```python
    reminders: Mapped[list[object]] = relationship(
        "Reminder",
        back_populates="item",
        lazy="selectin",
    )
```

Add the block above to `Item` after the `loans` relationship.

Add this block to `ItemLoan` after `return_actor`:

```python
    reminders: Mapped[list[object]] = relationship(
        "Reminder",
        back_populates="loan",
        lazy="selectin",
    )
```

- [ ] **Step 5: Export the model**

Modify `backend/app/models/__init__.py`:

```python
from app.models.reminders import Reminder
```

Add `"Reminder"` to `__all__`.

- [ ] **Step 6: Add Alembic migration**

Create `backend/alembic/versions/20260620_0005_reminders.py`:

```python
from alembic import op
import sqlalchemy as sa

revision = "20260620_0005"
down_revision = "20260620_0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "reminders",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("title", sa.String(length=160), nullable=False),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("source_type", sa.String(length=40), nullable=False, server_default="manual"),
        sa.Column("item_id", sa.Integer(), sa.ForeignKey("items.id", ondelete="SET NULL"), nullable=True),
        sa.Column("loan_id", sa.Integer(), sa.ForeignKey("item_loans.id", ondelete="SET NULL"), nullable=True),
        sa.Column("due_date", sa.Date(), nullable=True),
        sa.Column("remind_at", sa.Date(), nullable=True),
        sa.Column("status", sa.String(length=40), nullable=False, server_default="pending"),
        sa.Column("priority", sa.String(length=40), nullable=False, server_default="normal"),
        sa.Column("created_by_user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("completed_by_user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("dismissed_by_user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("dismissed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("status IN ('pending', 'done', 'dismissed')", name="ck_reminders_status"),
        sa.CheckConstraint("source_type IN ('manual', 'loan_return')", name="ck_reminders_source_type"),
        sa.CheckConstraint("priority IN ('low', 'normal', 'high')", name="ck_reminders_priority"),
    )
    op.create_index("ix_reminders_id", "reminders", ["id"])
    op.create_index("ix_reminders_title", "reminders", ["title"])
    op.create_index("ix_reminders_source_type", "reminders", ["source_type"])
    op.create_index("ix_reminders_item_id", "reminders", ["item_id"])
    op.create_index("ix_reminders_loan_id", "reminders", ["loan_id"])
    op.create_index("ix_reminders_due_date", "reminders", ["due_date"])
    op.create_index("ix_reminders_remind_at", "reminders", ["remind_at"])
    op.create_index("ix_reminders_status", "reminders", ["status"])
    op.create_index("ix_reminders_archived_at", "reminders", ["archived_at"])
    op.create_index("ix_reminders_pending_due_date", "reminders", ["status", "due_date"])
    op.create_index("ix_reminders_pending_remind_at", "reminders", ["status", "remind_at"])


def downgrade() -> None:
    op.drop_index("ix_reminders_pending_remind_at", table_name="reminders")
    op.drop_index("ix_reminders_pending_due_date", table_name="reminders")
    op.drop_index("ix_reminders_archived_at", table_name="reminders")
    op.drop_index("ix_reminders_status", table_name="reminders")
    op.drop_index("ix_reminders_remind_at", table_name="reminders")
    op.drop_index("ix_reminders_due_date", table_name="reminders")
    op.drop_index("ix_reminders_loan_id", table_name="reminders")
    op.drop_index("ix_reminders_item_id", table_name="reminders")
    op.drop_index("ix_reminders_source_type", table_name="reminders")
    op.drop_index("ix_reminders_title", table_name="reminders")
    op.drop_index("ix_reminders_id", table_name="reminders")
    op.drop_table("reminders")
```

- [ ] **Step 7: Run model tests**

Run from `backend`:

```powershell
python -m pytest tests/test_reminder_models.py -v
```

Expected: PASS.

- [ ] **Step 8: Commit**

```powershell
git add backend/app/models/reminders.py backend/app/models/inventory.py backend/app/models/__init__.py backend/alembic/versions/20260620_0005_reminders.py backend/tests/test_reminder_models.py
git commit -m "feat: add reminder model"
```

---

## Task 2: Reminder Schemas And Service Core

**Files:**
- Create: `backend/app/schemas/reminders.py`
- Create: `backend/app/services/reminders.py`
- Test: `backend/tests/test_reminder_schemas.py`
- Test: `backend/tests/test_reminder_services.py`

- [ ] **Step 1: Write failing schema tests**

Create `backend/tests/test_reminder_schemas.py`:

```python
from __future__ import annotations

from datetime import date, datetime, timezone

import pytest
from pydantic import ValidationError

from app.schemas.reminders import ReminderCreate, ReminderDetailResponse, ReminderListQuery


def test_reminder_create_requires_non_blank_title() -> None:
    with pytest.raises(ValidationError):
        ReminderCreate(title="   ")


def test_reminder_list_query_bounds_upcoming_days() -> None:
    assert ReminderListQuery().upcoming_days is None
    assert ReminderListQuery(upcoming_days=90).upcoming_days == 90
    with pytest.raises(ValidationError):
        ReminderListQuery(upcoming_days=0)
    with pytest.raises(ValidationError):
        ReminderListQuery(upcoming_days=91)


def test_reminder_detail_response_serializes_computed_state() -> None:
    now = datetime(2026, 6, 20, 12, 0, tzinfo=timezone.utc)
    response = ReminderDetailResponse(
        id=1,
        title="Return Passport",
        description="Check with Taylor",
        source_type="loan_return",
        item_id=2,
        loan_id=3,
        due_date=date(2026, 6, 21),
        remind_at=date(2026, 6, 20),
        status="pending",
        priority="high",
        due_state="upcoming",
        days_until_due=1,
        created_by_user_id=4,
        completed_by_user_id=None,
        dismissed_by_user_id=None,
        completed_at=None,
        dismissed_at=None,
        archived_at=None,
        created_at=now,
        updated_at=now,
        item={"id": 2, "name": "Passport", "is_archived": False},
        loan={"id": 3, "borrower_name": "Taylor", "expected_return_date": date(2026, 6, 21), "returned_at": None},
    )
    assert response.due_state == "upcoming"
    assert response.item is not None
    assert response.loan is not None
```

- [ ] **Step 2: Write failing service tests**

Create `backend/tests/test_reminder_services.py` with local seed helpers:

```python
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
```

- [ ] **Step 3: Run tests to verify failure**

Run from `backend`:

```powershell
python -m pytest tests/test_reminder_schemas.py tests/test_reminder_services.py -v
```

Expected: FAIL because reminder schemas and services do not exist.

- [ ] **Step 4: Add reminder schemas**

Create `backend/app/schemas/reminders.py` with these classes:

```python
from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field


class ResponseModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class RequestModel(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)


class ReminderListQuery(RequestModel):
    status: str | None = None
    source_type: str | None = None
    item_id: int | None = None
    loan_id: int | None = None
    overdue: bool | None = None
    upcoming_days: int | None = Field(default=None, ge=1, le=90)
    include_archived: bool = False
    search: str | None = None
    sort: str = "due_asc"
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)


class ReminderCreate(RequestModel):
    title: str = Field(min_length=1, max_length=160)
    description: str = ""
    item_id: int | None = None
    due_date: date | None = None
    remind_at: date | None = None
    priority: str = "normal"


class ReminderUpdate(RequestModel):
    title: str | None = Field(default=None, min_length=1, max_length=160)
    description: str | None = None
    item_id: int | None = None
    due_date: date | None = None
    remind_at: date | None = None
    priority: str | None = None


class ReminderItemSummary(ResponseModel):
    id: int
    name: str
    is_archived: bool


class ReminderLoanSummary(ResponseModel):
    id: int
    borrower_name: str
    expected_return_date: date | None = None
    returned_at: datetime | None = None


class ReminderSummaryResponse(ResponseModel):
    id: int
    title: str
    description: str
    source_type: str
    item_id: int | None = None
    loan_id: int | None = None
    due_date: date | None = None
    remind_at: date | None = None
    status: str
    priority: str
    due_state: str
    days_until_due: int | None = None
    created_by_user_id: int | None = None
    completed_by_user_id: int | None = None
    dismissed_by_user_id: int | None = None
    completed_at: datetime | None = None
    dismissed_at: datetime | None = None
    archived_at: datetime | None = None
    created_at: datetime
    updated_at: datetime
    item: ReminderItemSummary | None = None
    loan: ReminderLoanSummary | None = None


class ReminderDetailResponse(ReminderSummaryResponse):
    pass


class ReminderListResponse(ResponseModel):
    items: list[ReminderSummaryResponse] = Field(default_factory=list)
    total: int
    page: int
    page_size: int
```

- [ ] **Step 5: Add reminder service core**

Create `backend/app/services/reminders.py` with constants and these function signatures:

```python
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

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
    from fastapi import HTTPException, status

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
```

In the same file, add these behavior functions:

```python
def reminder_options() -> tuple:
    return (
        selectinload(Reminder.item),
        selectinload(Reminder.loan),
    )


def require_reminder(db: Session, reminder_id: int) -> Reminder:
    reminder = db.scalar(select(Reminder).where(Reminder.id == reminder_id).options(*reminder_options()))
    if reminder is None:
        raise not_found("\u63d0\u9192\u4e0d\u5b58\u5728")
    return reminder


def require_mutable_reminder(reminder: Reminder) -> None:
    if reminder.archived_at is not None:
        raise bad_request("\u5df2\u5f52\u6863\u7684\u63d0\u9192\u4e0d\u80fd\u64cd\u4f5c")


def validate_priority(priority: str) -> str:
    normalized = priority.strip().lower()
    if normalized not in REMINDER_PRIORITIES:
        raise bad_request("\u63d0\u9192\u4f18\u5148\u7ea7\u4e0d\u5408\u6cd5")
    return normalized


def load_active_item(db: Session, item_id: int | None) -> Item | None:
    if item_id is None:
        return None
    item = db.get(Item, item_id)
    if item is None or item.is_archived:
        raise bad_request("\u5173\u8054\u7269\u54c1\u4e0d\u5b58\u5728")
    return item


def compute_due_state(reminder: Reminder, *, today: date | None = None, upcoming_days: int = DEFAULT_UPCOMING_DAYS) -> tuple[str, int | None]:
    current_day = today or server_today()
    if reminder.status == REMINDER_STATUS_DONE:
        return "done", None
    if reminder.status == REMINDER_STATUS_DISMISSED:
        return "dismissed", None
    if reminder.due_date is not None:
        days_until_due = (reminder.due_date - current_day).days
        if days_until_due < 0:
            return "overdue", days_until_due
        if days_until_due <= upcoming_days:
            return "upcoming", days_until_due
        return "scheduled", days_until_due
    if reminder.remind_at is not None:
        days_until_reminder = (reminder.remind_at - current_day).days
        if days_until_reminder <= upcoming_days:
            return "upcoming", days_until_reminder
        return "scheduled", days_until_reminder
    return "none", None
```

Add response builders and CRUD functions:

```python
def build_reminder_response(reminder: Reminder) -> ReminderDetailResponse:
    due_state, days_until_due = compute_due_state(reminder)
    return ReminderDetailResponse(
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
        due_state=due_state,
        days_until_due=days_until_due,
        created_by_user_id=reminder.created_by_user_id,
        completed_by_user_id=reminder.completed_by_user_id,
        dismissed_by_user_id=reminder.dismissed_by_user_id,
        completed_at=reminder.completed_at,
        dismissed_at=reminder.dismissed_at,
        archived_at=reminder.archived_at,
        created_at=reminder.created_at,
        updated_at=reminder.updated_at,
        item=ReminderItemSummary.model_validate(reminder.item) if reminder.item is not None else None,
        loan=ReminderLoanSummary.model_validate(reminder.loan) if reminder.loan is not None else None,
    )


def create_reminder(db: Session, payload: ReminderCreate, actor_id: int | None = None) -> ReminderDetailResponse:
    title = payload.title.strip()
    if title == "":
        raise bad_request("\u63d0\u9192\u6807\u9898\u4e0d\u80fd\u4e3a\u7a7a")
    item = load_active_item(db, payload.item_id)
    reminder = Reminder(
        title=title,
        description=payload.description,
        source_type=REMINDER_SOURCE_MANUAL,
        item_id=item.id if item is not None else None,
        due_date=payload.due_date,
        remind_at=payload.remind_at,
        status=REMINDER_STATUS_PENDING,
        priority=validate_priority(payload.priority),
        created_by_user_id=actor_id,
    )
    db.add(reminder)
    commit_or_bad_request(db, "\u63d0\u9192\u4fdd\u5b58\u5931\u8d25")
    return get_reminder_detail(db, reminder.id)


def get_reminder_detail(db: Session, reminder_id: int) -> ReminderDetailResponse:
    return build_reminder_response(require_reminder(db, reminder_id))
```

Implement `list_reminders`, `update_reminder`, `complete_reminder`, `dismiss_reminder`, `reopen_reminder`, and `archive_reminder` in the same service. Use these exact rules:

```python
def list_reminders(db: Session, query: ReminderListQuery) -> ReminderListResponse:
    stmt = select(Reminder)
    today = server_today()
    if not query.include_archived:
        stmt = stmt.where(Reminder.archived_at.is_(None))
    if query.status:
        stmt = stmt.where(Reminder.status == query.status)
    if query.source_type:
        stmt = stmt.where(Reminder.source_type == query.source_type)
    if query.item_id is not None:
        stmt = stmt.where(Reminder.item_id == query.item_id)
    if query.loan_id is not None:
        stmt = stmt.where(Reminder.loan_id == query.loan_id)
    if query.overdue is True:
        stmt = stmt.where(Reminder.status == REMINDER_STATUS_PENDING, Reminder.due_date < today)
    elif query.overdue is False:
        stmt = stmt.where(or_(Reminder.due_date.is_(None), Reminder.due_date >= today))
    if query.upcoming_days is not None:
        cutoff = today + timedelta(days=query.upcoming_days)
        stmt = stmt.where(
            Reminder.status == REMINDER_STATUS_PENDING,
            or_(
                Reminder.due_date.between(today, cutoff),
                Reminder.remind_at.between(today, cutoff),
            ),
        )
    if query.search:
        search_term = f"%{query.search.strip()}%"
        if search_term != "%%":
            stmt = stmt.where(
                or_(
                    Reminder.title.ilike(search_term),
                    Reminder.description.ilike(search_term),
                    Reminder.item.has(Item.name.ilike(search_term)),
                )
            )
    total = db.scalar(select(func.count()).select_from(stmt.order_by(None).subquery())) or 0
    if query.sort == "created_desc":
        stmt = stmt.order_by(Reminder.created_at.desc(), Reminder.id.desc())
    elif query.sort == "priority_desc":
        stmt = stmt.order_by(Reminder.priority.desc(), Reminder.due_date.asc().nulls_last(), Reminder.id.asc())
    else:
        stmt = stmt.order_by(Reminder.due_date.asc().nulls_last(), Reminder.remind_at.asc().nulls_last(), Reminder.id.asc())
    reminders = db.scalars(
        stmt.options(*reminder_options()).limit(query.page_size).offset((query.page - 1) * query.page_size)
    ).unique().all()
    return ReminderListResponse(
        items=[build_reminder_response(reminder) for reminder in reminders],
        total=total,
        page=query.page,
        page_size=query.page_size,
    )
```

Use this code for update and lifecycle actions:

```python
def update_reminder(
    db: Session,
    reminder_id: int,
    payload: ReminderUpdate,
    actor_id: int | None = None,
) -> ReminderDetailResponse:
    reminder = require_reminder(db, reminder_id)
    require_mutable_reminder(reminder)
    if reminder.source_type == REMINDER_SOURCE_LOAN_RETURN and (
        payload.item_id is not None or payload.due_date is not None
    ):
        raise bad_request("\u501f\u51fa\u63d0\u9192\u7684\u5173\u8054\u501f\u51fa\u548c\u5230\u671f\u65e5\u7531\u501f\u51fa\u6d41\u7a0b\u7ef4\u62a4")
    if payload.title is not None:
        reminder.title = payload.title.strip()
    if payload.description is not None:
        reminder.description = payload.description
    if payload.item_id is not None:
        item = load_active_item(db, payload.item_id)
        reminder.item_id = item.id if item is not None else None
    if payload.due_date is not None:
        reminder.due_date = payload.due_date
    if payload.remind_at is not None:
        reminder.remind_at = payload.remind_at
    if payload.priority is not None:
        reminder.priority = validate_priority(payload.priority)
    reminder.updated_at = utcnow()
    commit_or_bad_request(db, "\u63d0\u9192\u4fdd\u5b58\u5931\u8d25")
    return get_reminder_detail(db, reminder_id)


def complete_reminder(db: Session, reminder_id: int, actor_id: int | None = None) -> ReminderDetailResponse:
    reminder = require_reminder(db, reminder_id)
    require_mutable_reminder(reminder)
    if reminder.status != REMINDER_STATUS_DONE:
        now = utcnow()
        reminder.status = REMINDER_STATUS_DONE
        reminder.completed_at = now
        reminder.completed_by_user_id = actor_id
        reminder.dismissed_at = None
        reminder.dismissed_by_user_id = None
        reminder.updated_at = now
        commit_or_bad_request(db, "\u63d0\u9192\u4fdd\u5b58\u5931\u8d25")
    return get_reminder_detail(db, reminder_id)


def dismiss_reminder(db: Session, reminder_id: int, actor_id: int | None = None) -> ReminderDetailResponse:
    reminder = require_reminder(db, reminder_id)
    require_mutable_reminder(reminder)
    if reminder.status != REMINDER_STATUS_DISMISSED:
        now = utcnow()
        reminder.status = REMINDER_STATUS_DISMISSED
        reminder.dismissed_at = now
        reminder.dismissed_by_user_id = actor_id
        reminder.completed_at = None
        reminder.completed_by_user_id = None
        reminder.updated_at = now
        commit_or_bad_request(db, "\u63d0\u9192\u4fdd\u5b58\u5931\u8d25")
    return get_reminder_detail(db, reminder_id)


def reopen_reminder(db: Session, reminder_id: int) -> ReminderDetailResponse:
    reminder = require_reminder(db, reminder_id)
    require_mutable_reminder(reminder)
    reminder.status = REMINDER_STATUS_PENDING
    reminder.completed_at = None
    reminder.completed_by_user_id = None
    reminder.dismissed_at = None
    reminder.dismissed_by_user_id = None
    reminder.updated_at = utcnow()
    commit_or_bad_request(db, "\u63d0\u9192\u4fdd\u5b58\u5931\u8d25")
    return get_reminder_detail(db, reminder_id)


def archive_reminder(db: Session, reminder_id: int) -> ReminderDetailResponse:
    reminder = require_reminder(db, reminder_id)
    if reminder.archived_at is None:
        reminder.archived_at = utcnow()
        reminder.updated_at = utcnow()
        commit_or_bad_request(db, "\u63d0\u9192\u4fdd\u5b58\u5931\u8d25")
    return get_reminder_detail(db, reminder_id)
```

- [ ] **Step 6: Run schema and service tests**

Run from `backend`:

```powershell
python -m pytest tests/test_reminder_schemas.py tests/test_reminder_services.py -v
```

Expected: PASS.

- [ ] **Step 7: Commit**

```powershell
git add backend/app/schemas/reminders.py backend/app/services/reminders.py backend/tests/test_reminder_schemas.py backend/tests/test_reminder_services.py
git commit -m "feat: add reminder service"
```

---

## Task 3: Reminder API Routes

**Files:**
- Create: `backend/app/api/routes/reminders.py`
- Modify: `backend/app/api/router.py`
- Test: `backend/tests/test_reminder_api.py`

- [ ] **Step 1: Write failing API tests**

Create `backend/tests/test_reminder_api.py` by reusing the seed helpers from `test_inventory_api.py`:

```python
from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.core.config import get_settings
from app.core.security import hash_password
from app.main import app
from app.models.auth import Role, User
from app.models.configuration import Category, FamilyMember, HomeSpace, ItemStatus, LocationNode, Residence
from app.services.seed import seed_auth_baseline


@pytest.fixture()
def client(db_session: Session, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    upload_dir = tmp_path / "uploads"
    upload_dir.mkdir()
    monkeypatch.setattr(get_settings(), "upload_dir", str(upload_dir), raising=False)
    seed_auth_baseline(db_session, admin_username="admin", admin_password="ChangeMe123!")
    seed_inventory_config(db_session)
    seed_user(db_session, "editor", "Editor123!", "editor")
    seed_user(db_session, "viewer", "Viewer123!", "viewer")

    def override_get_db() -> Iterator[Session]:
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()


def seed_user(db: Session, username: str, password: str, role_code: str) -> User:
    role = db.scalar(select(Role).where(Role.code == role_code))
    assert role is not None
    user = User(username=username, password_hash=hash_password(password), display_name=username.title(), is_active=True)
    user.roles = [role]
    db.add(user)
    db.commit()
    db.refresh(user)
    return user
```

Add these helper functions below `seed_user`:

```python
def seed_inventory_config(db: Session) -> None:
    home = db.scalar(select(HomeSpace).order_by(HomeSpace.id))
    assert home is not None
    residence = Residence(name="Main residence", home_space=home, sort_order=10)
    shelf = LocationNode(residence=residence, name="Shelf", node_type="shelf", sort_order=10)
    member = FamilyMember(home_space=home, name="Alex", relation="Owner")
    category = Category(code="documents", name="Documents", sort_order=10)
    db.add_all([residence, shelf, member, category])
    db.commit()


def login(client: TestClient, username: str = "admin", password: str = "ChangeMe123!") -> dict[str, str]:
    response = client.post("/api/auth/login", json={"username": username, "password": password})
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def inventory_ids(db: Session) -> dict[str, int]:
    return {
        "category_id": db.scalar(select(Category.id).where(Category.code == "documents")),
        "in_stock_id": db.scalar(select(ItemStatus.id).where(ItemStatus.code == "in_stock")),
        "shelf_id": db.scalar(select(LocationNode.id).where(LocationNode.name == "Shelf")),
        "member_id": db.scalar(select(FamilyMember.id).where(FamilyMember.name == "Alex")),
    }


def make_item_payload(ids: dict[str, int], **overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "name": "Passport folder",
        "description": "Family documents",
        "category_id": ids["category_id"],
        "status_id": ids["in_stock_id"],
        "quantity": "1.00",
        "unit": "pcs",
        "owner_member_id": ids["member_id"],
        "keeper_member_id": ids["member_id"],
        "location_node_id": ids["shelf_id"],
        "is_container": False,
        "privacy_level": "normal",
        "attribute_values": [],
        "tags": ["Important"],
    }
    payload.update(overrides)
    return payload


def create_item(client: TestClient, headers: dict[str, str], ids: dict[str, int], **overrides: object) -> dict[str, object]:
    response = client.post("/api/items", headers=headers, json=make_item_payload(ids, **overrides))
    assert response.status_code == 201
    return response.json()
```

Then add tests:

```python
def test_editor_can_create_filter_complete_reopen_dismiss_and_archive_reminder(client: TestClient, db_session: Session) -> None:
    headers = login(client, "editor", "Editor123!")
    ids = inventory_ids(db_session)
    item = create_item(client, headers, ids)

    created = client.post(
        "/api/reminders",
        headers=headers,
        json={"title": "Check passport", "item_id": item["id"], "due_date": "2026-07-01", "priority": "high"},
    )
    reminder_id = created.json()["id"]
    listed = client.get("/api/reminders", headers=headers, params={"upcoming_days": 90})
    detail = client.get(f"/api/reminders/{reminder_id}", headers=headers)
    completed = client.post(f"/api/reminders/{reminder_id}/complete", headers=headers)
    reopened = client.post(f"/api/reminders/{reminder_id}/reopen", headers=headers)
    dismissed = client.post(f"/api/reminders/{reminder_id}/dismiss", headers=headers)
    archived = client.delete(f"/api/reminders/{reminder_id}", headers=headers)

    assert created.status_code == 201
    assert created.json()["item"]["id"] == item["id"]
    assert listed.status_code == 200
    assert listed.json()["total"] == 1
    assert detail.status_code == 200
    assert completed.json()["status"] == "done"
    assert reopened.json()["status"] == "pending"
    assert dismissed.json()["status"] == "dismissed"
    assert archived.status_code == 200
    assert archived.json()["archived_at"] is not None


def test_viewer_can_read_but_cannot_write_reminders(client: TestClient, db_session: Session) -> None:
    admin_headers = login(client)
    viewer_headers = login(client, "viewer", "Viewer123!")
    ids = inventory_ids(db_session)
    item = create_item(client, admin_headers, ids)
    created = client.post("/api/reminders", headers=admin_headers, json={"title": "Read me", "item_id": item["id"]})
    reminder_id = created.json()["id"]

    listed = client.get("/api/reminders", headers=viewer_headers)
    detail = client.get(f"/api/reminders/{reminder_id}", headers=viewer_headers)
    create_response = client.post("/api/reminders", headers=viewer_headers, json={"title": "Nope"})
    complete_response = client.post(f"/api/reminders/{reminder_id}/complete", headers=viewer_headers)

    assert listed.status_code == 200
    assert detail.status_code == 200
    assert create_response.status_code == 403
    assert complete_response.status_code == 403
```

- [ ] **Step 2: Run API tests to verify failure**

Run from `backend`:

```powershell
python -m pytest tests/test_reminder_api.py -v
```

Expected: FAIL because `/api/reminders` routes are not registered.

- [ ] **Step 3: Add reminder routes**

Create `backend/app/api/routes/reminders.py`:

```python
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
```

- [ ] **Step 4: Register the router**

Modify `backend/app/api/router.py`:

```python
from app.api.routes import auth, configuration, health, inventory, reminders

api_router.include_router(reminders.router)
```

- [ ] **Step 5: Run API tests**

Run from `backend`:

```powershell
python -m pytest tests/test_reminder_api.py -v
```

Expected: PASS.

- [ ] **Step 6: Commit**

```powershell
git add backend/app/api/routes/reminders.py backend/app/api/router.py backend/tests/test_reminder_api.py
git commit -m "feat: expose reminder api"
```

---

## Task 4: Loan Reminder Sync And Item Filters

**Files:**
- Modify: `backend/app/services/reminders.py`
- Modify: `backend/app/schemas/inventory.py`
- Modify: `backend/app/services/inventory.py`
- Test: `backend/tests/test_reminder_services.py`
- Test: `backend/tests/test_inventory_api.py`
- Test: `backend/tests/test_inventory_services.py`

- [ ] **Step 1: Add failing loan sync service tests**

Append to `backend/tests/test_reminder_services.py`:

```python
from app.schemas.inventory import ItemListQuery, LoanCreate, LoanReturn
from app.services.inventory import create_loan, list_items, return_loan


def test_loan_with_expected_return_date_creates_and_completes_reminder(
    db_session: Session,
    reminder_seed: dict[str, object],
) -> None:
    item = reminder_seed["item"]

    detail = create_loan(
        db_session,
        item.id,
        LoanCreate(borrower_name="Taylor", expected_return_date=date.today() + timedelta(days=3)),
        actor_id=10,
    )
    loan_id = detail.loans[0].id
    reminder = db_session.scalar(select(Reminder).where(Reminder.loan_id == loan_id))

    assert reminder is not None
    assert reminder.source_type == "loan_return"
    assert reminder.item_id == item.id
    assert reminder.due_date == date.today() + timedelta(days=3)
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
    create_reminder(
        db_session,
        ReminderCreate(title="Late", item_id=item.id, due_date=date.today() - timedelta(days=1)),
        actor_id=10,
    )

    overdue = list_items(db_session, ItemListQuery(has_overdue_reminder=True))
    upcoming = list_items(db_session, ItemListQuery(has_upcoming_reminder=True, reminder_upcoming_days=7))
    pending = list_items(db_session, ItemListQuery(has_pending_reminder=True))

    assert overdue.total == 1
    assert overdue.items[0].id == item.id
    assert upcoming.total == 0
    assert pending.total == 1
```

- [ ] **Step 2: Add failing API filter test**

Append to `backend/tests/test_inventory_api.py`:

```python
def test_inventory_api_filters_items_by_reminders(client: TestClient, db_session: Session) -> None:
    headers = login(client)
    ids = inventory_ids(db_session)
    item = create_item(client, headers, ids)
    reminder = client.post(
        "/api/reminders",
        headers=headers,
        json={"title": "Late", "item_id": item["id"], "due_date": "2020-01-01"},
    )
    overdue = client.get("/api/items", headers=headers, params={"has_overdue_reminder": True})
    upcoming = client.get("/api/items", headers=headers, params={"has_upcoming_reminder": True, "reminder_upcoming_days": 7})
    pending = client.get("/api/items", headers=headers, params={"has_pending_reminder": True})

    assert reminder.status_code == 201
    assert overdue.status_code == 200
    assert overdue.json()["total"] == 1
    assert overdue.json()["items"][0]["id"] == item["id"]
    assert upcoming.status_code == 200
    assert upcoming.json()["total"] == 0
    assert pending.status_code == 200
    assert pending.json()["total"] == 1
```

- [ ] **Step 3: Run tests to verify failure**

Run from `backend`:

```powershell
python -m pytest tests/test_reminder_services.py::test_loan_with_expected_return_date_creates_and_completes_reminder tests/test_reminder_services.py::test_item_list_reminder_filters tests/test_inventory_api.py::test_inventory_api_filters_items_by_reminders -v
```

Expected: FAIL because loan sync and item filters are absent.

- [ ] **Step 4: Add loan sync helpers**

Append to `backend/app/services/reminders.py`:

```python
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
```

- [ ] **Step 5: Wire loan sync into inventory service**

Modify `backend/app/services/inventory.py` imports:

```python
from app.models.reminders import Reminder
from app.services.reminders import complete_loan_return_reminder, server_today, sync_loan_return_reminder
```

In `create_loan`, replace the inline `db.add(ItemLoan(...))` block with:

```python
    loan = ItemLoan(
        item_id=item.id,
        borrower_name=payload.borrower_name,
        borrower_contact=payload.borrower_contact,
        expected_return_date=payload.expected_return_date,
        loan_note=payload.loan_note,
        loan_actor_id=actor_id,
    )
    db.add(loan)
    flush_or_bad_request(db, "\u7269\u54c1\u4fdd\u5b58\u5931\u8d25")
    sync_loan_return_reminder(db, item=item, loan=loan, actor_id=actor_id)
```

In `return_loan`, after setting `loan.return_actor_id = actor_id`, add:

```python
    complete_loan_return_reminder(db, loan_id=loan.id, actor_id=actor_id)
```

- [ ] **Step 6: Add inventory query fields**

Modify `backend/app/schemas/inventory.py` in `ItemListQuery`:

```python
    has_pending_reminder: bool | None = None
    has_upcoming_reminder: bool | None = None
    has_overdue_reminder: bool | None = None
    reminder_upcoming_days: int = Field(default=7, ge=1, le=90)
```

- [ ] **Step 7: Apply item reminder filters**

Modify `backend/app/services/inventory.py` inside `list_items` before effective-location handling:

```python
    today = server_today()
    reminder_cutoff = today + timedelta(days=query.reminder_upcoming_days)
    pending_reminder_predicate = Item.reminders.any(and_(
        Reminder.status == "pending",
        Reminder.archived_at.is_(None),
    ))
    upcoming_reminder_predicate = Item.reminders.any(and_(
        Reminder.status == "pending",
        Reminder.archived_at.is_(None),
        or_(
            Reminder.due_date.between(today, reminder_cutoff),
            Reminder.remind_at.between(today, reminder_cutoff),
        ),
    ))
    overdue_reminder_predicate = Item.reminders.any(and_(
        Reminder.status == "pending",
        Reminder.archived_at.is_(None),
        Reminder.due_date < today,
    ))
    if query.has_pending_reminder is True:
        stmt = stmt.where(pending_reminder_predicate)
    elif query.has_pending_reminder is False:
        stmt = stmt.where(~pending_reminder_predicate)
    if query.has_upcoming_reminder is True:
        stmt = stmt.where(upcoming_reminder_predicate)
    elif query.has_upcoming_reminder is False:
        stmt = stmt.where(~upcoming_reminder_predicate)
    if query.has_overdue_reminder is True:
        stmt = stmt.where(overdue_reminder_predicate)
    elif query.has_overdue_reminder is False:
        stmt = stmt.where(~overdue_reminder_predicate)
```

Also add `timedelta` to the datetime import:

```python
from datetime import date, datetime, timedelta, timezone
```

Modify the SQLAlchemy import:

```python
from sqlalchemy import and_, func, or_, select
```

- [ ] **Step 8: Run reminder sync and item filter tests**

Run from `backend`:

```powershell
python -m pytest tests/test_reminder_services.py tests/test_inventory_api.py::test_inventory_api_filters_items_by_reminders -v
```

Expected: PASS.

- [ ] **Step 9: Commit**

```powershell
git add backend/app/services/reminders.py backend/app/schemas/inventory.py backend/app/services/inventory.py backend/tests/test_reminder_services.py backend/tests/test_inventory_api.py
git commit -m "feat: sync reminders with inventory"
```

---

## Task 5: Frontend Reminder API And Store

**Files:**
- Create: `frontend/src/api/reminders.ts`
- Create: `frontend/src/stores/reminders.ts`

- [ ] **Step 1: Add typed reminder API client**

Create `frontend/src/api/reminders.ts`:

```ts
import { apiClient } from './client'

export interface ReminderItemSummary {
  id: number
  name: string
  is_archived: boolean
}

export interface ReminderLoanSummary {
  id: number
  borrower_name: string
  expected_return_date: string | null
  returned_at: string | null
}

export interface ReminderSummary {
  id: number
  title: string
  description: string
  source_type: 'manual' | 'loan_return'
  item_id: number | null
  loan_id: number | null
  due_date: string | null
  remind_at: string | null
  status: 'pending' | 'done' | 'dismissed'
  priority: 'low' | 'normal' | 'high'
  due_state: 'done' | 'dismissed' | 'overdue' | 'upcoming' | 'scheduled' | 'none'
  days_until_due: number | null
  created_by_user_id: number | null
  completed_by_user_id: number | null
  dismissed_by_user_id: number | null
  completed_at: string | null
  dismissed_at: string | null
  archived_at: string | null
  created_at: string
  updated_at: string
  item: ReminderItemSummary | null
  loan: ReminderLoanSummary | null
}

export type ReminderDetail = ReminderSummary

export interface ReminderListResponse {
  items: ReminderSummary[]
  total: number
  page: number
  page_size: number
}

export interface ReminderFilters {
  status?: string | null
  source_type?: string | null
  item_id?: number | null
  loan_id?: number | null
  overdue?: boolean | null
  upcoming_days?: number | null
  include_archived?: boolean
  search?: string | null
  sort?: string
  page?: number
  page_size?: number
}

export interface ReminderCreateRequest {
  title: string
  description?: string
  item_id?: number | null
  due_date?: string | null
  remind_at?: string | null
  priority?: 'low' | 'normal' | 'high'
}

export interface ReminderUpdateRequest {
  title?: string
  description?: string | null
  item_id?: number | null
  due_date?: string | null
  remind_at?: string | null
  priority?: 'low' | 'normal' | 'high'
}

export async function listRemindersApi(filters: ReminderFilters = {}): Promise<ReminderListResponse> {
  const response = await apiClient.get<ReminderListResponse>('/reminders', { params: filters })
  return response.data
}

export async function createReminderApi(payload: ReminderCreateRequest): Promise<ReminderDetail> {
  const response = await apiClient.post<ReminderDetail>('/reminders', payload)
  return response.data
}

export async function fetchReminderDetailApi(reminderId: number): Promise<ReminderDetail> {
  const response = await apiClient.get<ReminderDetail>(`/reminders/${reminderId}`)
  return response.data
}

export async function updateReminderApi(reminderId: number, payload: ReminderUpdateRequest): Promise<ReminderDetail> {
  const response = await apiClient.patch<ReminderDetail>(`/reminders/${reminderId}`, payload)
  return response.data
}

export async function completeReminderApi(reminderId: number): Promise<ReminderDetail> {
  const response = await apiClient.post<ReminderDetail>(`/reminders/${reminderId}/complete`)
  return response.data
}

export async function dismissReminderApi(reminderId: number): Promise<ReminderDetail> {
  const response = await apiClient.post<ReminderDetail>(`/reminders/${reminderId}/dismiss`)
  return response.data
}

export async function reopenReminderApi(reminderId: number): Promise<ReminderDetail> {
  const response = await apiClient.post<ReminderDetail>(`/reminders/${reminderId}/reopen`)
  return response.data
}

export async function archiveReminderApi(reminderId: number): Promise<ReminderDetail> {
  const response = await apiClient.delete<ReminderDetail>(`/reminders/${reminderId}`)
  return response.data
}
```

- [ ] **Step 2: Add reminder store**

Create `frontend/src/stores/reminders.ts`:

```ts
import { defineStore } from 'pinia'

import {
  archiveReminderApi,
  completeReminderApi,
  createReminderApi,
  dismissReminderApi,
  fetchReminderDetailApi,
  listRemindersApi,
  reopenReminderApi,
  updateReminderApi,
  type ReminderCreateRequest,
  type ReminderDetail,
  type ReminderFilters,
  type ReminderSummary,
  type ReminderUpdateRequest
} from '../api/reminders'

interface ReminderState {
  reminders: ReminderSummary[]
  selectedReminder: ReminderDetail | null
  total: number
  page: number
  pageSize: number
  loading: boolean
  saving: boolean
  filters: ReminderFilters
}

const defaultFilters = (): ReminderFilters => ({
  page: 1,
  page_size: 20,
  sort: 'due_asc',
  include_archived: false
})

let loadRemindersRequestId = 0

export const useReminderStore = defineStore('reminders', {
  state: (): ReminderState => ({
    reminders: [],
    selectedReminder: null,
    total: 0,
    page: 1,
    pageSize: 20,
    loading: false,
    saving: false,
    filters: defaultFilters()
  }),
  actions: {
    async loadReminders(filters?: ReminderFilters) {
      if (filters) this.applyFilters(filters)
      const requestId = ++loadRemindersRequestId
      this.loading = true
      try {
        const response = await listRemindersApi(this.filters)
        if (requestId !== loadRemindersRequestId) return
        this.reminders = response.items
        this.total = response.total
        this.page = response.page
        this.pageSize = response.page_size
      } finally {
        if (requestId === loadRemindersRequestId) this.loading = false
      }
    },
    async openDetail(reminderId: number) {
      this.loading = true
      try {
        this.selectedReminder = await fetchReminderDetailApi(reminderId)
      } finally {
        this.loading = false
      }
    },
    applyFilters(filters: ReminderFilters) {
      this.filters = { ...this.filters, ...filters, page: 1 }
    },
    setPage(page: number) {
      this.filters = { ...this.filters, page }
      this.page = page
    },
    setPageSize(pageSize: number) {
      this.filters = { ...this.filters, page: 1, page_size: pageSize }
      this.page = 1
      this.pageSize = pageSize
    },
    resetFilters() {
      this.filters = defaultFilters()
      this.page = 1
      this.pageSize = this.filters.page_size ?? 20
    },
    closeDetail() {
      this.selectedReminder = null
    },
    async createReminder(payload: ReminderCreateRequest) {
      return await this.saveAndRefresh(() => createReminderApi(payload))
    },
    async updateReminder(reminderId: number, payload: ReminderUpdateRequest) {
      return await this.saveAndRefresh(() => updateReminderApi(reminderId, payload))
    },
    async completeReminder(reminderId: number) {
      return await this.saveAndRefresh(() => completeReminderApi(reminderId))
    },
    async dismissReminder(reminderId: number) {
      return await this.saveAndRefresh(() => dismissReminderApi(reminderId))
    },
    async reopenReminder(reminderId: number) {
      return await this.saveAndRefresh(() => reopenReminderApi(reminderId))
    },
    async archiveReminder(reminderId: number) {
      return await this.saveAndRefresh(() => archiveReminderApi(reminderId))
    },
    async saveAndRefresh<T extends ReminderDetail>(operation: () => Promise<T>): Promise<T> {
      this.saving = true
      try {
        const result = await operation()
        this.selectedReminder = result
        await this.loadReminders()
        return result
      } finally {
        this.saving = false
      }
    }
  }
})
```

- [ ] **Step 3: Run frontend typecheck through build**

Run from `frontend`:

```powershell
npm.cmd run build
```

Expected: PASS.

- [ ] **Step 4: Commit**

```powershell
git add frontend/src/api/reminders.ts frontend/src/stores/reminders.ts
git commit -m "feat: add reminder frontend client"
```

---

## Task 6: Reminder Center Page And Modal

**Files:**
- Create: `frontend/src/components/reminders/ReminderDetailModal.vue`
- Create: `frontend/src/components/reminders/ReminderFormDialog.vue`
- Create: `frontend/src/pages/ReminderCenterPage.vue`
- Modify: `frontend/src/router/index.ts`
- Modify: `frontend/src/layouts/AppLayout.vue`

- [ ] **Step 1: Add reminder detail modal**

Create `frontend/src/components/reminders/ReminderDetailModal.vue` with this interface and behavior:

```vue
<script setup lang="ts">
import { computed } from 'vue'
import { Bell, Check, Close, Delete, Edit, RefreshLeft } from '@element-plus/icons-vue'

import type { ReminderDetail } from '../../api/reminders'

const props = defineProps<{
  modelValue: boolean
  reminder: ReminderDetail | null
  loading?: boolean
  saving?: boolean
  canEdit: boolean
}>()

const emit = defineEmits<{
  'update:modelValue': [value: boolean]
  edit: []
  complete: []
  dismiss: []
  reopen: []
  archive: []
  close: []
}>()

const canComplete = computed(() => props.canEdit && props.reminder?.status === 'pending' && !props.reminder.archived_at)
const canDismiss = computed(() => props.canEdit && props.reminder?.status === 'pending' && !props.reminder.archived_at)
const canReopen = computed(() => props.canEdit && props.reminder && props.reminder.status !== 'pending' && !props.reminder.archived_at)

function updateOpen(open: boolean) {
  emit('update:modelValue', open)
  if (!open) emit('close')
}

function formatDate(value?: string | null): string {
  if (!value) return '-'
  const parsed = new Date(value)
  if (Number.isNaN(parsed.getTime())) return value
  return parsed.toLocaleDateString('zh-CN')
}

function stateLabel(value?: string): string {
  if (value === 'overdue') return '已逾期'
  if (value === 'upcoming') return '即将到期'
  if (value === 'scheduled') return '已安排'
  if (value === 'done') return '已完成'
  if (value === 'dismissed') return '已忽略'
  return '无日期'
}
</script>

<template>
  <el-dialog :model-value="modelValue" width="min(760px, 96vw)" destroy-on-close @update:model-value="updateOpen">
    <template #header>
      <div class="dialog-header">
        <div>
          <h2>{{ reminder?.title || '提醒详情' }}</h2>
          <p>{{ reminder?.item?.name || '未关联物品' }}</p>
        </div>
        <el-tag v-if="reminder" effect="plain">{{ stateLabel(reminder.due_state) }}</el-tag>
      </div>
    </template>

    <div v-loading="loading" class="detail-body">
      <el-empty v-if="!reminder" description="暂无提醒详情" />
      <template v-else>
        <div class="action-bar">
          <el-button v-if="canEdit && reminder.source_type === 'manual' && !reminder.archived_at" :icon="Edit" @click="emit('edit')">编辑</el-button>
          <el-button v-if="canComplete" type="primary" :icon="Check" :loading="saving" @click="emit('complete')">完成</el-button>
          <el-button v-if="canDismiss" :icon="Close" :loading="saving" @click="emit('dismiss')">忽略</el-button>
          <el-button v-if="canReopen" :icon="RefreshLeft" :loading="saving" @click="emit('reopen')">重新打开</el-button>
          <el-button v-if="canEdit && !reminder.archived_at" type="danger" plain :icon="Delete" :loading="saving" @click="emit('archive')">归档</el-button>
        </div>

        <el-descriptions :column="2" border>
          <el-descriptions-item label="标题">{{ reminder.title }}</el-descriptions-item>
          <el-descriptions-item label="来源">{{ reminder.source_type === 'loan_return' ? '借出归还' : '手动提醒' }}</el-descriptions-item>
          <el-descriptions-item label="状态">{{ stateLabel(reminder.due_state) }}</el-descriptions-item>
          <el-descriptions-item label="优先级">{{ reminder.priority }}</el-descriptions-item>
          <el-descriptions-item label="提醒日期">{{ formatDate(reminder.remind_at) }}</el-descriptions-item>
          <el-descriptions-item label="到期日期">{{ formatDate(reminder.due_date) }}</el-descriptions-item>
          <el-descriptions-item label="关联物品">{{ reminder.item?.name || '-' }}</el-descriptions-item>
          <el-descriptions-item label="借用人">{{ reminder.loan?.borrower_name || '-' }}</el-descriptions-item>
          <el-descriptions-item label="说明" :span="2">{{ reminder.description || '-' }}</el-descriptions-item>
        </el-descriptions>

        <el-alert v-if="reminder.source_type === 'loan_return'" type="info" :closable="false" show-icon>
          借出提醒的到期日期由借出记录维护。
        </el-alert>
      </template>
    </div>
  </el-dialog>
</template>
```

Add scoped styles for `.dialog-header`, `.detail-body`, and `.action-bar` matching the existing modal spacing in `ItemDetailModal.vue`.

- [ ] **Step 2: Add reminder form dialog**

Create `frontend/src/components/reminders/ReminderFormDialog.vue` with props:

```ts
const props = defineProps<{
  modelValue: boolean
  reminder?: ReminderDetail | null
  saving?: boolean
}>()
```

Use an Element Plus form with fields:

```ts
interface ReminderFormState {
  title: string
  description: string
  item_id: number | null
  due_date: string | null
  remind_at: string | null
  priority: 'low' | 'normal' | 'high'
}
```

Emit:

```ts
const emit = defineEmits<{
  'update:modelValue': [value: boolean]
  submit: [payload: ReminderCreateRequest | ReminderUpdateRequest]
}>()
```

The form must disable item and due-date inputs when editing a `loan_return` reminder. The submit payload must trim `title` and send `null` for empty date values.

- [ ] **Step 3: Add reminder center page**

Create `frontend/src/pages/ReminderCenterPage.vue` with:

```vue
<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { storeToRefs } from 'pinia'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Bell, Plus, RefreshLeft } from '@element-plus/icons-vue'

import { getChineseErrorMessage } from '../api/client'
import type { ReminderCreateRequest, ReminderSummary, ReminderUpdateRequest } from '../api/reminders'
import ReminderDetailModal from '../components/reminders/ReminderDetailModal.vue'
import ReminderFormDialog from '../components/reminders/ReminderFormDialog.vue'
import { useAuthStore } from '../stores/auth'
import { useReminderStore } from '../stores/reminders'

const auth = useAuthStore()
const reminders = useReminderStore()
const { reminders: rows, selectedReminder, total, page, pageSize, loading, saving } = storeToRefs(reminders)

const canEdit = computed(() => auth.hasPermission('items:edit'))
const detailOpen = ref(false)
const formOpen = ref(false)
const editingReminder = ref<ReminderSummary | null>(null)
const searchText = ref('')

onMounted(async () => {
  await load()
})

async function load() {
  try {
    await reminders.loadReminders()
  } catch (error) {
    ElMessage.error(getChineseErrorMessage(error))
  }
}
</script>
```

The template must include:

- Page title `提醒中心`.
- Toolbar with search input, status select, source select, upcoming window select, reset button, create button.
- Compact counters computed from loaded rows for overdue, upcoming, pending, done, dismissed.
- `el-table` with columns title, item, source, due state, due date, priority, status, updated time.
- `ReminderDetailModal`.
- `ReminderFormDialog`.

Lifecycle handlers:

```ts
async function openDetail(row: ReminderSummary) {
  await reminders.openDetail(row.id)
  detailOpen.value = true
}

async function saveReminder(payload: ReminderCreateRequest | ReminderUpdateRequest) {
  try {
    if (editingReminder.value) {
      await reminders.updateReminder(editingReminder.value.id, payload)
    } else {
      await reminders.createReminder(payload as ReminderCreateRequest)
    }
    formOpen.value = false
    editingReminder.value = null
    ElMessage.success('已保存提醒')
  } catch (error) {
    ElMessage.error(getChineseErrorMessage(error))
  }
}

async function archiveSelectedReminder() {
  if (!selectedReminder.value) return
  await ElMessageBox.confirm('确定归档这个提醒吗？', '归档提醒', { type: 'warning' })
  await reminders.archiveReminder(selectedReminder.value.id)
  detailOpen.value = false
}
```

- [ ] **Step 4: Register route and navigation**

Modify `frontend/src/router/index.ts` inside authenticated children:

```ts
{
  path: 'reminders',
  name: 'reminders',
  component: () => import('../pages/ReminderCenterPage.vue'),
  meta: { permission: 'items:view' }
}
```

Modify `frontend/src/layouts/AppLayout.vue` import:

```ts
import { Bell, Box, House, Setting, SwitchButton } from '@element-plus/icons-vue'
```

Add menu item after `/items`:

```vue
<PermissionGate permission="items:view">
  <el-menu-item index="/reminders">
    <el-icon><Bell /></el-icon>
    <span>提醒</span>
  </el-menu-item>
</PermissionGate>
```

- [ ] **Step 5: Run build**

Run from `frontend`:

```powershell
npm.cmd run build
```

Expected: PASS.

- [ ] **Step 6: Commit**

```powershell
git add frontend/src/components/reminders/ReminderDetailModal.vue frontend/src/components/reminders/ReminderFormDialog.vue frontend/src/pages/ReminderCenterPage.vue frontend/src/router/index.ts frontend/src/layouts/AppLayout.vue
git commit -m "feat: add reminder center"
```

---

## Task 7: Inventory Reminder Quick Filters

**Files:**
- Modify: `frontend/src/api/inventory.ts`
- Modify: `frontend/src/components/items/ItemFilterPanel.vue`

- [ ] **Step 1: Add item filter types**

Modify `frontend/src/api/inventory.ts` in `ItemFilters`:

```ts
  has_pending_reminder?: boolean | null
  has_upcoming_reminder?: boolean | null
  has_overdue_reminder?: boolean | null
  reminder_upcoming_days?: number
```

- [ ] **Step 2: Add quick filter state**

Modify `frontend/src/components/items/ItemFilterPanel.vue` `quickFilters` computed getter:

```ts
  get: () => [
    ...(inventory.filters.is_on_loan ? ['loan'] : []),
    ...(inventory.filters.container_only ? ['container'] : []),
    ...(inventory.filters.has_pending_reminder ? ['reminder-pending'] : []),
    ...(inventory.filters.has_upcoming_reminder ? ['reminder-upcoming'] : []),
    ...(inventory.filters.has_overdue_reminder ? ['reminder-overdue'] : []),
    ...(inventory.filters.include_archived ? ['archived'] : [])
  ],
```

Modify the setter:

```ts
  set: (values: string[]) => {
    void applyFilters({
      is_on_loan: values.includes('loan') ? true : null,
      container_only: values.includes('container') ? true : null,
      has_pending_reminder: values.includes('reminder-pending') ? true : null,
      has_upcoming_reminder: values.includes('reminder-upcoming') ? true : null,
      has_overdue_reminder: values.includes('reminder-overdue') ? true : null,
      reminder_upcoming_days: 7,
      include_archived: values.includes('archived')
    })
  }
```

- [ ] **Step 3: Add checkbox buttons**

Modify the quick filter template in `frontend/src/components/items/ItemFilterPanel.vue`:

```vue
<el-checkbox-button label="reminder-pending">有待处理提醒</el-checkbox-button>
<el-checkbox-button label="reminder-upcoming">即将到期</el-checkbox-button>
<el-checkbox-button label="reminder-overdue">已逾期</el-checkbox-button>
```

Place the reminder filters after the loan filter and before container/archive filters.

- [ ] **Step 4: Run build**

Run from `frontend`:

```powershell
npm.cmd run build
```

Expected: PASS.

- [ ] **Step 5: Commit**

```powershell
git add frontend/src/api/inventory.ts frontend/src/components/items/ItemFilterPanel.vue
git commit -m "feat: filter items by reminders"
```

---

## Task 8: Final Verification

**Files:**
- No committed source file changes unless a verification failure requires a fix.

- [ ] **Step 1: Run backend tests**

Run from `backend`:

```powershell
python -m pytest -v
```

Expected: all tests pass.

- [ ] **Step 2: Run frontend build**

Run from `frontend`:

```powershell
npm.cmd run build
```

Expected: build exits 0.

- [ ] **Step 3: Run migration smoke**

Run from `backend` against a temporary database:

```powershell
$env:HOMEVAULT_DATABASE_URL='sqlite:///./output/phase4a-smoke.sqlite3'
python -m alembic upgrade head
```

Expected: Alembic reaches head revision `20260620_0005`.

- [ ] **Step 4: Run browser or HTTP smoke**

If browser tooling works, verify these flows:

- Login as admin.
- Open `/reminders`.
- Create a manual reminder.
- Open reminder detail modal.
- Complete and reopen the reminder.
- Open `/items`.
- Apply the overdue or pending reminder filter.

If browser tooling is unavailable, run an HTTP smoke against the local API:

```powershell
python output/smoke/phase4a_reminders_smoke.py
```

The smoke script must login, create an item, create a reminder, list reminders, complete the reminder, and confirm item reminder filters.

- [ ] **Step 5: Check git state**

Run:

```powershell
git status --short --branch
```

Expected: clean working tree after all implementation commits.
