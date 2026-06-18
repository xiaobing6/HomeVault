# HomeVault Phase 2 Core Configuration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the core configuration module that Phase 3 inventory depends on: home space, residences, custom location trees, family members, category tree, attribute definitions/options, item statuses, and dictionaries.

**Architecture:** The backend keeps configuration as normalized SQLAlchemy models with REST APIs guarded by existing RBAC permissions. The frontend adds an admin configuration area under the existing authenticated shell, using Element Plus tabs and forms for dense operational workflows. This phase creates working, testable configuration data without creating inventory items yet.

**Tech Stack:** FastAPI, SQLAlchemy 2, Alembic, Pydantic, pytest, Vue 3, Pinia, Vue Router, Element Plus, Axios, Playwright verification.

---

## Scope Check

Phase 2 covers only reusable configuration data. It does not create item cards, item images, item details, item movements, loans, quantity history, reminders, or logs beyond existing auth behavior. Those stay in Phase 3 and Phase 4.

## File Structure

Backend files:

- Create `backend/app/models/configuration.py`: SQLAlchemy models for home space, residences, location tree, family members, categories, attribute definitions, attribute options, item statuses, dictionary groups, and dictionary options.
- Modify `backend/app/models/__init__.py`: export configuration models so metadata and Alembic can see them.
- Create `backend/alembic/versions/20260619_0002_core_configuration.py`: migration for configuration tables.
- Create `backend/app/schemas/configuration.py`: Pydantic request/response schemas and tree node shapes.
- Create `backend/app/services/configuration.py`: create/update/list helpers, tree loading, parent validation, unique checks, and default seed helpers.
- Modify `backend/app/services/seed.py`: seed default home space, statuses, and basic dictionaries in addition to auth baseline.
- Create `backend/app/api/routes/configuration.py`: REST endpoints under `/api/config`.
- Modify `backend/app/api/router.py`: include configuration routes.
- Create `backend/tests/test_configuration_models.py`: model and migration tests.
- Create `backend/tests/test_configuration_api.py`: API and permission tests.
- Create `backend/tests/test_configuration_seed.py`: default seed idempotency tests.

Frontend files:

- Create `frontend/src/api/configuration.ts`: typed API client for configuration endpoints.
- Create `frontend/src/stores/configuration.ts`: Pinia store for dashboard/admin pages.
- Modify `frontend/src/router/index.ts`: replace the admin placeholder with `/admin/config`.
- Modify `frontend/src/layouts/AppLayout.vue`: point 后台管理 to `/admin/config`.
- Create `frontend/src/pages/CoreConfigPage.vue`: tabbed admin UI.
- Create `frontend/src/components/config/ResidenceLocationPanel.vue`: residence list and location tree editor.
- Create `frontend/src/components/config/FamilyMemberPanel.vue`: member editor.
- Create `frontend/src/components/config/CategoryFieldPanel.vue`: category tree and attribute field editor.
- Create `frontend/src/components/config/DictionaryPanel.vue`: status and dictionary option editor.

Verification files:

- Use temporary files in `output/playwright/` for browser smoke scripts and screenshots. Do not commit them unless the user explicitly wants evidence committed.

---

## Backend API Contract

All endpoints require a valid bearer token.

Read endpoints require `items:view`:

- `GET /api/config/bootstrap`
- `GET /api/config/residences`
- `GET /api/config/location-tree`
- `GET /api/config/family-members`
- `GET /api/config/categories`
- `GET /api/config/item-statuses`
- `GET /api/config/dictionaries`

Write endpoints require `config:manage`:

- `PUT /api/config/home-space`
- `POST /api/config/residences`
- `PATCH /api/config/residences/{residence_id}`
- `POST /api/config/location-nodes`
- `PATCH /api/config/location-nodes/{node_id}`
- `POST /api/config/family-members`
- `PATCH /api/config/family-members/{member_id}`
- `POST /api/config/categories`
- `PATCH /api/config/categories/{category_id}`
- `POST /api/config/attribute-definitions`
- `PATCH /api/config/attribute-definitions/{definition_id}`
- `POST /api/config/attribute-options`
- `PATCH /api/config/attribute-options/{option_id}`
- `POST /api/config/item-statuses`
- `PATCH /api/config/item-statuses/{status_id}`
- `POST /api/config/dictionary-groups`
- `POST /api/config/dictionary-options`

Validation rules:

- There is exactly one active home space in Phase 2.
- Residence names are unique among active residences.
- Location nodes belong to one residence; parent and child must share the same residence.
- Location nodes cannot use themselves as parent.
- Category parent and child must not create a cycle.
- Attribute field keys are unique within one category.
- Option values are unique within one attribute definition.
- System item statuses cannot be deleted; Phase 2 uses `is_active=false` instead of deletion.
- Writes return Chinese validation messages through the existing `{ "message": "..." }` error format.

---

## Task 1: Backend Configuration Models And Migration

