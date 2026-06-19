# HomeVault Phase 3 Inventory Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the complete Phase 3 inventory module: items, custom values, images, attachments, tags, card/table workbench, detail modal, category-driven item form, placement, containers, status changes, loans, returns, and quantity history.

**Architecture:** Keep Phase 3 in an `inventory` backend slice that references Phase 2 configuration models. The backend owns all business rules and history writes; the frontend owns the inventory workbench, form drawer, detail modal, and action dialogs through typed API and Pinia store modules.

**Tech Stack:** FastAPI, SQLAlchemy 2, Alembic, Pydantic, pytest, Vue 3, TypeScript, Pinia, Element Plus, Vite.

---

## Source Specs

- `docs/superpowers/specs/2026-06-19-home-vault-design.md`
- `docs/superpowers/specs/2026-06-19-home-vault-phase-3-inventory-design.md`
- `docs/superpowers/plans/2026-06-19-home-vault-phase-2-core-config.md`

## File Structure

Backend files:

- Create `backend/app/models/inventory.py`: item, custom value, media, tag, movement, quantity, and loan models.
- Modify `backend/app/models/__init__.py`: import inventory models so SQLAlchemy metadata and Alembic see them.
- Create `backend/alembic/versions/20260619_0003_inventory.py`: Phase 3 tables and indexes.
- Create `backend/app/schemas/inventory.py`: request/response models for inventory routes.
- Create `backend/app/services/inventory.py`: item create/edit/list/detail, custom field validation, tag handling, movement/status/quantity/loan/media business logic.
- Create `backend/app/services/uploads.py`: local upload path, content type, file size, and filename helpers.
- Create `backend/app/api/routes/inventory.py`: REST routes under `/items` and `/tags`.
- Modify `backend/app/api/router.py`: include inventory router.
- Modify `backend/app/main.py`: serve uploaded files from `/uploads`.
- Test `backend/tests/test_inventory_models.py`: model and migration coverage.
- Test `backend/tests/test_inventory_services.py`: service business rules.
- Test `backend/tests/test_inventory_api.py`: API contract and permissions.
- Test `backend/tests/test_inventory_uploads.py`: upload helper and route behavior.

Frontend files:

- Create `frontend/src/api/inventory.ts`: typed inventory API client.
- Create `frontend/src/stores/inventory.ts`: Pinia store for list filters, selection, detail payload, and actions.
- Create `frontend/src/pages/ItemsPage.vue`: A-layout inventory workbench.
- Create `frontend/src/components/items/ItemFilterPanel.vue`: location/category/quick filter tree.
- Create `frontend/src/components/items/ItemToolbar.vue`: search, view toggle, sort, add action.
- Create `frontend/src/components/items/ItemCardGrid.vue`: card grid.
- Create `frontend/src/components/items/ItemTable.vue`: table view.
- Create `frontend/src/components/items/ItemDetailModal.vue`: modal detail surface.
- Create `frontend/src/components/items/ItemFormDrawer.vue`: five-step create/edit drawer.
- Create `frontend/src/components/items/ItemActionDialogs.vue`: move, status, borrow, return, quantity, archive dialogs.
- Create `frontend/src/components/items/CustomFieldInputs.vue`: dynamic category field inputs.
- Create `frontend/src/components/items/MediaUploader.vue`: image and attachment uploader.
- Modify `frontend/src/router/index.ts`: route `/items`.
- Modify `frontend/src/layouts/AppLayout.vue`: make the `物品` menu point to `/items`.

---

## Cross-Cutting Contracts

Use these constant values consistently:

```python
MAX_CONTAINER_DEPTH = 5
EXIT_STATUS_SEMANTICS = {"removed", "missing", "consumed"}
IMAGE_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp"}
MAX_IMAGE_BYTES = 5 * 1024 * 1024
MAX_ATTACHMENT_BYTES = 20 * 1024 * 1024
```

Use these Chinese messages in backend service errors:

```python
ITEM_NAME_REQUIRED = "物品名称不能为空"
CATEGORY_REQUIRED = "请选择分类"
PLACEMENT_REQUIRED = "请选择位置或容器"
PLACEMENT_EXCLUSIVE = "请选择位置或容器，不能同时选择两者"
CONTAINER_CYCLE = "这个容器不能放进自己或自己的下级容器中"
CONTAINER_DEPTH = "容器层级不能超过 5 层"
QUANTITY_REASON_REQUIRED = "数量调整必须填写原因"
ACTIVE_LOAN_EXISTS = "该物品已有未归还的借出记录"
UNSUPPORTED_UPLOAD_TYPE = "上传文件类型不支持"
UPLOAD_TOO_LARGE = "上传文件过大"
```

Route permissions:

```python
READ_PERMISSION = "items:view"
CREATE_PERMISSION = "items:create"
EDIT_PERMISSION = "items:edit"
ARCHIVE_PERMISSION = "items:archive"
```

---

## Task 1: Inventory Models And Migration

**Files:**
- Create: `backend/app/models/inventory.py`
- Modify: `backend/app/models/__init__.py`
- Create: `backend/alembic/versions/20260619_0003_inventory.py`
- Test: `backend/tests/test_inventory_models.py`
- Test: `backend/tests/test_database_models.py`

- [ ] **Step 1: Add failing model tests**

Create `backend/tests/test_inventory_models.py` with tests named exactly:

```python
def test_inventory_tables_are_registered() -> None: ...
def test_inventory_models_persist_item_with_tag_media_history_and_loan(db_session: Session) -> None: ...
def test_item_location_and_container_are_mutually_exclusive(db_session: Session) -> None: ...
```

The persistence test must create:

- `Category`, `ItemStatus`, `Residence`, `LocationNode`, and `FamilyMember` configuration records.
- One `Item` named `证件收纳盒`.
- One `ItemAttributeValue`.
- One `Tag` linked through `ItemTag`.
- One primary `ItemImage`.
- One `ItemAttachment`.
- One `ItemMovement`.
- One `ItemQuantityChange`.
- One `ItemLoan`.

Assert that reloading the item returns all relationships through SQLAlchemy relationships.

- [ ] **Step 2: Add failing migration test**

Modify `backend/tests/test_database_models.py` and add:

```python
def test_inventory_migration_upgrade_and_downgrade_temp_sqlite(tmp_path: Path) -> None:
    db_path = tmp_path / "inventory.sqlite3"
    cfg = alembic_config(str(db_path))

    command.upgrade(cfg, "20260619_0003")

    engine = create_engine(f"sqlite:///{db_path}")
    inspector = inspect(engine)
    assert "items" in inspector.get_table_names()
    assert "item_attribute_values" in inspector.get_table_names()
    assert "item_images" in inspector.get_table_names()
    assert "item_attachments" in inspector.get_table_names()
    assert "tags" in inspector.get_table_names()
    assert "item_tags" in inspector.get_table_names()
    assert "item_movements" in inspector.get_table_names()
    assert "item_quantity_changes" in inspector.get_table_names()
    assert "item_loans" in inspector.get_table_names()

    command.downgrade(cfg, "20260619_0002")
    inspector = inspect(engine)
    assert "items" not in inspector.get_table_names()
```

- [ ] **Step 3: Run tests to confirm failure**

Run from `backend`:

```powershell
python -m pytest tests/test_inventory_models.py tests/test_database_models.py::test_inventory_migration_upgrade_and_downgrade_temp_sqlite -v
```

Expected: failures because inventory models and migration do not exist.

- [ ] **Step 4: Create inventory models**

Create `backend/app/models/inventory.py` with these model classes and relationships:

```python
from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Item(Base):
    __tablename__ = "items"
    __table_args__ = (
        CheckConstraint(
            "(location_node_id IS NULL OR container_item_id IS NULL)",
            name="ck_item_location_or_container",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(160), index=True, nullable=False)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    category_id: Mapped[int] = mapped_column(ForeignKey("categories.id", ondelete="RESTRICT"), nullable=False, index=True)
    status_id: Mapped[int] = mapped_column(ForeignKey("item_statuses.id", ondelete="RESTRICT"), nullable=False, index=True)
    quantity: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=1, nullable=False)
    unit: Mapped[str] = mapped_column(String(40), default="件", nullable=False)
    owner_member_id: Mapped[int | None] = mapped_column(ForeignKey("family_members.id", ondelete="SET NULL"), nullable=True)
    keeper_member_id: Mapped[int | None] = mapped_column(ForeignKey("family_members.id", ondelete="SET NULL"), nullable=True)
    location_node_id: Mapped[int | None] = mapped_column(ForeignKey("location_nodes.id", ondelete="SET NULL"), nullable=True, index=True)
    container_item_id: Mapped[int | None] = mapped_column(ForeignKey("items.id", ondelete="SET NULL"), nullable=True, index=True)
    is_container: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    privacy_level: Mapped[str] = mapped_column(String(40), default="normal", nullable=False)
    is_archived: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    archive_reason: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    updated_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)

    category = relationship("Category", lazy="selectin")
    status = relationship("ItemStatus", lazy="selectin")
    owner_member = relationship("FamilyMember", foreign_keys=[owner_member_id], lazy="selectin")
    keeper_member = relationship("FamilyMember", foreign_keys=[keeper_member_id], lazy="selectin")
    location_node = relationship("LocationNode", lazy="selectin")
    container_item = relationship("Item", remote_side=[id], foreign_keys=[container_item_id], lazy="selectin")
    children = relationship("Item", foreign_keys=[container_item_id], lazy="selectin")
    attribute_values = relationship("ItemAttributeValue", back_populates="item", cascade="all, delete-orphan", lazy="selectin")
    images = relationship("ItemImage", back_populates="item", cascade="all, delete-orphan", lazy="selectin")
    attachments = relationship("ItemAttachment", back_populates="item", cascade="all, delete-orphan", lazy="selectin")
    tag_links = relationship("ItemTag", back_populates="item", cascade="all, delete-orphan", lazy="selectin")
    movements = relationship("ItemMovement", back_populates="item", cascade="all, delete-orphan", lazy="selectin")
    quantity_changes = relationship("ItemQuantityChange", back_populates="item", cascade="all, delete-orphan", lazy="selectin")
    loans = relationship("ItemLoan", back_populates="item", cascade="all, delete-orphan", lazy="selectin")
```

Add the remaining classes in the same file with these table contracts:

- `ItemAttributeValue`: `item_id`, `attribute_definition_id`, `value`, unique `(item_id, attribute_definition_id)`.
- `Tag`: `name`, `normalized_name`, unique `normalized_name`.
- `ItemTag`: `item_id`, `tag_id`, unique `(item_id, tag_id)`.
- `ItemImage`: item file metadata, `is_primary`, `sort_order`, `is_archived`.
- `ItemAttachment`: item file metadata, `is_archived`.
- `ItemMovement`: previous/new location, container, status, `movement_type`, `reason`, `note`, `actor_id`.
- `ItemQuantityChange`: quantity before/after/delta, unit, reason, note, actor.
- `ItemLoan`: borrower, contact, expected return, loan/return notes, returned_at, return placement, actor fields.