**Files:**
- Create: `backend/app/models/configuration.py`
- Modify: `backend/app/models/__init__.py`
- Create: `backend/alembic/versions/20260619_0002_core_configuration.py`
- Test: `backend/tests/test_configuration_models.py`

- [ ] **Step 1: Write failing model registration and relationship tests**

Create `backend/tests/test_configuration_models.py`:

```python
from sqlalchemy import inspect, select
from sqlalchemy.orm import Session

from app.db.base import Base
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


def test_configuration_tables_are_registered() -> None:
    table_names = set(Base.metadata.tables)

    assert {
        "home_spaces",
        "residences",
        "location_nodes",
        "family_members",
        "categories",
        "attribute_definitions",
        "attribute_options",
        "item_statuses",
        "dictionary_groups",
        "dictionary_options",
    }.issubset(table_names)


def test_configuration_models_persist_tree_and_fields(db_session: Session) -> None:
    home = HomeSpace(name="我们家", description="家庭物品空间", is_active=True)
    residence = Residence(name="现在住处", home_space=home, description="主住处", is_active=True)
    room = LocationNode(residence=residence, name="客厅", node_type="room", sort_order=10, is_active=True)
    cabinet = LocationNode(
        residence=residence,
        parent=room,
        name="电视柜",
        node_type="cabinet",
        sort_order=20,
        is_active=True,
    )
    member = FamilyMember(home_space=home, name="妈妈", relation="家人", is_active=True)
    category = Category(name="证件", code="documents", sort_order=10, is_active=True)
    field = AttributeDefinition(
        category=category,
        key="expire_date",
        name="有效期",
        field_type="date",
        is_required=False,
        is_filterable=True,
        sort_order=10,
        is_active=True,
    )
    option = AttributeOption(definition=field, label="长期", value="long_term", sort_order=10, is_active=True)
    status = ItemStatus(code="in_stock", name="在库", semantic="in_inventory", sort_order=10, is_system=True, is_active=True)
    group = DictionaryGroup(code="units", name="单位", is_system=True, is_active=True)
    dictionary_option = DictionaryOption(group=group, label="件", value="piece", sort_order=10, is_active=True)
    db_session.add_all([home, member, option, status, dictionary_option])
    db_session.commit()

    saved_residence = db_session.scalar(select(Residence).where(Residence.name == "现在住处"))
    saved_category = db_session.scalar(select(Category).where(Category.code == "documents"))

    assert saved_residence is not None
    assert [node.name for node in saved_residence.location_nodes] == ["客厅", "电视柜"]
    assert cabinet.parent == room
    assert saved_category is not None
    assert saved_category.attribute_definitions[0].options == [option]
```

- [ ] **Step 2: Run model tests and confirm they fail**

Run:

```powershell
Set-Location backend
python -m pytest tests/test_configuration_models.py -v
```

Expected: FAIL because `app.models.configuration` does not exist.

- [ ] **Step 3: Create configuration models**

Create `backend/app/models/configuration.py` with these models and names exactly:

```python
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class HomeSpace(Base):
    __tablename__ = "home_spaces"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(120), unique=True, index=True, nullable=False)
    description: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)

    residences: Mapped[list[Residence]] = relationship(back_populates="home_space", lazy="selectin")
    family_members: Mapped[list[FamilyMember]] = relationship(back_populates="home_space", lazy="selectin")


class Residence(Base):
    __tablename__ = "residences"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    home_space_id: Mapped[int] = mapped_column(ForeignKey("home_spaces.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(120), unique=True, index=True, nullable=False)
    description: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    address: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)

    home_space: Mapped[HomeSpace] = relationship(back_populates="residences", lazy="selectin")
    location_nodes: Mapped[list[LocationNode]] = relationship(back_populates="residence", lazy="selectin")


class LocationNode(Base):
    __tablename__ = "location_nodes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    residence_id: Mapped[int] = mapped_column(ForeignKey("residences.id", ondelete="CASCADE"), nullable=False)
    parent_id: Mapped[int | None] = mapped_column(ForeignKey("location_nodes.id", ondelete="SET NULL"), nullable=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    node_type: Mapped[str] = mapped_column(String(40), default="area", nullable=False)
    icon: Mapped[str] = mapped_column(String(60), default="", nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    note: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    residence: Mapped[Residence] = relationship(back_populates="location_nodes", lazy="selectin")
    parent: Mapped[LocationNode | None] = relationship(remote_side="LocationNode.id", back_populates="children", lazy="selectin")
    children: Mapped[list[LocationNode]] = relationship(back_populates="parent", lazy="selectin")


class FamilyMember(Base):
    __tablename__ = "family_members"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    home_space_id: Mapped[int] = mapped_column(ForeignKey("home_spaces.id", ondelete="CASCADE"), nullable=False)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    name: Mapped[str] = mapped_column(String(120), index=True, nullable=False)
    relation: Mapped[str] = mapped_column(String(80), default="", nullable=False)
    phone: Mapped[str] = mapped_column(String(80), default="", nullable=False)
    note: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    home_space: Mapped[HomeSpace] = relationship(back_populates="family_members", lazy="selectin")


class Category(Base):
    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    parent_id: Mapped[int | None] = mapped_column(ForeignKey("categories.id", ondelete="SET NULL"), nullable=True)
    code: Mapped[str] = mapped_column(String(80), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    icon: Mapped[str] = mapped_column(String(60), default="", nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    parent: Mapped[Category | None] = relationship(remote_side="Category.id", back_populates="children", lazy="selectin")
    children: Mapped[list[Category]] = relationship(back_populates="parent", lazy="selectin")
    attribute_definitions: Mapped[list[AttributeDefinition]] = relationship(back_populates="category", lazy="selectin")


class AttributeDefinition(Base):
    __tablename__ = "attribute_definitions"
    __table_args__ = (UniqueConstraint("category_id", "key", name="uq_attribute_definition_category_key"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    category_id: Mapped[int] = mapped_column(ForeignKey("categories.id", ondelete="CASCADE"), nullable=False)
    key: Mapped[str] = mapped_column(String(80), nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    field_type: Mapped[str] = mapped_column(String(40), nullable=False)
    default_value: Mapped[str] = mapped_column(Text(), default="", nullable=False)
    privacy_level: Mapped[str] = mapped_column(String(40), default="normal", nullable=False)
    is_required: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_filterable: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    category: Mapped[Category] = relationship(back_populates="attribute_definitions", lazy="selectin")
    options: Mapped[list[AttributeOption]] = relationship(back_populates="definition", lazy="selectin")


class AttributeOption(Base):
    __tablename__ = "attribute_options"
    __table_args__ = (UniqueConstraint("definition_id", "value", name="uq_attribute_option_definition_value"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    definition_id: Mapped[int] = mapped_column(ForeignKey("attribute_definitions.id", ondelete="CASCADE"), nullable=False)
    label: Mapped[str] = mapped_column(String(120), nullable=False)
    value: Mapped[str] = mapped_column(String(120), nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    definition: Mapped[AttributeDefinition] = relationship(back_populates="options", lazy="selectin")


class ItemStatus(Base):
    __tablename__ = "item_statuses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    code: Mapped[str] = mapped_column(String(80), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    semantic: Mapped[str] = mapped_column(String(80), nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_system: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class DictionaryGroup(Base):
    __tablename__ = "dictionary_groups"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    code: Mapped[str] = mapped_column(String(80), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    is_system: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    options: Mapped[list[DictionaryOption]] = relationship(back_populates="group", lazy="selectin")


class DictionaryOption(Base):
    __tablename__ = "dictionary_options"
    __table_args__ = (UniqueConstraint("group_id", "value", name="uq_dictionary_option_group_value"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    group_id: Mapped[int] = mapped_column(ForeignKey("dictionary_groups.id", ondelete="CASCADE"), nullable=False)
    label: Mapped[str] = mapped_column(String(120), nullable=False)
    value: Mapped[str] = mapped_column(String(120), nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    group: Mapped[DictionaryGroup] = relationship(back_populates="options", lazy="selectin")
```

- [ ] **Step 4: Export configuration models**

Modify `backend/app/models/__init__.py` to import auth and configuration models:

```python
from app.models.auth import AuthSession, ExternalIdentity, Permission, Role, User
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

__all__ = [
    "AttributeDefinition",
    "AttributeOption",
    "AuthSession",
    "Category",
    "DictionaryGroup",
    "DictionaryOption",
    "ExternalIdentity",
    "FamilyMember",
    "HomeSpace",
    "ItemStatus",
    "LocationNode",
    "Permission",
    "Residence",
    "Role",
    "User",
]
```

- [ ] **Step 5: Create Alembic migration**

Create `backend/alembic/versions/20260619_0002_core_configuration.py` with the same columns, indexes, foreign keys, and unique constraints as the model file. Use `revision = "20260619_0002"` and `down_revision = "20260618_0001"`. The downgrade must drop tables in this order: `dictionary_options`, `dictionary_groups`, `item_statuses`, `attribute_options`, `attribute_definitions`, `categories`, `family_members`, `location_nodes`, `residences`, `home_spaces`.

- [ ] **Step 6: Run model tests**

Run:

```powershell
Set-Location backend
python -m pytest tests/test_configuration_models.py -v
```

Expected: PASS.

- [ ] **Step 7: Run full backend tests**

Run:

```powershell
python -m pytest -v
```

Expected: PASS, with only the existing FastAPI/Starlette TestClient warning acceptable.

- [ ] **Step 8: Commit Task 1**

Run:

```powershell
git add backend
git commit -m "feat: add core configuration models"
```

---

## Task 2: Backend Configuration Schemas And Services

**Files:**
- Create: `backend/app/schemas/configuration.py`
- Create: `backend/app/services/configuration.py`
- Test: `backend/tests/test_configuration_seed.py`

- [ ] **Step 1: Write failing service and seed tests**

Create `backend/tests/test_configuration_seed.py`:

```python
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.configuration import DictionaryGroup, HomeSpace, ItemStatus
from app.services.configuration import ensure_core_configuration_seed


def test_core_configuration_seed_is_idempotent(db_session: Session) -> None:
    first = ensure_core_configuration_seed(db_session)
    second = ensure_core_configuration_seed(db_session)

    home_spaces = db_session.scalars(select(HomeSpace)).all()
    statuses = db_session.scalars(select(ItemStatus)).all()
    groups = db_session.scalars(select(DictionaryGroup)).all()

    assert first.home_space.id == second.home_space.id
    assert [space.name for space in home_spaces] == ["我们家"]
    assert {status.code for status in statuses} == {
        "in_stock",
        "loaned",
        "discarded",
        "given_away",
        "sold",
        "lost",
        "consumed",
    }
    assert {"units", "importance", "storage_conditions"}.issubset({group.code for group in groups})
```

- [ ] **Step 2: Run seed test and confirm it fails**

Run:

```powershell
python -m pytest tests/test_configuration_seed.py -v
```

Expected: FAIL because `app.services.configuration` does not exist.

- [ ] **Step 3: Create configuration schemas**

Create `backend/app/schemas/configuration.py`. Include these schema names exactly:

```python
from pydantic import BaseModel, Field


class HomeSpaceResponse(BaseModel):
    id: int
    name: str
    description: str
    is_active: bool


class HomeSpaceUpdate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    description: str = Field(default="", max_length=255)


class ResidenceCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    description: str = Field(default="", max_length=255)
    address: str = Field(default="", max_length=255)
    sort_order: int = 0


class ResidenceUpdate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    description: str = Field(default="", max_length=255)
    address: str = Field(default="", max_length=255)
    sort_order: int = 0
    is_active: bool = True


class ResidenceResponse(ResidenceUpdate):
    id: int


class LocationNodeCreate(BaseModel):
    residence_id: int
    parent_id: int | None = None
    name: str = Field(min_length=1, max_length=120)
    node_type: str = Field(default="area", max_length=40)
    icon: str = Field(default="", max_length=60)
    sort_order: int = 0
    note: str = Field(default="", max_length=255)


class LocationNodeUpdate(BaseModel):
    parent_id: int | None = None
    name: str = Field(min_length=1, max_length=120)
    node_type: str = Field(default="area", max_length=40)
    icon: str = Field(default="", max_length=60)
    sort_order: int = 0
    note: str = Field(default="", max_length=255)
    is_active: bool = True


class LocationNodeResponse(LocationNodeUpdate):
    id: int
    residence_id: int
    children: list["LocationNodeResponse"] = []


class FamilyMemberCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    relation: str = Field(default="", max_length=80)
    phone: str = Field(default="", max_length=80)
    note: str = Field(default="", max_length=255)


class FamilyMemberUpdate(FamilyMemberCreate):
    is_active: bool = True


class FamilyMemberResponse(FamilyMemberUpdate):
    id: int
    user_id: int | None


class CategoryCreate(BaseModel):
    parent_id: int | None = None
    code: str = Field(min_length=1, max_length=80)
    name: str = Field(min_length=1, max_length=120)
    icon: str = Field(default="", max_length=60)
    sort_order: int = 0


class CategoryUpdate(BaseModel):
    parent_id: int | None = None
    name: str = Field(min_length=1, max_length=120)
    icon: str = Field(default="", max_length=60)
    sort_order: int = 0
    is_active: bool = True


class CategoryResponse(CategoryUpdate):
    id: int
    code: str
    children: list["CategoryResponse"] = []


class AttributeDefinitionCreate(BaseModel):
    category_id: int
    key: str = Field(min_length=1, max_length=80)
    name: str = Field(min_length=1, max_length=120)
    field_type: str = Field(min_length=1, max_length=40)
    default_value: str = ""
    privacy_level: str = "normal"
    is_required: bool = False
    is_filterable: bool = False
    sort_order: int = 0


class AttributeDefinitionUpdate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    field_type: str = Field(min_length=1, max_length=40)
    default_value: str = ""
    privacy_level: str = "normal"
    is_required: bool = False
    is_filterable: bool = False
    sort_order: int = 0
    is_active: bool = True


class AttributeDefinitionResponse(AttributeDefinitionUpdate):
    id: int
    category_id: int
    key: str
    options: list["AttributeOptionResponse"] = []


class AttributeOptionCreate(BaseModel):
    definition_id: int
    label: str = Field(min_length=1, max_length=120)
    value: str = Field(min_length=1, max_length=120)
    sort_order: int = 0


class AttributeOptionUpdate(BaseModel):
    label: str = Field(min_length=1, max_length=120)
    sort_order: int = 0
    is_active: bool = True


class AttributeOptionResponse(AttributeOptionUpdate):
    id: int
    definition_id: int
    value: str


class ItemStatusCreate(BaseModel):
    code: str = Field(min_length=1, max_length=80)
    name: str = Field(min_length=1, max_length=120)
    semantic: str = Field(min_length=1, max_length=80)
    sort_order: int = 0


class ItemStatusUpdate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    semantic: str = Field(min_length=1, max_length=80)
    sort_order: int = 0
    is_active: bool = True


class ItemStatusResponse(ItemStatusUpdate):
    id: int
    code: str
    is_system: bool


class DictionaryGroupCreate(BaseModel):
    code: str = Field(min_length=1, max_length=80)
    name: str = Field(min_length=1, max_length=120)


class DictionaryOptionResponse(BaseModel):
    id: int
    group_id: int
    label: str
    value: str
    sort_order: int
    is_active: bool


class DictionaryGroupResponse(BaseModel):
    id: int
    code: str
    name: str
    is_system: bool
    is_active: bool
    options: list[DictionaryOptionResponse] = []


class DictionaryOptionCreate(BaseModel):
    group_id: int
    label: str = Field(min_length=1, max_length=120)
    value: str = Field(min_length=1, max_length=120)
    sort_order: int = 0


class ConfigBootstrapResponse(BaseModel):
    home_space: HomeSpaceResponse
    residences: list[ResidenceResponse]
    location_tree: list[LocationNodeResponse]
    family_members: list[FamilyMemberResponse]
    categories: list[CategoryResponse]
    item_statuses: list[ItemStatusResponse]
    dictionary_groups: list[DictionaryGroupResponse]
```