- [ ] **Step 5: Import models**

Modify `backend/app/models/__init__.py` to import inventory models beside auth and configuration models:

```python
from app.models.auth import ExternalIdentity, Permission, Role, RolePermission, User, UserRole, UserSession
from app.models.configuration import (
    AttributeDefinition,
    AttributeOption,
    Category,
    DictionaryGroup,
    DictionaryOption,
    FamilyMember,
    HomeSpace,
    ItemStatus,
    LocationNode,
    Residence,
)
from app.models.inventory import (
    Item,
    ItemAttachment,
    ItemAttributeValue,
    ItemImage,
    ItemLoan,
    ItemMovement,
    ItemQuantityChange,
    ItemTag,
    Tag,
)
```

- [ ] **Step 6: Create migration**

Create `backend/alembic/versions/20260619_0003_inventory.py` with:

```python
revision = "20260619_0003"
down_revision = "20260619_0002"
branch_labels = None
depends_on = None
```

The migration must create tables in this order:

1. `items`
2. `tags`
3. `item_attribute_values`
4. `item_images`
5. `item_attachments`
6. `item_tags`
7. `item_movements`
8. `item_quantity_changes`
9. `item_loans`

Downgrade must drop them in reverse order.

- [ ] **Step 7: Run model and migration tests**

Run from `backend`:

```powershell
python -m pytest tests/test_inventory_models.py tests/test_database_models.py::test_inventory_migration_upgrade_and_downgrade_temp_sqlite -v
```

Expected: all targeted tests pass.

- [ ] **Step 8: Commit**

```powershell
git add backend/app/models/inventory.py backend/app/models/__init__.py backend/alembic/versions/20260619_0003_inventory.py backend/tests/test_inventory_models.py backend/tests/test_database_models.py
git commit -m "feat: add inventory data model"
```

---

## Task 2: Inventory Schemas And Read Serialization

**Files:**
- Create: `backend/app/schemas/inventory.py`
- Create: `backend/tests/test_inventory_schemas.py`

- [ ] **Step 1: Add failing schema tests**

Create `backend/tests/test_inventory_schemas.py` with tests named:

```python
def test_item_create_requires_name_and_category() -> None: ...
def test_item_list_query_defaults_hide_archived_items() -> None: ...
def test_item_detail_response_serializes_nested_inventory_payload() -> None: ...
```

The tests must instantiate Pydantic models directly and assert:

- Empty name fails for `ItemCreate`.
- `ItemListQuery().include_archived is False`.
- `ItemDetailResponse` accepts nested image, attachment, tag, custom value, movement, quantity, and loan payloads.

- [ ] **Step 2: Run schema tests to confirm failure**

Run from `backend`:

```powershell
python -m pytest tests/test_inventory_schemas.py -v
```

Expected: import failure for `app.schemas.inventory`.

- [ ] **Step 3: Create schema module**

Create `backend/app/schemas/inventory.py` with these model groups:

```python
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ResponseModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class PlacementPayload(BaseModel):
    location_node_id: int | None = None
    container_item_id: int | None = None

    @model_validator(mode="after")
    def validate_single_placement(self) -> PlacementPayload:
        if self.location_node_id is not None and self.container_item_id is not None:
            raise ValueError("请选择位置或容器，不能同时选择两者")
        return self


class ItemAttributeValueInput(BaseModel):
    attribute_definition_id: int
    value: str = ""


class ItemCreate(PlacementPayload):
    name: str = Field(min_length=1, max_length=160)
    description: str = ""
    category_id: int
    status_id: int
    quantity: Decimal = Decimal("1")
    unit: str = "件"
    owner_member_id: int | None = None
    keeper_member_id: int | None = None
    is_container: bool = False
    privacy_level: str = "normal"
    attribute_values: list[ItemAttributeValueInput] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
```

Also add:

- `ItemUpdate`
- `ItemListQuery`
- `ItemSummaryResponse`
- `ItemDetailResponse`
- `TagResponse`
- `ItemImageResponse`
- `ItemAttachmentResponse`
- `ItemMovementResponse`
- `ItemQuantityChangeResponse`
- `ItemLoanResponse`
- `MoveItemRequest`
- `ChangeStatusRequest`
- `QuantityAdjustmentCreate`
- `LoanCreate`
- `LoanReturn`
- `ArchiveItemRequest`
- `MediaMetadataResponse`

- [ ] **Step 4: Run schema tests**

Run from `backend`:

```powershell
python -m pytest tests/test_inventory_schemas.py -v
```

Expected: all schema tests pass.

- [ ] **Step 5: Commit**

```powershell
git add backend/app/schemas/inventory.py backend/tests/test_inventory_schemas.py
git commit -m "feat: add inventory schemas"
```

---

## Task 3: Create, Edit, List, Detail, Tags, And Custom Fields

**Files:**
- Create: `backend/app/services/inventory.py`
- Test: `backend/tests/test_inventory_services.py`

- [ ] **Step 1: Add failing service tests**

Create `backend/tests/test_inventory_services.py` with fixtures that seed:

- `HomeSpace`, `Residence`, `LocationNode`, `FamilyMember`
- `Category`
- `AttributeDefinition` for `expire_date`, `serial_number`, and `importance`
- `AttributeOption` for `importance`
- `ItemStatus` values `in_stock` and `loaned`

Add tests named:

```python
def test_create_item_persists_custom_values_tags_initial_quantity_and_location(db_session: Session) -> None: ...
def test_create_item_rejects_required_missing_custom_value(db_session: Session) -> None: ...
def test_create_item_rejects_invalid_select_value(db_session: Session) -> None: ...
def test_list_items_searches_name_tag_and_custom_value(db_session: Session) -> None: ...
def test_item_detail_includes_tags_custom_values_and_paths(db_session: Session) -> None: ...
def test_update_item_does_not_change_quantity_silently(db_session: Session) -> None: ...
def test_archive_item_hides_from_default_list(db_session: Session) -> None: ...
```

- [ ] **Step 2: Run service tests to confirm failure**

Run from `backend`:

```powershell
python -m pytest tests/test_inventory_services.py -v
```

Expected: import failure for `app.services.inventory`.

- [ ] **Step 3: Create inventory service constants and helpers**

Create `backend/app/services/inventory.py` with:

```python
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.core.errors import bad_request, not_found
from app.models.configuration import AttributeDefinition, AttributeOption, Category, ItemStatus, LocationNode
from app.models.inventory import (
    Item,
    ItemAttributeValue,
    ItemLoan,
    ItemMovement,
    ItemQuantityChange,
    ItemTag,
    Tag,
)
from app.schemas.inventory import (
    ArchiveItemRequest,
    ItemCreate,
    ItemDetailResponse,
    ItemListQuery,
    ItemSummaryResponse,
    ItemUpdate,
)

MAX_CONTAINER_DEPTH = 5
EXIT_STATUS_SEMANTICS = {"removed", "missing", "consumed"}
```

Add helper functions:

```python
def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def normalize_tag(name: str) -> str:
    return " ".join(name.strip().lower().split())


def require_item(db: Session, item_id: int) -> Item:
    item = db.get(Item, item_id)
    if item is None:
        raise not_found("物品不存在")
    return item
```

- [ ] **Step 4: Implement custom field validation**

Add:

```python
def validate_attribute_values(
    db: Session,
    category_id: int,
    values: list[ItemAttributeValueInput],
) -> dict[int, str]:
    definitions = db.scalars(
        select(AttributeDefinition)
        .where(AttributeDefinition.category_id == category_id)
        .options(selectinload(AttributeDefinition.options))
    ).all()
    active_definitions = [definition for definition in definitions if definition.is_active]
    value_by_definition_id = {value.attribute_definition_id: value.value for value in values}

    for definition in active_definitions:
        raw_value = value_by_definition_id.get(definition.id, "").strip()
        if definition.is_required and raw_value == "":
            raise bad_request(f"{definition.name}不能为空")
        if raw_value == "":
            continue
        assert_attribute_value_matches_definition(definition, raw_value)

    return {
        definition_id: raw_value.strip()
        for definition_id, raw_value in value_by_definition_id.items()
    }
```

`assert_attribute_value_matches_definition` must validate `number`, `money`, `date`, `datetime`, `boolean`, `single_select`, and `multi_select` without trusting the frontend.

- [ ] **Step 5: Implement create, update, archive, list, and detail**

Add service functions:

```python
def create_item(db: Session, payload: ItemCreate, actor_id: int | None) -> ItemDetailResponse: ...
def update_item(db: Session, item_id: int, payload: ItemUpdate, actor_id: int | None) -> ItemDetailResponse: ...
def archive_item(db: Session, item_id: int, payload: ArchiveItemRequest, actor_id: int | None) -> ItemDetailResponse: ...
def list_items(db: Session, query: ItemListQuery) -> list[ItemSummaryResponse]: ...
def get_item_detail(db: Session, item_id: int) -> ItemDetailResponse: ...
```

`create_item` must:

- Reject empty names through Pydantic and through a defensive `strip()`.
- Confirm category and status exist.
- Validate basic placement with a local `validate_basic_placement` helper that rejects location/container mutual selection and missing placement when status is not exit-style.
- Write item row.
- Replace custom values with validated rows.
- Upsert tags by normalized name.
- Write initial `ItemQuantityChange` with reason `初始数量`.
- Commit once.

`update_item` must not change quantity, location, container, or status.

`archive_item` must set `is_archived`, `archive_reason`, and `archived_at`.

`list_items` must hide archived items unless `include_archived` is true.

- [ ] **Step 6: Run service tests**

Run from `backend`:

```powershell
python -m pytest tests/test_inventory_services.py -v
```

Expected: Task 3 service tests pass.

- [ ] **Step 7: Commit**

```powershell
git add backend/app/services/inventory.py backend/tests/test_inventory_services.py
git commit -m "feat: add inventory item services"
```

---

## Task 4: Placement, Container, Status, Quantity, And Loan Services

**Files:**
- Modify: `backend/app/services/inventory.py`
- Test: `backend/tests/test_inventory_services.py`

- [ ] **Step 1: Add failing lifecycle service tests**

Append tests named:

```python
def test_move_item_writes_movement_history(db_session: Session) -> None: ...
def test_move_item_rejects_location_and_container_together(db_session: Session) -> None: ...
def test_move_item_rejects_container_cycle(db_session: Session) -> None: ...
def test_move_item_rejects_container_depth_over_five(db_session: Session) -> None: ...
def test_change_status_to_exit_status_clears_placement_and_writes_history(db_session: Session) -> None: ...
def test_adjust_quantity_requires_reason_and_writes_history(db_session: Session) -> None: ...
def test_create_loan_rejects_second_active_loan(db_session: Session) -> None: ...
def test_return_loan_sets_return_placement_and_history(db_session: Session) -> None: ...
```

- [ ] **Step 2: Run lifecycle tests to confirm failure**

Run from `backend`:

```powershell
python -m pytest tests/test_inventory_services.py -k "move_item or status or quantity or loan" -v
```

Expected: failures for missing service functions.

- [ ] **Step 3: Implement placement validation**

Add these service functions:

```python
def validate_placement(
    db: Session,
    *,
    item_id: int | None,
    location_node_id: int | None,
    container_item_id: int | None,
    status: ItemStatus,
) -> None:
    if location_node_id is not None and container_item_id is not None:
        raise bad_request("请选择位置或容器，不能同时选择两者")
    if status.semantic not in EXIT_STATUS_SEMANTICS and location_node_id is None and container_item_id is None:
        raise bad_request("请选择位置或容器")
    if location_node_id is not None and db.get(LocationNode, location_node_id) is None:
        raise bad_request("位置不存在")
    if container_item_id is not None:
        validate_container_target(db, item_id=item_id, container_item_id=container_item_id)
```

`validate_container_target` must:

- Confirm target item exists.
- Confirm target `is_container` is true.
- Reject `item_id == container_item_id`.
- Walk up `container_item_id` links to reject descendants and depth over 5.

- [ ] **Step 4: Implement move and status services**

Add:

```python
def move_item(db: Session, item_id: int, payload: MoveItemRequest, actor_id: int | None) -> ItemDetailResponse: ...
def change_item_status(db: Session, item_id: int, payload: ChangeStatusRequest, actor_id: int | None) -> ItemDetailResponse: ...
```

Both functions must create an `ItemMovement` row containing previous and new placement/status values.

- [ ] **Step 5: Implement quantity services**

Add:

```python
def adjust_quantity(db: Session, item_id: int, payload: QuantityAdjustmentCreate, actor_id: int | None) -> ItemDetailResponse: ...
def list_quantity_changes(db: Session, item_id: int) -> list[ItemQuantityChangeResponse]: ...
```

Reject blank reason. Allow either `new_quantity` or `delta`, with `new_quantity` taking precedence. Store before, after, and delta.

- [ ] **Step 6: Implement loan services**

Add:

```python
def create_loan(db: Session, item_id: int, payload: LoanCreate, actor_id: int | None) -> ItemDetailResponse: ...
def return_loan(db: Session, item_id: int, loan_id: int, payload: LoanReturn, actor_id: int | None) -> ItemDetailResponse: ...
```

`create_loan` must reject an active loan. `return_loan` must set `returned_at`, return placement, and return note. Both must write movement/status history.

- [ ] **Step 7: Run lifecycle tests**

Run from `backend`:

```powershell
python -m pytest tests/test_inventory_services.py -v
```

Expected: all inventory service tests pass.

- [ ] **Step 8: Commit**

```powershell
git add backend/app/services/inventory.py backend/tests/test_inventory_services.py
git commit -m "feat: add inventory lifecycle services"
```

---

## Task 5: Upload Helpers And Media Services

**Files:**
- Create: `backend/app/services/uploads.py`
- Modify: `backend/app/services/inventory.py`
- Modify: `backend/app/main.py`
- Test: `backend/tests/test_inventory_uploads.py`

- [ ] **Step 1: Add failing upload tests**

Create `backend/tests/test_inventory_uploads.py` with tests named:

```python
def test_image_upload_rejects_unsupported_type(tmp_path: Path) -> None: ...
def test_image_upload_rejects_large_file(tmp_path: Path) -> None: ...
def test_store_upload_generates_safe_filename(tmp_path: Path) -> None: ...
def test_archive_image_and_attachment_hide_media_from_detail(db_session: Session, tmp_path: Path) -> None: ...
```

- [ ] **Step 2: Run upload tests to confirm failure**

Run from `backend`:

```powershell
python -m pytest tests/test_inventory_uploads.py -v
```

Expected: import failure for `app.services.uploads`.

- [ ] **Step 3: Create upload helper**

Create `backend/app/services/uploads.py` with:

```python
from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from fastapi import UploadFile

from app.core.config import get_settings
from app.core.errors import bad_request

IMAGE_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp"}
MAX_IMAGE_BYTES = 5 * 1024 * 1024
MAX_ATTACHMENT_BYTES = 20 * 1024 * 1024


def safe_extension(filename: str) -> str:
    suffix = Path(filename).suffix.lower()
    return suffix if suffix in {".jpg", ".jpeg", ".png", ".webp", ".pdf", ".txt", ".doc", ".docx", ".xls", ".xlsx"} else ""


def build_storage_name(filename: str) -> str:
    return f"{uuid4().hex}{safe_extension(filename)}"


async def store_upload(upload: UploadFile, *, item_id: int, media_type: str) -> tuple[str, int]:
    settings = get_settings()
    root = Path(settings.upload_dir)
    target_dir = root / "items" / str(item_id) / media_type
    target_dir.mkdir(parents=True, exist_ok=True)

    content = await upload.read()
    limit = MAX_IMAGE_BYTES if media_type == "images" else MAX_ATTACHMENT_BYTES
    if len(content) > limit:
        raise bad_request("上传文件过大")

    stored_name = build_storage_name(upload.filename or "upload")
    target_path = target_dir / stored_name
    target_path.write_bytes(content)
    return str(target_path.relative_to(root)).replace("\\", "/"), len(content)
```

- [ ] **Step 4: Add media services**

In `backend/app/services/inventory.py`, add:

```python
async def add_item_image(db: Session, item_id: int, upload: UploadFile, is_primary: bool, actor_id: int | None) -> ItemImageResponse: ...
async def add_item_attachment(db: Session, item_id: int, upload: UploadFile, actor_id: int | None) -> ItemAttachmentResponse: ...
def archive_item_image(db: Session, item_id: int, image_id: int, actor_id: int | None) -> ItemDetailResponse: ...
def archive_item_attachment(db: Session, item_id: int, attachment_id: int, actor_id: int | None) -> ItemDetailResponse: ...
```

Validate image content types against `IMAGE_CONTENT_TYPES`. If `is_primary` is true, set all other active images on the item to false.

- [ ] **Step 5: Serve uploads**

Modify `backend/app/main.py`:

```python
from fastapi.staticfiles import StaticFiles
```

Inside `create_app`, after router inclusion:

```python
application.mount("/uploads", StaticFiles(directory=settings.upload_dir), name="uploads")
```

- [ ] **Step 6: Run upload tests**

Run from `backend`:

```powershell
python -m pytest tests/test_inventory_uploads.py -v
```

Expected: all upload tests pass.

- [ ] **Step 7: Commit**

```powershell
git add backend/app/services/uploads.py backend/app/services/inventory.py backend/app/main.py backend/tests/test_inventory_uploads.py
git commit -m "feat: add inventory media handling"
```

---

## Task 6: Inventory API Routes And Permissions

**Files:**
- Create: `backend/app/api/routes/inventory.py`
- Modify: `backend/app/api/router.py`
- Test: `backend/tests/test_inventory_api.py`

- [ ] **Step 1: Add failing API tests**

Create `backend/tests/test_inventory_api.py` with tests named:

```python
def test_admin_can_create_list_detail_update_and_archive_item(client: TestClient) -> None: ...
def test_editor_can_create_move_borrow_return_and_adjust_quantity(client: TestClient) -> None: ...
def test_viewer_can_read_but_cannot_write_inventory(client: TestClient) -> None: ...
def test_inventory_api_rejects_container_cycle(client: TestClient) -> None: ...
def test_inventory_api_uploads_image_and_attachment(client: TestClient) -> None: ...
```

Use the existing auth test pattern from `backend/tests/test_configuration_api.py`. Seed admin/editor/viewer users through `seed_auth_baseline` plus role assignment.

- [ ] **Step 2: Run API tests to confirm failure**

Run from `backend`:

```powershell
python -m pytest tests/test_inventory_api.py -v
```

Expected: routes return 404.

- [ ] **Step 3: Create routes**

Create `backend/app/api/routes/inventory.py` with:

```python
from fastapi import APIRouter, Depends, File, UploadFile, status
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_permission
from app.models.auth import User
from app.schemas.inventory import (
    ArchiveItemRequest,
    ChangeStatusRequest,
    ItemCreate,
    ItemDetailResponse,
    ItemListQuery,
    ItemSummaryResponse,
    ItemUpdate,
    LoanCreate,
    LoanReturn,
    MoveItemRequest,
    QuantityAdjustmentCreate,
)
from app.services import inventory as inventory_service

router = APIRouter(tags=["inventory"])
```

Add endpoints matching the Phase 3 design:

- `GET /items`
- `POST /items`
- `GET /items/{item_id}`
- `PATCH /items/{item_id}`
- `POST /items/{item_id}/archive`
- `POST /items/{item_id}/move`
- `POST /items/{item_id}/status`
- `POST /items/{item_id}/quantity-adjustments`
- `GET /items/{item_id}/quantity-adjustments`
- `POST /items/{item_id}/loans`
- `POST /items/{item_id}/loans/{loan_id}/return`
- `GET /items/{item_id}/movements`
- `POST /items/{item_id}/images`
- `PATCH /items/{item_id}/images/{image_id}`
- `DELETE /items/{item_id}/images/{image_id}`
- `POST /items/{item_id}/attachments`
- `DELETE /items/{item_id}/attachments/{attachment_id}`
- `GET /tags`
- `POST /tags`

- [ ] **Step 4: Include router**

Modify `backend/app/api/router.py`:

```python
from app.api.routes import auth, configuration, health, inventory

api_router.include_router(inventory.router)
```

- [ ] **Step 5: Run API tests**

Run from `backend`:

```powershell
python -m pytest tests/test_inventory_api.py -v
```

Expected: all inventory API tests pass.

- [ ] **Step 6: Run full backend tests**

Run from `backend`:

```powershell
python -m pytest -v
```

Expected: all backend tests pass.

- [ ] **Step 7: Commit**

```powershell
git add backend/app/api/routes/inventory.py backend/app/api/router.py backend/tests/test_inventory_api.py
git commit -m "feat: add inventory api"
```

---

## Task 7: Frontend Inventory API And Store

**Files:**
- Create: `frontend/src/api/inventory.ts`
- Create: `frontend/src/stores/inventory.ts`

- [ ] **Step 1: Create typed API client**