- [ ] **Step 4: Create configuration service**

Create `backend/app/services/configuration.py` with:

- `ensure_core_configuration_seed(db: Session) -> CoreConfigurationSeedResult`
- `get_or_create_home_space(db: Session) -> HomeSpace`
- `list_residences(db: Session) -> list[Residence]`
- `build_location_tree(nodes: list[LocationNode]) -> list[LocationNodeResponse]`
- `build_category_tree(categories: list[Category]) -> list[CategoryResponse]`
- `assert_location_parent_valid(db, residence_id, parent_id, current_id=None) -> None`
- `assert_category_parent_valid(db, parent_id, current_id=None) -> None`
- `get_config_bootstrap(db: Session) -> ConfigBootstrapResponse`
- `create_residence(db: Session, payload: ResidenceCreate) -> ResidenceResponse`
- `create_location_node(db: Session, payload: LocationNodeCreate) -> LocationNodeResponse`
- `create_family_member(db: Session, payload: FamilyMemberCreate) -> FamilyMemberResponse`
- `create_category(db: Session, payload: CategoryCreate) -> CategoryResponse`
- `create_attribute_definition(db: Session, payload: AttributeDefinitionCreate) -> AttributeDefinitionResponse`

The implementation must raise `bad_request("位置上级节点不合法")` when a location parent is missing, belongs to another residence, or equals the current node. It must raise `bad_request("分类上级节点不合法")` when a category parent is missing, equals the current node, or would create a cycle.

- [ ] **Step 5: Run seed tests**

Run:

```powershell
python -m pytest tests/test_configuration_seed.py -v
```

Expected: PASS.

- [ ] **Step 6: Commit Task 2**

Run:

```powershell
git add backend
git commit -m "feat: add configuration services"
```

---

## Task 3: Backend Configuration API

**Files:**
- Create: `backend/app/api/routes/configuration.py`
- Modify: `backend/app/api/router.py`
- Modify: `backend/app/services/seed.py`
- Test: `backend/tests/test_configuration_api.py`

- [ ] **Step 1: Write failing API tests**

Create `backend/tests/test_configuration_api.py`:

```python
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.core.security import hash_password
from app.main import app
from app.models.auth import Role, User
from app.services.seed import seed_auth_baseline


@pytest.fixture()
def client(db_session: Session) -> Iterator[TestClient]:
    seed_auth_baseline(db_session, admin_username="admin", admin_password="ChangeMe123!")

    def override_get_db() -> Iterator[Session]:
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()


def login(client: TestClient, username: str = "admin", password: str = "ChangeMe123!") -> dict[str, str]:
    response = client.post("/api/auth/login", json={"username": username, "password": password})
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def test_bootstrap_returns_seeded_core_config(client: TestClient) -> None:
    response = client.get("/api/config/bootstrap", headers=login(client))

    assert response.status_code == 200
    body = response.json()
    assert body["home_space"]["name"] == "我们家"
    assert body["item_statuses"][0]["code"] == "in_stock"
    assert "residences" in body
    assert "categories" in body


def test_admin_creates_residence_location_member_category_and_field(client: TestClient) -> None:
    headers = login(client)

    residence = client.post(
        "/api/config/residences",
        headers=headers,
        json={"name": "现在住处", "description": "主住处", "address": "", "sort_order": 10},
    )
    assert residence.status_code == 201
    residence_id = residence.json()["id"]

    room = client.post(
        "/api/config/location-nodes",
        headers=headers,
        json={"residence_id": residence_id, "name": "客厅", "node_type": "room", "sort_order": 10},
    )
    assert room.status_code == 201

    member = client.post(
        "/api/config/family-members",
        headers=headers,
        json={"name": "妈妈", "relation": "家人", "phone": "", "note": ""},
    )
    assert member.status_code == 201

    category = client.post(
        "/api/config/categories",
        headers=headers,
        json={"code": "documents", "name": "证件", "icon": "document", "sort_order": 10},
    )
    assert category.status_code == 201
    category_id = category.json()["id"]

    field = client.post(
        "/api/config/attribute-definitions",
        headers=headers,
        json={
            "category_id": category_id,
            "key": "expire_date",
            "name": "有效期",
            "field_type": "date",
            "is_filterable": True,
            "sort_order": 10,
        },
    )
    assert field.status_code == 201

    bootstrap = client.get("/api/config/bootstrap", headers=headers).json()
    assert bootstrap["residences"][0]["name"] == "现在住处"
    assert bootstrap["location_tree"][0]["name"] == "客厅"
    assert bootstrap["family_members"][0]["name"] == "妈妈"
    assert bootstrap["categories"][0]["code"] == "documents"


def test_viewer_cannot_create_configuration(client: TestClient, db_session: Session) -> None:
    viewer_role = db_session.query(Role).filter(Role.code == "viewer").one()
    viewer = User(
        username="viewer",
        password_hash=hash_password("Viewer123!"),
        display_name="查看者",
        is_active=True,
    )
    viewer.roles = [viewer_role]
    db_session.add(viewer)
    db_session.commit()

    response = client.post(
        "/api/config/residences",
        headers=login(client, "viewer", "Viewer123!"),
        json={"name": "老家", "description": "", "address": "", "sort_order": 10},
    )

    assert response.status_code == 403
    assert response.json()["message"] == "你没有权限执行此操作"
```

- [ ] **Step 2: Run API tests and confirm they fail**

Run:

```powershell
python -m pytest tests/test_configuration_api.py -v
```

Expected: FAIL because `/api/config/*` routes do not exist.

- [ ] **Step 3: Update seed service**

Modify `backend/app/services/seed.py` so `seed_auth_baseline` calls `ensure_core_configuration_seed(db)` after seeding roles and admin. Keep the returned value as `User` so existing callers do not change.

- [ ] **Step 4: Add configuration routes**

Create `backend/app/api/routes/configuration.py`. Use `APIRouter(prefix="/config", tags=["configuration"])`. Every write endpoint must include `Depends(require_permission("config:manage"))`. Every read endpoint must include `Depends(require_permission("items:view"))`.

Implement these endpoints and delegate all data work to service functions:

```python
@router.get("/bootstrap", response_model=ConfigBootstrapResponse)
def bootstrap(db: Session = Depends(get_db), user: User = Depends(require_permission("items:view"))) -> ConfigBootstrapResponse:
    return get_config_bootstrap(db)

@router.post("/residences", response_model=ResidenceResponse, status_code=status.HTTP_201_CREATED)
def create_residence(payload: ResidenceCreate, db: Session = Depends(get_db), user: User = Depends(require_permission("config:manage"))) -> ResidenceResponse:
    return create_residence_record(db, payload)

@router.post("/location-nodes", response_model=LocationNodeResponse, status_code=status.HTTP_201_CREATED)
def create_location_node(payload: LocationNodeCreate, db: Session = Depends(get_db), user: User = Depends(require_permission("config:manage"))) -> LocationNodeResponse:
    return create_location_node_record(db, payload)

@router.post("/family-members", response_model=FamilyMemberResponse, status_code=status.HTTP_201_CREATED)
def create_family_member(payload: FamilyMemberCreate, db: Session = Depends(get_db), user: User = Depends(require_permission("config:manage"))) -> FamilyMemberResponse:
    return create_family_member_record(db, payload)

@router.post("/categories", response_model=CategoryResponse, status_code=status.HTTP_201_CREATED)
def create_category(payload: CategoryCreate, db: Session = Depends(get_db), user: User = Depends(require_permission("config:manage"))) -> CategoryResponse:
    return create_category_record(db, payload)

@router.post("/attribute-definitions", response_model=AttributeDefinitionResponse, status_code=status.HTTP_201_CREATED)
def create_attribute_definition(payload: AttributeDefinitionCreate, db: Session = Depends(get_db), user: User = Depends(require_permission("config:manage"))) -> AttributeDefinitionResponse:
    return create_attribute_definition_record(db, payload)
```

The route file imports service functions with `_record` suffix to avoid shadowing endpoint function names:

```python
from app.services.configuration import (
    create_attribute_definition as create_attribute_definition_record,
    create_category as create_category_record,
    create_family_member as create_family_member_record,
    create_location_node as create_location_node_record,
    create_residence as create_residence_record,
    get_config_bootstrap,
)
```

Add list endpoints for residences, location tree, family members, categories, item statuses, and dictionaries before committing. Use service helpers for tree building and parent validation; do not duplicate cycle logic in the route functions.

- [ ] **Step 5: Include router**

Modify `backend/app/api/router.py`:

```python
from app.api.routes import auth, configuration, health

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(configuration.router)
```

- [ ] **Step 6: Run API and backend tests**

Run:

```powershell
python -m pytest tests/test_configuration_api.py -v
python -m pytest -v
```

Expected: PASS.

- [ ] **Step 7: Verify migration and seed on a real SQLite file**

Run:

```powershell
python -m alembic upgrade head
python -m app.cli
```

Expected: migration succeeds and seed prints `管理员账号已就绪: admin`.

- [ ] **Step 8: Commit Task 3**

Run:

```powershell
git add backend
git commit -m "feat: add configuration api"
```

---

## Task 4: Frontend Configuration API And Store

**Files:**
- Create: `frontend/src/api/configuration.ts`
- Create: `frontend/src/stores/configuration.ts`

- [ ] **Step 1: Create typed frontend API**

Create `frontend/src/api/configuration.ts` with interfaces matching the backend response names: `HomeSpace`, `Residence`, `LocationNode`, `FamilyMember`, `Category`, `AttributeDefinition`, `ItemStatus`, `DictionaryGroup`, `ConfigBootstrap`.

Implement:

```ts
export async function fetchConfigBootstrapApi(): Promise<ConfigBootstrap>
export async function createResidenceApi(payload: ResidenceCreate): Promise<Residence>
export async function createLocationNodeApi(payload: LocationNodeCreate): Promise<LocationNode>
export async function createFamilyMemberApi(payload: FamilyMemberCreate): Promise<FamilyMember>
export async function createCategoryApi(payload: CategoryCreate): Promise<Category>
export async function createAttributeDefinitionApi(payload: AttributeDefinitionCreate): Promise<AttributeDefinition>
```

Each function must use `apiClient` from `./client` and return `response.data`.

- [ ] **Step 2: Create Pinia store**

Create `frontend/src/stores/configuration.ts`:

```ts
import { defineStore } from 'pinia'

import {
  createAttributeDefinitionApi,
  createCategoryApi,
  createFamilyMemberApi,
  createLocationNodeApi,
  createResidenceApi,
  fetchConfigBootstrapApi,
  type AttributeDefinitionCreate,
  type CategoryCreate,
  type ConfigBootstrap,
  type FamilyMemberCreate,
  type LocationNodeCreate,
  type ResidenceCreate
} from '../api/configuration'

interface ConfigurationState {
  data: ConfigBootstrap | null
  loading: boolean
}

export const useConfigurationStore = defineStore('configuration', {
  state: (): ConfigurationState => ({ data: null, loading: false }),
  actions: {
    async load() {
      this.loading = true
      try {
        this.data = await fetchConfigBootstrapApi()
      } finally {
        this.loading = false
      }
    },
    async createResidence(payload: ResidenceCreate) {
      await createResidenceApi(payload)
      await this.load()
    },
    async createLocationNode(payload: LocationNodeCreate) {
      await createLocationNodeApi(payload)
      await this.load()
    },
    async createFamilyMember(payload: FamilyMemberCreate) {
      await createFamilyMemberApi(payload)
      await this.load()
    },
    async createCategory(payload: CategoryCreate) {
      await createCategoryApi(payload)
      await this.load()
    },
    async createAttributeDefinition(payload: AttributeDefinitionCreate) {
      await createAttributeDefinitionApi(payload)
      await this.load()
    }
  }
})
```

- [ ] **Step 3: Build frontend**

Run:

```powershell
Set-Location frontend
npm run build
```

Expected: PASS.

- [ ] **Step 4: Commit Task 4**

Run:

```powershell
git add frontend
git commit -m "feat: add configuration frontend data layer"
```

---

## Task 5: Frontend Core Configuration Admin Page

**Files:**
- Create: `frontend/src/pages/CoreConfigPage.vue`
- Create: `frontend/src/components/config/ResidenceLocationPanel.vue`
- Create: `frontend/src/components/config/FamilyMemberPanel.vue`
- Create: `frontend/src/components/config/CategoryFieldPanel.vue`
- Create: `frontend/src/components/config/DictionaryPanel.vue`
- Modify: `frontend/src/router/index.ts`
- Modify: `frontend/src/layouts/AppLayout.vue`

- [ ] **Step 1: Replace admin placeholder route**

Modify `frontend/src/router/index.ts` so the admin child route is:

```ts
{
  path: 'admin/config',
  name: 'core-config',
  component: () => import('../pages/CoreConfigPage.vue'),
  meta: { permission: 'config:manage' }
}
```

- [ ] **Step 2: Update navigation**

Modify `frontend/src/layouts/AppLayout.vue` so the 后台管理 menu item uses `index="/admin/config"` and still sits inside `PermissionGate permission="users:manage"` or `PermissionGate permission="config:manage"`. Prefer `config:manage`, because this page manages configuration rather than user accounts.