Create `frontend/src/api/inventory.ts` exporting interfaces:

```ts
export interface ItemSummary {
  id: number
  name: string
  description: string
  category_id: number
  category_name: string
  status_id: number
  status_name: string
  status_semantic: string
  quantity: string
  unit: string
  location_label: string
  container_label: string
  primary_image_url: string
  tags: Tag[]
  is_container: boolean
  is_archived: boolean
}

export interface ItemDetail extends ItemSummary {
  attribute_values: ItemAttributeValue[]
  images: ItemImage[]
  attachments: ItemAttachment[]
  movements: ItemMovement[]
  quantity_changes: ItemQuantityChange[]
  loans: ItemLoan[]
}
```

Add request types and functions for every route in Task 6. Use `FormData` for image and attachment uploads.

- [ ] **Step 2: Create Pinia store**

Create `frontend/src/stores/inventory.ts` with state:

```ts
interface InventoryState {
  items: ItemSummary[]
  selectedItem: ItemDetail | null
  loading: boolean
  saving: boolean
  viewMode: 'cards' | 'table'
  filters: ItemFilters
}
```

Actions:

- `loadItems`
- `openDetail`
- `createItem`
- `updateItem`
- `archiveItem`
- `moveItem`
- `changeStatus`
- `adjustQuantity`
- `borrowItem`
- `returnLoan`
- `uploadImage`
- `uploadAttachment`
- `closeDetail`

Each write action reloads the detail payload and list payload after success.

- [ ] **Step 3: Build frontend**

Run from `frontend`:

```powershell
npm.cmd run build
```

Expected: TypeScript compiles and Vite build finishes.

- [ ] **Step 4: Commit**

```powershell
git add frontend/src/api/inventory.ts frontend/src/stores/inventory.ts
git commit -m "feat: add inventory frontend data layer"
```

---

## Task 8: Inventory Workbench Page

**Files:**
- Create: `frontend/src/pages/ItemsPage.vue`
- Create: `frontend/src/components/items/ItemFilterPanel.vue`
- Create: `frontend/src/components/items/ItemToolbar.vue`
- Create: `frontend/src/components/items/ItemCardGrid.vue`
- Create: `frontend/src/components/items/ItemTable.vue`
- Modify: `frontend/src/router/index.ts`
- Modify: `frontend/src/layouts/AppLayout.vue`

- [ ] **Step 1: Add `/items` route and menu**

Modify router:

```ts
{
  path: 'items',
  name: 'items',
  component: () => import('../pages/ItemsPage.vue'),
  meta: { permission: 'items:view' }
}
```

Modify `AppLayout.vue` so the `物品` menu item points to `/items`, not `/`.

- [ ] **Step 2: Create workbench page**

Create `ItemsPage.vue` with:

- Page title `物品`.
- Left filter panel.
- Right work area.
- Loading state from inventory store.
- Error messages via `getChineseErrorMessage`.
- Add button shown only when `auth.hasPermission('items:create')`.

- [ ] **Step 3: Create filter panel**

`ItemFilterPanel.vue` must render:

- Residence/location tree from `useConfigurationStore`.
- Category tree from `useConfigurationStore`.
- Quick filters: `借出未归还`, `容器物品`, `已归档`.

On selection, update inventory store filters and call `loadItems`.

- [ ] **Step 4: Create toolbar**

`ItemToolbar.vue` must render:

- Search input.
- Card/table segmented control.
- Sort selector.
- Add item button.

- [ ] **Step 5: Create card and table views**

`ItemCardGrid.vue` must emit `open-detail` with item id.

`ItemTable.vue` must emit `open-detail` with item id.

Both must show empty state text `还没有物品`.

- [ ] **Step 6: Build frontend**

Run from `frontend`:

```powershell
npm.cmd run build
```

Expected: build passes.

- [ ] **Step 7: Commit**

```powershell
git add frontend/src/pages/ItemsPage.vue frontend/src/components/items/ItemFilterPanel.vue frontend/src/components/items/ItemToolbar.vue frontend/src/components/items/ItemCardGrid.vue frontend/src/components/items/ItemTable.vue frontend/src/router/index.ts frontend/src/layouts/AppLayout.vue
git commit -m "feat: add inventory workbench"
```

---

## Task 9: Item Form Drawer, Detail Modal, And Action Dialogs

**Files:**
- Create: `frontend/src/components/items/ItemFormDrawer.vue`
- Create: `frontend/src/components/items/ItemDetailModal.vue`
- Create: `frontend/src/components/items/ItemActionDialogs.vue`
- Create: `frontend/src/components/items/CustomFieldInputs.vue`
- Create: `frontend/src/components/items/MediaUploader.vue`
- Modify: `frontend/src/pages/ItemsPage.vue`

- [ ] **Step 1: Create dynamic custom field inputs**

`CustomFieldInputs.vue` receives:

```ts
interface Props {
  definitions: AttributeDefinition[]
  modelValue: Record<number, string>
}
```

It emits `update:modelValue`. Render Element Plus controls by `field_type`:

- `text`, `encrypted_text`, `url`: `el-input`
- `long_text`: textarea input
- `number`, `money`: `el-input-number`
- `date`: `el-date-picker` with `value-format="YYYY-MM-DD"`
- `datetime`: `el-date-picker` with `type="datetime"` and ISO-like value format
- `single_select`: `el-select`
- `multi_select`: multi `el-select`
- `boolean`: `el-switch`
- `attachment`: read-only hint telling the user to use the attachment step
- `reminder_date`: date picker

- [ ] **Step 2: Create form drawer**

`ItemFormDrawer.vue` implements five steps:

1. Category.
2. Basic information.
3. Location or container.
4. Custom fields.
5. Images and attachments.

Client-side validation:

- Name required.
- Category required.
- Location/container mutual exclusion.
- Required active custom fields required.

On save, call `inventory.createItem` or `inventory.updateItem`. Upload selected images and attachments after item creation succeeds.

- [ ] **Step 3: Create detail modal**

`ItemDetailModal.vue` uses `el-dialog` and tabs:

- 概览
- 自定义字段
- 图片附件
- 移动历史
- 数量历史
- 借出记录

Primary actions are visible according to permissions:

- `items:edit`: 编辑, 移动, 状态, 借出, 归还, 调整数量
- `items:archive`: 归档

- [ ] **Step 4: Create action dialogs**

`ItemActionDialogs.vue` contains dialogs for:

- Move.
- Change status.
- Borrow.
- Return.
- Quantity adjustment.
- Archive.

Each successful action calls the matching inventory store method and shows a Chinese success message.

- [ ] **Step 5: Create media uploader**

`MediaUploader.vue` supports image and attachment upload queues. It shows selected filenames before save and existing media in detail/edit mode.

- [ ] **Step 6: Wire components into page**

Modify `ItemsPage.vue`:

- Open detail modal when a card/table row is clicked.
- Open form drawer from add and edit actions.
- Keep detail modal open after action dialogs succeed.
- Reload list after create, edit, archive, move, loan, return, or quantity adjustment.

- [ ] **Step 7: Build frontend**

Run from `frontend`:

```powershell
npm.cmd run build
```

Expected: build passes.

- [ ] **Step 8: Commit**

```powershell
git add frontend/src/components/items/ItemFormDrawer.vue frontend/src/components/items/ItemDetailModal.vue frontend/src/components/items/ItemActionDialogs.vue frontend/src/components/items/CustomFieldInputs.vue frontend/src/components/items/MediaUploader.vue frontend/src/pages/ItemsPage.vue
git commit -m "feat: add inventory item workflows"
```

---

## Task 10: End-To-End Verification And Phase 3 Polish

**Files:**
- Modify as needed: backend/frontend files touched by verification fixes.
- Create screenshots under `output/playwright/` only if browser smoke produces them. The directory is ignored.

- [ ] **Step 1: Run full backend tests**

Run from `backend`:

```powershell
python -m pytest -v
```

Expected: all backend tests pass.

- [ ] **Step 2: Run frontend build**

Run from `frontend`:

```powershell
npm.cmd run build
```

Expected: TypeScript and Vite build pass.

- [ ] **Step 3: Verify migration and seed**

Run from `backend`:

```powershell
python -m alembic upgrade head
python -m app.cli
```

Expected: migration reaches head and CLI prints `管理员账号已就绪: admin`.

- [ ] **Step 4: Browser smoke**

Start backend and frontend dev servers. In browser:

1. Log in as `admin` / `ChangeMe123!`.
2. Open `物品`.
3. Create a residence, location, member, category, and category fields if the local database has no Phase 2 config data.
4. Create a container item `证件收纳盒` with a primary image, attachment, tag, custom field value, quantity, and location.
5. Create a second item and place it inside `证件收纳盒`.
6. Search and filter by text and tag.
7. Open detail modal.
8. Move the item to another location.
9. Borrow and return the item.
10. Adjust quantity.
11. Confirm movement, loan, and quantity histories display.
12. Create or use a viewer account and confirm write actions are hidden or rejected.

Save screenshots:

- `output/playwright/phase-3-inventory-workbench.png`
- `output/playwright/phase-3-item-detail-modal.png`
- `output/playwright/phase-3-item-form.png`

- [ ] **Step 5: Fix verification issues**

If verification reveals defects, fix only Phase 3 files. Run the smallest failing test/build first, then rerun the full backend and frontend commands from Steps 1 and 2.

- [ ] **Step 6: Final review**

Use `superpowers:requesting-code-review` for a Phase 3 review. Required review focus:

- Inventory business rules.
- Permission boundaries.
- Upload safety.
- Container cycle/depth logic.
- Quantity and loan history integrity.
- Frontend action visibility.
- Browser smoke coverage.

- [ ] **Step 7: Commit final fixes**

If Step 5 changed files:

```powershell
git add backend frontend docs
git commit -m "fix: polish phase 3 inventory verification"
```

If no files changed, do not create an empty commit.

---

## Self-Review

Spec coverage:

- Data model coverage: Task 1.
- Schemas and response payloads: Task 2.
- Item create/edit/list/detail, tags, custom fields: Task 3.
- Placement, containers, status, quantity, loans: Task 4.
- Images and attachments: Task 5.
- REST API and permissions: Task 6.
- Frontend API/store: Task 7.
- Workbench A layout: Task 8.
- Detail modal, form drawer, action dialogs: Task 9.
- Full verification and browser acceptance: Task 10.

Scope control:

- Phase 4 reminder center, global audit log UI, role management screens, external notifications, QR code workflows, mobile screens, and import/export are not included.

Type consistency:

- Backend route, schema, and service names match across Tasks 2, 3, 4, 5, and 6.
- Frontend API, store, page, and component names match across Tasks 7, 8, and 9.