- [ ] **Step 3: Create config page shell**

Create `frontend/src/pages/CoreConfigPage.vue` as a first-screen admin tool, not a landing page. It should call `configuration.load()` on mount, show the title `核心配置`, and render Element Plus tabs:

- `住宅与位置`
- `家庭成员`
- `分类字段`
- `状态与字典`

Use the four component panels listed above. Do not nest cards inside cards.

- [ ] **Step 4: Create residence/location panel**

Create `ResidenceLocationPanel.vue` with:

- A compact form to add residence name, description, and address.
- A residence list table.
- A location form that selects residence, optional parent, name, and type.
- A tree view of locations grouped by residence.

The panel must call `configuration.createResidence` and `configuration.createLocationNode`, show `ElMessage.success("已保存")`, and show `getChineseErrorMessage(error)` on failure.

- [ ] **Step 5: Create family member panel**

Create `FamilyMemberPanel.vue` with:

- Form fields: name, relation, phone, note.
- A table of existing members.
- Save action through `configuration.createFamilyMember`.

- [ ] **Step 6: Create category and field panel**

Create `CategoryFieldPanel.vue` with:

- Form to create category code, name, icon, optional parent.
- Category tree/table.
- Form to create field for a selected category: key, name, field_type, required, filterable.
- Save action through `configuration.createCategory` and `configuration.createAttributeDefinition`.

The supported field type selector options are exactly: `text`, `long_text`, `number`, `money`, `date`, `datetime`, `single_select`, `multi_select`, `boolean`, `url`, `attachment`, `encrypted_text`, `reminder_date`.

- [ ] **Step 7: Create dictionary panel**

Create `DictionaryPanel.vue` as read-first for Phase 2. It lists seeded item statuses and dictionary groups/options from the bootstrap payload. Do not add status or dictionary edit forms in this phase; those controls can be added in the later management-enhancement phase after inventory uses the dictionaries.

- [ ] **Step 8: Build frontend**

Run:

```powershell
npm run build
```

Expected: PASS.

- [ ] **Step 9: Commit Task 5**

Run:

```powershell
git add frontend
git commit -m "feat: add core configuration admin page"
```

---

## Task 6: Phase 2 Verification

**Files:**
- No source files should change.
- Use temporary verification files under `output/playwright/`.

- [ ] **Step 1: Run backend tests**

Run:

```powershell
Set-Location backend
python -m pytest -v
```

Expected: all backend tests PASS.

- [ ] **Step 2: Run frontend build**

Run:

```powershell
Set-Location frontend
npm run build
```

Expected: build completes without TypeScript or Vite errors.

- [ ] **Step 3: Verify migration and seed**

Run:

```powershell
Set-Location backend
python -m alembic upgrade head
python -m app.cli
```

Expected: schema includes Phase 2 tables and CLI prints `管理员账号已就绪: admin`.

- [ ] **Step 4: Browser smoke flow**

Start backend and frontend locally, then verify in a real browser:

1. Login as `admin / ChangeMe123!`.
2. Open `后台管理`.
3. Confirm `核心配置` page renders.
4. Create residence `现在住处`.
5. Create location node `客厅` under `现在住处`.
6. Create family member `妈妈`.
7. Create category `证件` with code `documents`.
8. Create field `有效期` with key `expire_date` and type `date`.
9. Confirm the created records remain visible after refresh.
10. Confirm logout returns to login.

Capture screenshots:

- `output/playwright/phase-2-core-config.png`
- `output/playwright/phase-2-location-tree.png`

- [ ] **Step 5: Commit verification artifacts only if intentionally kept**

If screenshots are temporary evidence, leave `output/playwright/` untracked and mention paths in the completion report. If screenshots should be kept, commit them separately with:

```powershell
git add output/playwright/phase-2-core-config.png output/playwright/phase-2-location-tree.png
git commit -m "test: capture phase 2 browser smoke"
```

---

## Completion Criteria

Phase 2 is complete when:

- `python -m pytest -v` passes in `backend`.
- `npm run build` passes in `frontend`.
- Alembic upgrades a fresh SQLite database through `20260619_0002`.
- `python -m app.cli` seeds auth and core configuration idempotently.
- Admin can open `后台管理 -> 核心配置`.
- Admin can create a residence, location node, family member, category, and category field.
- Viewer/editor users cannot write configuration without `config:manage`.
- Configuration read responses are reusable by Phase 3 item forms.

## Self-Review Notes

- Covered from the product design: home space, residences, location tree, family members, category tree, custom attribute fields, attribute options, item statuses, dictionaries, RBAC checks, Chinese errors, and browser verification.
- Deferred to Phase 3: item creation, item custom values, images, containers, movement history, quantity history, loan flow, item search, and item detail pages.
- Deferred to Phase 4: operation log UI, reminder center, deeper user/role management screens, and complete admin/editor/viewer acceptance flows.
