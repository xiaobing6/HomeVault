# HomeVault Phase 4C-1 Management Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the Phase 4C-1 management foundation: administrator user management, system role visibility, active-only residence-name uniqueness, and residence edit/activation UI.

**Architecture:** Add a focused admin backend slice under `/api/admin` for user and role management, leaving roles system-defined. Keep residence behavior in the existing configuration slice, but change the model, migration, service checks, and UI to support active-only residence-name uniqueness. Add typed frontend API/store modules and dense Element Plus management pages that follow existing route and permission patterns.

**Tech Stack:** FastAPI, SQLAlchemy, Alembic, SQLite, Pydantic, pytest, Vue 3, Pinia, Vue Router, Element Plus, TypeScript, Vite.

---

## File Structure

Backend:

- Create `backend/app/schemas/admin.py`: request/response models for user and role management.
- Create `backend/app/services/admin.py`: user list/create/update/reset-password services and role serialization.
- Create `backend/app/api/routes/admin.py`: `/api/admin/users` and `/api/admin/roles` routes guarded by `users:manage`.
- Modify `backend/app/api/router.py`: include the admin router.
- Modify `backend/app/models/configuration.py`: remove global uniqueness from `Residence.name`.
- Create `backend/alembic/versions/20260627_0006_residence_active_unique.py`: replace global residence-name uniqueness with active-only partial uniqueness.
- Modify `backend/app/services/configuration.py`: active-only residence name checks.
- Modify `docs/superpowers/phase-2-known-limitations.md`: mark the residence limitation as resolved by Phase 4C-1.
- Test `backend/tests/test_admin_users.py`: admin API and service behavior.
- Test `backend/tests/test_configuration_seed.py`: active-only residence service rules.
- Test `backend/tests/test_database_models.py`: migration/index behavior.

Frontend:

- Create `frontend/src/api/admin.ts`: typed admin user/role API helpers.
- Create `frontend/src/stores/adminUsers.ts`: Pinia store for user management filters, loading, roles, users, and mutations.
- Create `frontend/src/pages/AdminUsersPage.vue`: user management workbench.
- Modify `frontend/src/router/index.ts`: add `/admin/users` route guarded by `users:manage`.
- Modify `frontend/src/layouts/AppLayout.vue`: add navigation item guarded by `users:manage`.
- Modify `frontend/src/api/configuration.ts`: add `ResidenceUpdate` and `updateResidenceApi`.
- Modify `frontend/src/stores/configuration.ts`: add `updateResidence`.
- Modify `frontend/src/components/config/ResidenceLocationPanel.vue`: edit residence dialog and active-state display.
- Test `frontend/tests/admin-users-contract.ts`: TypeScript API/store/router/page contract.
- Test `frontend/tests/admin-users-ui-contract.mjs`: source-level UI route/navigation/residence edit contract.

## Task 1: Backend Admin User And Role Management

**Files:**
- Create: `backend/tests/test_admin_users.py`
- Create: `backend/app/schemas/admin.py`
- Create: `backend/app/services/admin.py`
- Create: `backend/app/api/routes/admin.py`
- Modify: `backend/app/api/router.py`

- [ ] **Step 1: Write failing admin user API tests**

Create `backend/tests/test_admin_users.py`:

```python
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.core.security import verify_password
from app.db.base import Base
from app.main import app
from app.models.auth import User
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


def test_admin_can_list_roles_create_update_and_reset_user(
    client: TestClient,
    db_session: Session,
) -> None:
    headers = login(client)

    roles = client.get("/api/admin/roles", headers=headers)
    assert roles.status_code == 200
    assert {role["code"] for role in roles.json()} == {"admin", "editor", "viewer"}

    created = client.post(
        "/api/admin/users",
        headers=headers,
        json={
            "username": "manager",
            "display_name": "Manager",
            "password": "Manager123!",
            "role_codes": ["editor"],
        },
    )
    assert created.status_code == 201
    assert created.json()["username"] == "manager"
    assert created.json()["roles"] == ["editor"]
    assert created.json()["is_active"] is True

    listed = client.get("/api/admin/users", headers=headers, params={"search": "man"})
    assert listed.status_code == 200
    assert listed.json()["total"] == 1
    user_id = listed.json()["items"][0]["id"]

    updated = client.patch(
        f"/api/admin/users/{user_id}",
        headers=headers,
        json={"display_name": "Manager Renamed", "is_active": False, "role_codes": ["viewer"]},
    )
    assert updated.status_code == 200
    assert updated.json()["display_name"] == "Manager Renamed"
    assert updated.json()["is_active"] is False
    assert updated.json()["roles"] == ["viewer"]

    reset = client.post(
        f"/api/admin/users/{user_id}/reset-password",
        headers=headers,
        json={"password": "NewManager123!"},
    )
    assert reset.status_code == 200
    assert reset.json()["id"] == user_id

    saved = db_session.get(User, user_id)
    assert saved is not None
    assert verify_password("NewManager123!", saved.password_hash)


def test_user_management_rejects_viewer_and_editor(client: TestClient) -> None:
    admin_headers = login(client)
    client.post(
        "/api/admin/users",
        headers=admin_headers,
        json={
            "username": "viewer",
            "display_name": "Viewer",
            "password": "Viewer123!",
            "role_codes": ["viewer"],
        },
    )
    viewer_headers = login(client, "viewer", "Viewer123!")

    response = client.get("/api/admin/users", headers=viewer_headers)
    assert response.status_code == 403
    assert response.json()["message"] == "你没有权限执行此操作"


def test_user_management_prevents_last_active_admin_lockout(client: TestClient) -> None:
    headers = login(client)
    users = client.get("/api/admin/users", headers=headers)
    admin_id = users.json()["items"][0]["id"]

    deactivate = client.patch(
        f"/api/admin/users/{admin_id}",
        headers=headers,
        json={"display_name": "Admin", "is_active": False, "role_codes": ["admin"]},
    )
    assert deactivate.status_code == 400
    assert deactivate.json()["message"] == "至少保留一个启用的管理员"

    remove_role = client.patch(
        f"/api/admin/users/{admin_id}",
        headers=headers,
        json={"display_name": "Admin", "is_active": True, "role_codes": ["viewer"]},
    )
    assert remove_role.status_code == 400
    assert remove_role.json()["message"] == "至少保留一个启用的管理员"


def test_user_management_rejects_bad_roles_and_duplicate_username(client: TestClient) -> None:
    headers = login(client)

    empty_roles = client.post(
        "/api/admin/users",
        headers=headers,
        json={
            "username": "emptyroles",
            "display_name": "Empty Roles",
            "password": "Empty123!",
            "role_codes": [],
        },
    )
    assert empty_roles.status_code == 400
    assert empty_roles.json()["message"] == "用户至少需要一个角色"

    bad_role = client.post(
        "/api/admin/users",
        headers=headers,
        json={
            "username": "badrole",
            "display_name": "Bad Role",
            "password": "BadRole123!",
            "role_codes": ["missing"],
        },
    )
    assert bad_role.status_code == 400
    assert bad_role.json()["message"] == "角色不存在"

    duplicate = client.post(
        "/api/admin/users",
        headers=headers,
        json={
            "username": "admin",
            "display_name": "Duplicate",
            "password": "Duplicate123!",
            "role_codes": ["viewer"],
        },
    )
    assert duplicate.status_code == 400
    assert duplicate.json()["message"] == "账号已存在"
```

- [ ] **Step 2: Run tests and confirm they fail**

Run from `backend`:

```powershell
python -m pytest tests/test_admin_users.py -v
```

Expected: FAIL because `/api/admin/users` and `/api/admin/roles` do not exist.

- [ ] **Step 3: Add admin schemas**

Create `backend/app/schemas/admin.py`:

```python
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ResponseModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class RequestModel(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)


class AdminUserListQuery(RequestModel):
    search: str | None = None
    role: str | None = None
    is_active: bool | None = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)


class AdminUserCreate(RequestModel):
    username: str = Field(min_length=1, max_length=80)
    display_name: str = Field(min_length=1, max_length=120)
    password: str = Field(min_length=8, max_length=128)
    role_codes: list[str] = Field(min_length=1)


class AdminUserUpdate(RequestModel):
    display_name: str = Field(min_length=1, max_length=120)
    is_active: bool = True
    role_codes: list[str] = Field(min_length=1)


class AdminPasswordReset(RequestModel):
    password: str = Field(min_length=8, max_length=128)


class AdminPermissionResponse(ResponseModel):
    code: str
    name: str
    description: str


class AdminRoleResponse(ResponseModel):
    id: int
    code: str
    name: str
    description: str
    is_system: bool
    permissions: list[AdminPermissionResponse] = Field(default_factory=list)


class AdminUserResponse(ResponseModel):
    id: int
    username: str
    display_name: str
    is_active: bool
    roles: list[str] = Field(default_factory=list)
    permissions: list[str] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


class AdminUserListResponse(ResponseModel):
    items: list[AdminUserResponse] = Field(default_factory=list)
    total: int
    page: int
    page_size: int
```

- [ ] **Step 4: Add admin services**

Create `backend/app/services/admin.py`:

```python
from __future__ import annotations

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.core.errors import bad_request, not_found
from app.core.security import hash_password
from app.models.auth import Permission, Role, User
from app.schemas.admin import (
    AdminPasswordReset,
    AdminPermissionResponse,
    AdminRoleResponse,
    AdminUserCreate,
    AdminUserListQuery,
    AdminUserListResponse,
    AdminUserResponse,
    AdminUserUpdate,
)


def serialize_admin_user(user: User) -> AdminUserResponse:
    role_codes = sorted({role.code for role in user.roles})
    permission_codes = sorted(
        {
            permission.code
            for role in user.roles
            for permission in role.permissions
        }
    )
    return AdminUserResponse(
        id=user.id,
        username=user.username,
        display_name=user.display_name,
        is_active=user.is_active,
        roles=role_codes,
        permissions=permission_codes,
        created_at=user.created_at,
        updated_at=user.updated_at,
    )


def serialize_admin_role(role: Role) -> AdminRoleResponse:
    permissions = sorted(role.permissions, key=lambda permission: permission.code)
    return AdminRoleResponse(
        id=role.id,
        code=role.code,
        name=role.name,
        description=role.description,
        is_system=role.is_system,
        permissions=[
            AdminPermissionResponse(
                code=permission.code,
                name=permission.name,
                description=permission.description,
            )
            for permission in permissions
        ],
    )


def list_roles(db: Session) -> list[AdminRoleResponse]:
    roles = db.scalars(
        select(Role)
        .options(selectinload(Role.permissions))
        .order_by(Role.code)
    ).all()
    return [serialize_admin_role(role) for role in roles]


def role_map_by_code(db: Session, role_codes: list[str]) -> dict[str, Role]:
    normalized = sorted({code.strip() for code in role_codes if code.strip()})
    if not normalized:
        raise bad_request("用户至少需要一个角色")
    roles = db.scalars(
        select(Role)
        .where(Role.code.in_(normalized))
        .options(selectinload(Role.permissions))
    ).all()
    by_code = {role.code: role for role in roles}
    if set(by_code) != set(normalized):
        raise bad_request("角色不存在")
    return by_code


def active_admin_count(db: Session, excluding_user_id: int | None = None) -> int:
    statement = (
        select(func.count(User.id))
        .join(User.roles)
        .where(User.is_active.is_(True), Role.code == "admin")
    )
    if excluding_user_id is not None:
        statement = statement.where(User.id != excluding_user_id)
    return db.scalar(statement) or 0


def assert_not_last_active_admin(db: Session, user: User, next_active: bool, next_roles: list[Role]) -> None:
    currently_admin = any(role.code == "admin" for role in user.roles)
    next_admin = any(role.code == "admin" for role in next_roles)
    if not currently_admin:
        return
    if next_active and next_admin:
        return
    if active_admin_count(db, excluding_user_id=user.id) == 0:
        raise bad_request("至少保留一个启用的管理员")


def list_users(db: Session, query: AdminUserListQuery) -> AdminUserListResponse:
    statement = select(User).options(selectinload(User.roles).selectinload(Role.permissions))
    count_statement = select(func.count(User.id))

    conditions = []
    if query.search:
        pattern = f"%{query.search}%"
        conditions.append(or_(User.username.ilike(pattern), User.display_name.ilike(pattern)))
    if query.is_active is not None:
        conditions.append(User.is_active.is_(query.is_active))
    if query.role:
        statement = statement.join(User.roles).where(Role.code == query.role)
        count_statement = count_statement.join(User.roles).where(Role.code == query.role)

    for condition in conditions:
        statement = statement.where(condition)
        count_statement = count_statement.where(condition)

    total = db.scalar(count_statement) or 0
    users = db.scalars(
        statement
        .order_by(User.id)
        .offset((query.page - 1) * query.page_size)
        .limit(query.page_size)
    ).unique().all()
    return AdminUserListResponse(
        items=[serialize_admin_user(user) for user in users],
        total=total,
        page=query.page,
        page_size=query.page_size,
    )


def create_user(db: Session, payload: AdminUserCreate) -> AdminUserResponse:
    if db.scalar(select(User).where(User.username == payload.username)) is not None:
        raise bad_request("账号已存在")
    roles = list(role_map_by_code(db, payload.role_codes).values())
    user = User(
        username=payload.username,
        display_name=payload.display_name,
        password_hash=hash_password(payload.password),
        is_active=True,
    )
    user.roles = roles
    db.add(user)
    db.commit()
    db.refresh(user)
    return serialize_admin_user(user)


def get_user_for_admin(db: Session, user_id: int) -> User:
    user = db.scalar(
        select(User)
        .where(User.id == user_id)
        .options(selectinload(User.roles).selectinload(Role.permissions))
    )
    if user is None:
        raise not_found("用户不存在")
    return user


def update_user(db: Session, user_id: int, payload: AdminUserUpdate) -> AdminUserResponse:
    user = get_user_for_admin(db, user_id)
    roles = list(role_map_by_code(db, payload.role_codes).values())
    assert_not_last_active_admin(db, user, payload.is_active, roles)
    user.display_name = payload.display_name
    user.is_active = payload.is_active
    user.roles = roles
    db.commit()
    db.refresh(user)
    return serialize_admin_user(user)


def reset_user_password(db: Session, user_id: int, payload: AdminPasswordReset) -> AdminUserResponse:
    user = get_user_for_admin(db, user_id)
    user.password_hash = hash_password(payload.password)
    db.commit()
    db.refresh(user)
    return serialize_admin_user(user)
```

If `app.core.errors` lacks `not_found`, add it in `backend/app/core/errors.py`:

```python
def not_found(message: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={"message": message})
```

- [ ] **Step 5: Add admin routes and include them**

Create `backend/app/api/routes/admin.py`:

```python
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_permission
from app.models.auth import User
from app.schemas.admin import (
    AdminPasswordReset,
    AdminRoleResponse,
    AdminUserCreate,
    AdminUserListQuery,
    AdminUserListResponse,
    AdminUserResponse,
    AdminUserUpdate,
)
from app.services.admin import (
    create_user,
    list_roles,
    list_users,
    reset_user_password,
    update_user,
)

router = APIRouter(prefix="/admin", tags=["admin"])
MANAGE_USERS_PERMISSION = "users:manage"


@router.get("/users", response_model=AdminUserListResponse)
def admin_users(
    query: AdminUserListQuery = Depends(),
    db: Session = Depends(get_db),
    user: User = Depends(require_permission(MANAGE_USERS_PERMISSION)),
) -> AdminUserListResponse:
    return list_users(db, query)


@router.post("/users", response_model=AdminUserResponse, status_code=status.HTTP_201_CREATED)
def create_admin_user(
    payload: AdminUserCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission(MANAGE_USERS_PERMISSION)),
) -> AdminUserResponse:
    return create_user(db, payload)


@router.patch("/users/{user_id}", response_model=AdminUserResponse)
def update_admin_user(
    user_id: int,
    payload: AdminUserUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission(MANAGE_USERS_PERMISSION)),
) -> AdminUserResponse:
    return update_user(db, user_id, payload)


@router.post("/users/{user_id}/reset-password", response_model=AdminUserResponse)
def reset_admin_user_password(
    user_id: int,
    payload: AdminPasswordReset,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission(MANAGE_USERS_PERMISSION)),
) -> AdminUserResponse:
    return reset_user_password(db, user_id, payload)


@router.get("/roles", response_model=list[AdminRoleResponse])
def admin_roles(
    db: Session = Depends(get_db),
    user: User = Depends(require_permission(MANAGE_USERS_PERMISSION)),
) -> list[AdminRoleResponse]:
    return list_roles(db)
```

Modify `backend/app/api/router.py`:

```python
from fastapi import APIRouter

from app.api.routes import admin, auth, configuration, health, inventory, reminders

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(configuration.router)
api_router.include_router(inventory.router)
api_router.include_router(reminders.router)
api_router.include_router(admin.router)
```

- [ ] **Step 6: Run admin user tests**

Run from `backend`:

```powershell
python -m pytest tests/test_admin_users.py -v
```

Expected: all tests in `test_admin_users.py` pass.

- [ ] **Step 7: Run focused auth/config regression**

Run from `backend`:

```powershell
python -m pytest tests/test_auth_api.py tests/test_seed.py -v
```

Expected: existing auth and seed tests pass.

- [ ] **Step 8: Commit Task 1**

```powershell
git add backend/app/schemas/admin.py backend/app/services/admin.py backend/app/api/routes/admin.py backend/app/api/router.py backend/app/core/errors.py backend/tests/test_admin_users.py
git commit -m "feat: add admin user management api"
```

## Task 2: Active-Only Residence Name Uniqueness

**Files:**
- Modify: `backend/tests/test_configuration_seed.py`
- Modify: `backend/tests/test_database_models.py`
- Modify: `backend/app/models/configuration.py`
- Modify: `backend/app/services/configuration.py`
- Create: `backend/alembic/versions/20260627_0006_residence_active_unique.py`
- Modify: `docs/superpowers/phase-2-known-limitations.md`

- [ ] **Step 1: Add failing configuration service tests**

Append to `backend/tests/test_configuration_seed.py`:

```python
from app.schemas.configuration import ResidenceUpdate
from app.services.configuration import update_residence


def test_inactive_residence_name_can_be_reused(db_session: Session) -> None:
    first = create_residence(db_session, ResidenceCreate(name="海边家"))
    update_residence(
        db_session,
        first.id,
        ResidenceUpdate(name="海边家", description="", address="", sort_order=0, is_active=False),
    )

    second = create_residence(db_session, ResidenceCreate(name="海边家"))

    assert second.id != first.id
    assert second.is_active is True


def test_active_residence_name_conflict_is_rejected_on_create_and_reactivate(db_session: Session) -> None:
    active = create_residence(db_session, ResidenceCreate(name="主住宅"))
    inactive = create_residence(db_session, ResidenceCreate(name="旧名字"))
    update_residence(
        db_session,
        inactive.id,
        ResidenceUpdate(name="旧名字", description="", address="", sort_order=0, is_active=False),
    )

    with pytest.raises(HTTPException) as create_exc:
        create_residence(db_session, ResidenceCreate(name="主住宅"))
    assert_bad_request_message(create_exc, "启用住宅名称已存在")

    with pytest.raises(HTTPException) as reactivate_exc:
        update_residence(
            db_session,
            inactive.id,
            ResidenceUpdate(name="主住宅", description="", address="", sort_order=0, is_active=True),
        )
    assert_bad_request_message(reactivate_exc, "启用住宅名称已存在")
```

Update the existing duplicate-name tests in the same file so they expect `启用住宅名称已存在` instead of the Phase 2 message.

- [ ] **Step 2: Add failing migration index test**

Append to `backend/tests/test_database_models.py`:

```python
def test_residence_active_unique_index_migration_exists_and_upgrades(tmp_path: Path) -> None:
    cfg = alembic_config(str(tmp_path / "residence_active_unique.sqlite3"))

    try:
        script = ScriptDirectory.from_config(cfg)
        revision = script.get_revision("20260627_0006")
        assert revision is not None
        assert revision.down_revision == "20260620_0005"

        command.upgrade(cfg, "head")
        engine = create_engine(f"sqlite:///{tmp_path / 'residence_active_unique.sqlite3'}")
        try:
            indexes = {index["name"]: index for index in inspect(engine).get_indexes("residences")}
        finally:
            engine.dispose()

        assert "ix_residences_name" in indexes
        assert "uq_residences_active_name" in indexes
    finally:
        restore_alembic_database_url(cfg)
```

- [ ] **Step 3: Run focused tests and confirm failure**

Run from `backend`:

```powershell
python -m pytest tests/test_configuration_seed.py::test_inactive_residence_name_can_be_reused tests/test_configuration_seed.py::test_active_residence_name_conflict_is_rejected_on_create_and_reactivate tests/test_database_models.py::test_residence_active_unique_index_migration_exists_and_upgrades -v
```

Expected: FAIL because the service still enforces global uniqueness and migration `20260627_0006` does not exist.

- [ ] **Step 4: Update Residence model**

Modify `backend/app/models/configuration.py`:

```python
class Residence(Base):
    __tablename__ = "residences"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    home_space_id: Mapped[int] = mapped_column(ForeignKey("home_spaces.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(120), index=True, nullable=False)
```

- [ ] **Step 5: Update configuration service checks**

Modify `backend/app/services/configuration.py` near the residence helpers:

```python
def assert_active_residence_name_available(
    db: Session,
    name: str,
    current_id: int | None = None,
) -> None:
    statement = select(Residence).where(
        Residence.name == name,
        Residence.is_active.is_(True),
    )
    if current_id is not None:
        statement = statement.where(Residence.id != current_id)
    if db.scalar(statement) is not None:
        raise bad_request("启用住宅名称已存在")
```

Update `create_residence`:

```python
def create_residence(db: Session, payload: ResidenceCreate) -> ResidenceResponse:
    seed = ensure_core_configuration_seed(db)
    assert_active_residence_name_available(db, payload.name)
    residence = Residence(
        home_space_id=seed.home_space.id,
        name=payload.name,
        description=payload.description,
        address=payload.address,
        sort_order=payload.sort_order,
        is_active=True,
    )
    db.add(residence)
    commit_or_bad_request(db, "启用住宅名称已存在")
    db.refresh(residence)
    return ResidenceResponse.model_validate(residence)
```

Update `update_residence`:

```python
def update_residence(db: Session, residence_id: int, payload: ResidenceUpdate) -> ResidenceResponse:
    residence = db.get(Residence, residence_id)
    if residence is None:
        raise bad_request("Residence not found")
    if payload.is_active:
        assert_active_residence_name_available(db, payload.name, current_id=residence_id)
    residence.name = payload.name
    residence.description = payload.description
    residence.address = payload.address
    residence.sort_order = payload.sort_order
    residence.is_active = payload.is_active
    commit_or_bad_request(db, "启用住宅名称已存在")
    db.refresh(residence)
    return ResidenceResponse.model_validate(residence)
```

- [ ] **Step 6: Add Alembic migration**

Create `backend/alembic/versions/20260627_0006_residence_active_unique.py`:

```python
from alembic import op
import sqlalchemy as sa

revision = "20260627_0006"
down_revision = "20260620_0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_index("ix_residences_name", table_name="residences")
    op.create_index("ix_residences_name", "residences", ["name"], unique=False)
    op.create_index(
        "uq_residences_active_name",
        "residences",
        ["name"],
        unique=True,
        sqlite_where=sa.text("is_active = 1"),
        postgresql_where=sa.text("is_active = true"),
    )


def downgrade() -> None:
    op.drop_index("uq_residences_active_name", table_name="residences")
    op.drop_index("ix_residences_name", table_name="residences")
    op.create_index("ix_residences_name", "residences", ["name"], unique=True)
```

- [ ] **Step 7: Update known limitation doc**

Replace `docs/superpowers/phase-2-known-limitations.md`:

```markdown
# Phase 2 Known Limitations

No active Phase 2 known limitations remain.

- The inactive residence-name reuse limitation was resolved by Phase 4C-1. Active residences now enforce unique names, while inactive residence names may be reused safely.
```

- [ ] **Step 8: Run focused residence tests**

Run from `backend`:

```powershell
python -m pytest tests/test_configuration_seed.py tests/test_database_models.py::test_residence_active_unique_index_migration_exists_and_upgrades -v
```

Expected: all selected tests pass.

- [ ] **Step 9: Run migration round-trip tests**

Run from `backend`:

```powershell
python -m pytest tests/test_database_models.py -v
```

Expected: all database model and migration tests pass.

- [ ] **Step 10: Commit Task 2**

```powershell
git add backend/app/models/configuration.py backend/app/services/configuration.py backend/alembic/versions/20260627_0006_residence_active_unique.py backend/tests/test_configuration_seed.py backend/tests/test_database_models.py docs/superpowers/phase-2-known-limitations.md
git commit -m "fix: allow inactive residence name reuse"
```

## Task 3: Frontend Admin API, Store, And Contracts

**Files:**
- Create: `frontend/src/api/admin.ts`
- Create: `frontend/src/stores/adminUsers.ts`
- Create: `frontend/tests/admin-users-contract.ts`
- Create: `frontend/tests/admin-users-ui-contract.mjs`
- Modify: `frontend/src/router/index.ts`
- Modify: `frontend/src/layouts/AppLayout.vue`

- [ ] **Step 1: Add failing frontend type contract**

Create `frontend/tests/admin-users-contract.ts`:

```ts
import {
  createAdminUserApi,
  fetchAdminRolesApi,
  listAdminUsersApi,
  resetAdminUserPasswordApi,
  updateAdminUserApi,
  type AdminPasswordResetRequest,
  type AdminRole,
  type AdminUser,
  type AdminUserCreateRequest,
  type AdminUserFilters,
  type AdminUserListResponse,
  type AdminUserUpdateRequest
} from '../src/api/admin'
import AdminUsersPage from '../src/pages/AdminUsersPage.vue'
import { router } from '../src/router'
import { useAdminUsersStore } from '../src/stores/adminUsers'

function expectType<T>(_value: T): void {}

async function assertAdminApiContract() {
  const filters: AdminUserFilters = {
    search: 'admin',
    role: 'admin',
    is_active: true,
    page: 1,
    page_size: 20
  }
  const createPayload: AdminUserCreateRequest = {
    username: 'manager',
    display_name: 'Manager',
    password: 'Manager123!',
    role_codes: ['editor']
  }
  const updatePayload: AdminUserUpdateRequest = {
    display_name: 'Manager Renamed',
    is_active: true,
    role_codes: ['viewer']
  }
  const resetPayload: AdminPasswordResetRequest = {
    password: 'NewManager123!'
  }

  expectType<AdminUserListResponse>(await listAdminUsersApi(filters))
  expectType<AdminRole[]>(await fetchAdminRolesApi())
  expectType<AdminUser>(await createAdminUserApi(createPayload))
  expectType<AdminUser>(await updateAdminUserApi(1, updatePayload))
  expectType<AdminUser>(await resetAdminUserPasswordApi(1, resetPayload))
}

async function assertAdminStoreContract() {
  const store = useAdminUsersStore()
  expectType<AdminUser[]>(store.users)
  expectType<AdminRole[]>(store.roles)
  expectType<AdminUserFilters>(store.filters)

  await store.loadUsers({ search: 'admin' })
  await store.loadRoles()
  store.applyFilters({ role: 'viewer' })
  store.setPage(2)
  store.setPageSize(50)
  store.resetFilters()
  expectType<AdminUser>(await store.createUser({ username: 'u', display_name: 'U', password: 'Password123!', role_codes: ['viewer'] }))
  expectType<AdminUser>(await store.updateUser(1, { display_name: 'U2', is_active: true, role_codes: ['editor'] }))
  expectType<AdminUser>(await store.resetPassword(1, { password: 'Password456!' }))
}

void assertAdminApiContract
void assertAdminStoreContract

function assertAdminUiContract() {
  expectType<object>(AdminUsersPage)
  const route = router.resolve('/admin/users')
  expectType<string | symbol | null | undefined>(route.name)
  expectType<unknown>(route.meta.permission)
}

void assertAdminUiContract
```

- [ ] **Step 2: Add failing source contract**

Create `frontend/tests/admin-users-ui-contract.mjs`:

```js
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

const testDir = dirname(fileURLToPath(import.meta.url))
const root = resolve(testDir, '..')

function readSource(relativePath) {
  return readFileSync(resolve(root, relativePath), 'utf8')
}

const routerSource = readSource('src/router/index.ts')
const layoutSource = readSource('src/layouts/AppLayout.vue')
assert.match(routerSource, /path: 'admin\/users'/, 'router should expose /admin/users')
assert.match(routerSource, /name: 'admin-users'/, 'admin users route should have a stable name')
assert.match(routerSource, /permission: 'users:manage'/, 'admin users route should require users:manage')
assert.match(layoutSource, /permission="users:manage"/, 'layout should hide user management nav without users:manage')
assert.match(layoutSource, /index="\/admin\/users"/, 'layout should link to user management')
```

- [ ] **Step 3: Run frontend contracts and confirm failure**

Run from `frontend`:

```powershell
.\node_modules\.bin\vue-tsc.cmd --noEmit -p tsconfig.contract.json
node .\tests\admin-users-ui-contract.mjs
```

Expected: TypeScript contract fails because admin API/store/page do not exist; source contract fails because the user-management route and navigation item are missing.

- [ ] **Step 4: Add admin API**

Create `frontend/src/api/admin.ts`:

```ts
import { apiClient } from './client'

export interface AdminPermission {
  code: string
  name: string
  description: string
}

export interface AdminRole {
  id: number
  code: string
  name: string
  description: string
  is_system: boolean
  permissions: AdminPermission[]
}

export interface AdminUser {
  id: number
  username: string
  display_name: string
  is_active: boolean
  roles: string[]
  permissions: string[]
  created_at: string
  updated_at: string
}

export interface AdminUserListResponse {
  items: AdminUser[]
  total: number
  page: number
  page_size: number
}

export interface AdminUserFilters {
  search?: string | null
  role?: string | null
  is_active?: boolean | null
  page?: number
  page_size?: number
}

export interface AdminUserCreateRequest {
  username: string
  display_name: string
  password: string
  role_codes: string[]
}

export interface AdminUserUpdateRequest {
  display_name: string
  is_active: boolean
  role_codes: string[]
}

export interface AdminPasswordResetRequest {
  password: string
}

export async function listAdminUsersApi(filters: AdminUserFilters = {}): Promise<AdminUserListResponse> {
  const response = await apiClient.get<AdminUserListResponse>('/admin/users', { params: filters })
  return response.data
}

export async function fetchAdminRolesApi(): Promise<AdminRole[]> {
  const response = await apiClient.get<AdminRole[]>('/admin/roles')
  return response.data
}

export async function createAdminUserApi(payload: AdminUserCreateRequest): Promise<AdminUser> {
  const response = await apiClient.post<AdminUser>('/admin/users', payload)
  return response.data
}

export async function updateAdminUserApi(userId: number, payload: AdminUserUpdateRequest): Promise<AdminUser> {
  const response = await apiClient.patch<AdminUser>(`/admin/users/${userId}`, payload)
  return response.data
}

export async function resetAdminUserPasswordApi(
  userId: number,
  payload: AdminPasswordResetRequest
): Promise<AdminUser> {
  const response = await apiClient.post<AdminUser>(`/admin/users/${userId}/reset-password`, payload)
  return response.data
}
```

- [ ] **Step 5: Add admin users store**

Create `frontend/src/stores/adminUsers.ts`:

```ts
import { defineStore } from 'pinia'

import {
  createAdminUserApi,
  fetchAdminRolesApi,
  listAdminUsersApi,
  resetAdminUserPasswordApi,
  updateAdminUserApi,
  type AdminPasswordResetRequest,
  type AdminRole,
  type AdminUser,
  type AdminUserCreateRequest,
  type AdminUserFilters,
  type AdminUserUpdateRequest
} from '../api/admin'

interface AdminUsersState {
  users: AdminUser[]
  roles: AdminRole[]
  filters: AdminUserFilters
  total: number
  page: number
  pageSize: number
  loading: boolean
  saving: boolean
}

const defaultFilters = (): AdminUserFilters => ({
  page: 1,
  page_size: 20
})

const paginationFilterKeys = new Set<keyof AdminUserFilters>(['page', 'page_size'])

function hasNonPaginationFilter(filters: AdminUserFilters): boolean {
  return (Object.keys(filters) as (keyof AdminUserFilters)[]).some((key) => !paginationFilterKeys.has(key))
}

export const useAdminUsersStore = defineStore('adminUsers', {
  state: (): AdminUsersState => ({
    users: [],
    roles: [],
    filters: defaultFilters(),
    total: 0,
    page: 1,
    pageSize: 20,
    loading: false,
    saving: false
  }),
  actions: {
    async loadUsers(filters?: AdminUserFilters) {
      if (filters) {
        this.filters = {
          ...this.filters,
          ...filters,
          page: hasNonPaginationFilter(filters) ? 1 : filters.page ?? this.filters.page
        }
      }
      this.loading = true
      try {
        const response = await listAdminUsersApi(this.filters)
        this.users = response.items
        this.total = response.total
        this.page = response.page
        this.pageSize = response.page_size
      } finally {
        this.loading = false
      }
    },
    async loadRoles() {
      this.roles = await fetchAdminRolesApi()
    },
    applyFilters(filters: AdminUserFilters) {
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
    async createUser(payload: AdminUserCreateRequest): Promise<AdminUser> {
      return await this.saveAndRefresh(() => createAdminUserApi(payload))
    },
    async updateUser(userId: number, payload: AdminUserUpdateRequest): Promise<AdminUser> {
      return await this.saveAndRefresh(() => updateAdminUserApi(userId, payload))
    },
    async resetPassword(userId: number, payload: AdminPasswordResetRequest): Promise<AdminUser> {
      return await this.saveAndRefresh(() => resetAdminUserPasswordApi(userId, payload))
    },
    async saveAndRefresh(operation: () => Promise<AdminUser>): Promise<AdminUser> {
      this.saving = true
      try {
        const result = await operation()
        await this.loadUsers()
        return result
      } finally {
        this.saving = false
      }
    }
  }
})
```

- [ ] **Step 6: Add temporary page and route/nav shell**

Create `frontend/src/pages/AdminUsersPage.vue` with a minimal shell that will be replaced in Task 4:

```vue
<script setup lang="ts">
</script>

<template>
  <section class="admin-users-page">
    <h1 class="page-title">用户管理</h1>
  </section>
</template>
```

Modify `frontend/src/router/index.ts` children:

```ts
{
  path: 'admin/users',
  name: 'admin-users',
  component: () => import('../pages/AdminUsersPage.vue'),
  meta: { permission: 'users:manage' }
}
```

Modify `frontend/src/layouts/AppLayout.vue` imports:

```ts
import { Bell, Box, House, Setting, SwitchButton, UserFilled } from '@element-plus/icons-vue'
```

Add the nav item:

```vue
<PermissionGate permission="users:manage">
  <el-menu-item index="/admin/users">
    <el-icon><UserFilled /></el-icon>
    <span>用户</span>
  </el-menu-item>
</PermissionGate>
```

- [ ] **Step 7: Run frontend contracts**

Run from `frontend`:

```powershell
.\node_modules\.bin\vue-tsc.cmd --noEmit -p tsconfig.contract.json
node .\tests\admin-users-ui-contract.mjs
```

Expected: TypeScript contract and source contract pass.

- [ ] **Step 8: Commit Task 3**

```powershell
git add frontend/src/api/admin.ts frontend/src/stores/adminUsers.ts frontend/src/pages/AdminUsersPage.vue frontend/src/router/index.ts frontend/src/layouts/AppLayout.vue frontend/tests/admin-users-contract.ts frontend/tests/admin-users-ui-contract.mjs
git commit -m "feat: add admin user frontend contracts"
```

## Task 4: Admin Users Page

**Files:**
- Modify: `frontend/src/pages/AdminUsersPage.vue`

- [ ] **Step 1: Replace shell with full user management page**

Replace `frontend/src/pages/AdminUsersPage.vue` with:

```vue
<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { storeToRefs } from 'pinia'
import { ElMessage, type FormInstance } from 'element-plus'
import { Edit, Key, Plus, Refresh, Search } from '@element-plus/icons-vue'

import { getChineseErrorMessage } from '../api/client'
import type { AdminUser } from '../api/admin'
import { useAdminUsersStore } from '../stores/adminUsers'

const adminUsers = useAdminUsersStore()
const { users, roles, filters, loading, saving, total, page, pageSize } = storeToRefs(adminUsers)

const formRef = ref<FormInstance>()
const resetFormRef = ref<FormInstance>()
const userDialogOpen = ref(false)
const resetDialogOpen = ref(false)
const editingUser = ref<AdminUser | null>(null)
const resettingUser = ref<AdminUser | null>(null)

const userForm = reactive({
  username: '',
  display_name: '',
  password: '',
  is_active: true,
  role_codes: [] as string[]
})

const resetForm = reactive({
  password: '',
  confirm_password: ''
})

const searchValue = computed({
  get: () => filters.value.search ?? '',
  set: (value: string) => {
    adminUsers.applyFilters({ search: value.trim() || null })
  }
})

const roleValue = computed({
  get: () => filters.value.role ?? '',
  set: (value: string) => {
    void applyAndLoad({ role: value || null })
  }
})

const activeValue = computed({
  get: () => {
    if (filters.value.is_active === true) return 'active'
    if (filters.value.is_active === false) return 'inactive'
    return ''
  },
  set: (value: string) => {
    void applyAndLoad({ is_active: value === 'active' ? true : value === 'inactive' ? false : null })
  }
})

onMounted(async () => {
  try {
    await Promise.all([adminUsers.loadRoles(), adminUsers.loadUsers()])
  } catch (error) {
    ElMessage.error(getChineseErrorMessage(error))
  }
})

async function validateForm(form?: FormInstance) {
  if (!form) return false
  return form.validate().then(() => true).catch(() => false)
}

async function applyAndLoad(nextFilters: Parameters<typeof adminUsers.applyFilters>[0]) {
  try {
    adminUsers.applyFilters(nextFilters)
    await adminUsers.loadUsers()
  } catch (error) {
    ElMessage.error(getChineseErrorMessage(error))
  }
}

async function refreshSearch() {
  await applyAndLoad({ search: searchValue.value.trim() || null })
}

async function resetFilters() {
  try {
    adminUsers.resetFilters()
    await adminUsers.loadUsers()
  } catch (error) {
    ElMessage.error(getChineseErrorMessage(error))
  }
}

async function changePage(nextPage: number) {
  try {
    adminUsers.setPage(nextPage)
    await adminUsers.loadUsers()
  } catch (error) {
    ElMessage.error(getChineseErrorMessage(error))
  }
}

async function changePageSize(nextSize: number) {
  try {
    adminUsers.setPageSize(nextSize)
    await adminUsers.loadUsers()
  } catch (error) {
    ElMessage.error(getChineseErrorMessage(error))
  }
}

function openCreateDialog() {
  editingUser.value = null
  Object.assign(userForm, {
    username: '',
    display_name: '',
    password: '',
    is_active: true,
    role_codes: ['viewer']
  })
  userDialogOpen.value = true
}

function openEditDialog(user: AdminUser) {
  editingUser.value = user
  Object.assign(userForm, {
    username: user.username,
    display_name: user.display_name,
    password: '',
    is_active: user.is_active,
    role_codes: [...user.roles]
  })
  userDialogOpen.value = true
}

async function saveUser() {
  const valid = await validateForm(formRef.value)
  if (!valid) return
  try {
    if (editingUser.value) {
      await adminUsers.updateUser(editingUser.value.id, {
        display_name: userForm.display_name.trim(),
        is_active: userForm.is_active,
        role_codes: userForm.role_codes
      })
    } else {
      await adminUsers.createUser({
        username: userForm.username.trim(),
        display_name: userForm.display_name.trim(),
        password: userForm.password,
        role_codes: userForm.role_codes
      })
    }
    userDialogOpen.value = false
    ElMessage.success('用户已保存')
  } catch (error) {
    ElMessage.error(getChineseErrorMessage(error))
  }
}

function openResetDialog(user: AdminUser) {
  resettingUser.value = user
  Object.assign(resetForm, { password: '', confirm_password: '' })
  resetDialogOpen.value = true
}

async function resetPassword() {
  const valid = await validateForm(resetFormRef.value)
  if (!valid || !resettingUser.value) return
  try {
    await adminUsers.resetPassword(resettingUser.value.id, { password: resetForm.password })
    resetDialogOpen.value = false
    ElMessage.success('密码已重置')
  } catch (error) {
    ElMessage.error(getChineseErrorMessage(error))
  }
}

function formatDateTime(value: string): string {
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return date.toLocaleString('zh-CN', { hour12: false })
}
</script>

<template>
  <section class="admin-users-page">
    <div class="page-heading">
      <div>
        <h1 class="page-title">用户管理</h1>
        <p>管理本地账号、系统角色和登录权限</p>
      </div>
      <el-button type="primary" :icon="Plus" @click="openCreateDialog">新增用户</el-button>
    </div>

    <div class="toolbar-panel">
      <el-input
        v-model="searchValue"
        class="search-input"
        :prefix-icon="Search"
        placeholder="搜索账号或姓名"
        clearable
        @keyup.enter="refreshSearch"
        @clear="refreshSearch"
      />
      <div class="filter-actions">
        <el-select v-model="roleValue" class="filter-select" placeholder="角色" clearable>
          <el-option v-for="role in roles" :key="role.code" :label="role.name" :value="role.code" />
        </el-select>
        <el-select v-model="activeValue" class="filter-select" placeholder="状态" clearable>
          <el-option label="启用" value="active" />
          <el-option label="停用" value="inactive" />
        </el-select>
        <el-button :icon="Refresh" @click="resetFilters">重置</el-button>
      </div>
    </div>

    <div class="table-panel">
      <el-table v-loading="loading" :data="users" row-key="id" empty-text="暂无用户">
        <el-table-column prop="username" label="账号" min-width="130" />
        <el-table-column prop="display_name" label="姓名" min-width="140" />
        <el-table-column label="角色" min-width="180">
          <template #default="{ row }">
            <el-tag v-for="role in row.roles" :key="role" class="role-tag" effect="plain">{{ role }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="row.is_active ? 'success' : 'info'">{{ row.is_active ? '启用' : '停用' }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="更新时间" width="180">
          <template #default="{ row }">{{ formatDateTime(row.updated_at) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="160" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" :icon="Edit" @click="openEditDialog(row)">编辑</el-button>
            <el-button link type="primary" :icon="Key" @click="openResetDialog(row)">密码</el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <div class="pagination-row">
      <el-pagination
        background
        layout="total, sizes, prev, pager, next"
        :total="total"
        :current-page="page"
        :page-size="pageSize"
        :page-sizes="[20, 40, 80]"
        @current-change="changePage"
        @size-change="changePageSize"
      />
    </div>

    <div class="roles-panel">
      <h2>系统角色</h2>
      <el-table :data="roles" size="small" row-key="code" empty-text="暂无角色">
        <el-table-column prop="name" label="角色" width="120" />
        <el-table-column prop="code" label="编码" width="120" />
        <el-table-column prop="description" label="说明" min-width="180" show-overflow-tooltip />
        <el-table-column label="权限" min-width="260">
          <template #default="{ row }">
            <el-tag v-for="permission in row.permissions" :key="permission.code" class="role-tag" effect="plain">
              {{ permission.code }}
            </el-tag>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <el-dialog v-model="userDialogOpen" :title="editingUser ? '编辑用户' : '新增用户'" width="min(560px, 96vw)">
      <el-form ref="formRef" :model="userForm" label-position="top">
        <el-form-item label="账号" prop="username" :rules="[{ required: true, message: '请输入账号' }]">
          <el-input v-model="userForm.username" :disabled="Boolean(editingUser)" maxlength="80" />
        </el-form-item>
        <el-form-item label="姓名" prop="display_name" :rules="[{ required: true, message: '请输入姓名' }]">
          <el-input v-model="userForm.display_name" maxlength="120" />
        </el-form-item>
        <el-form-item
          v-if="!editingUser"
          label="初始密码"
          prop="password"
          :rules="[{ required: true, min: 8, message: '请输入至少 8 位密码' }]"
        >
          <el-input v-model="userForm.password" type="password" show-password maxlength="128" />
        </el-form-item>
        <el-form-item label="角色" prop="role_codes" :rules="[{ required: true, message: '请选择角色' }]">
          <el-checkbox-group v-model="userForm.role_codes">
            <el-checkbox v-for="role in roles" :key="role.code" :label="role.code">{{ role.name }}</el-checkbox>
          </el-checkbox-group>
        </el-form-item>
        <el-form-item label="状态">
          <el-switch v-model="userForm.is_active" active-text="启用" inactive-text="停用" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="userDialogOpen = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="saveUser">保存</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="resetDialogOpen" title="重置密码" width="min(480px, 96vw)">
      <el-form ref="resetFormRef" :model="resetForm" label-position="top">
        <el-form-item label="新密码" prop="password" :rules="[{ required: true, min: 8, message: '请输入至少 8 位密码' }]">
          <el-input v-model="resetForm.password" type="password" show-password maxlength="128" />
        </el-form-item>
        <el-form-item
          label="确认密码"
          prop="confirm_password"
          :rules="[
            { required: true, message: '请再次输入密码' },
            { validator: (_rule, value, callback) => value === resetForm.password ? callback() : callback(new Error('两次密码不一致')) }
          ]"
        >
          <el-input v-model="resetForm.confirm_password" type="password" show-password maxlength="128" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="resetDialogOpen = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="resetPassword">保存</el-button>
      </template>
    </el-dialog>
  </section>
</template>

<style scoped>
.admin-users-page {
  display: grid;
  gap: 14px;
  min-width: 0;
}

.page-heading {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
}

.page-heading p {
  margin: 4px 0 0;
  color: #69766d;
}

.toolbar-panel,
.table-panel,
.pagination-row,
.roles-panel {
  min-width: 0;
  background: #fff;
  border: 1px solid #e2e8df;
  border-radius: 8px;
}

.toolbar-panel {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 12px;
}

.search-input {
  width: min(360px, 100%);
}

.filter-actions {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 10px;
}

.filter-select {
  width: 132px;
}

.table-panel {
  overflow: hidden;
}

.pagination-row {
  display: flex;
  justify-content: flex-end;
  padding: 12px;
  overflow-x: auto;
}

.roles-panel {
  display: grid;
  gap: 10px;
  padding: 14px;
}

.roles-panel h2 {
  margin: 0;
  color: #26342e;
  font-size: 16px;
}

.role-tag {
  margin: 2px 4px 2px 0;
}

@media (max-width: 820px) {
  .page-heading,
  .toolbar-panel,
  .filter-actions {
    align-items: stretch;
    flex-direction: column;
  }

  .search-input,
  .filter-select {
    width: 100%;
  }
}
</style>
```

- [ ] **Step 2: Run frontend type check**

Run from `frontend`:

```powershell
.\node_modules\.bin\vue-tsc.cmd --noEmit -p tsconfig.contract.json
```

Expected: contract type check passes.

- [ ] **Step 3: Run frontend build**

Run from `frontend`:

```powershell
npm.cmd run build
```

Expected: build passes. Existing Rollup chunk-size warnings may remain.

- [ ] **Step 4: Commit Task 4**

```powershell
git add frontend/src/pages/AdminUsersPage.vue
git commit -m "feat: add admin users page"
```

## Task 5: Residence Edit UI And Configuration Frontend API

**Files:**
- Modify: `frontend/src/api/configuration.ts`
- Modify: `frontend/src/stores/configuration.ts`
- Modify: `frontend/src/components/config/ResidenceLocationPanel.vue`
- Test: `frontend/tests/admin-users-ui-contract.mjs`

- [ ] **Step 1: Extend TypeScript contract for residence update**

Modify `frontend/tests/admin-users-contract.ts` imports:

```ts
import {
  updateResidenceApi,
  type Residence,
  type ResidenceUpdate
} from '../src/api/configuration'
import { useConfigurationStore } from '../src/stores/configuration'
```

Add before `void assertAdminUiContract`:

```ts
async function assertResidenceManagementContract() {
  const payload: ResidenceUpdate = {
    name: 'Main Home',
    description: '',
    address: '',
    sort_order: 0,
    is_active: true
  }
  expectType<Residence>(await updateResidenceApi(1, payload))

  const configuration = useConfigurationStore()
  await configuration.updateResidence(1, payload)
}

void assertResidenceManagementContract
```

- [ ] **Step 2: Run type contract and confirm failure**

Run from `frontend`:

```powershell
.\node_modules\.bin\vue-tsc.cmd --noEmit -p tsconfig.contract.json
```

Expected: FAIL because `ResidenceUpdate`, `updateResidenceApi`, and `configuration.updateResidence` do not exist.

- [ ] **Step 3: Add configuration API support**

Modify `frontend/src/api/configuration.ts`:

```ts
export interface ResidenceUpdate {
  name: string
  description: string
  address: string
  sort_order: number
  is_active: boolean
}

export async function updateResidenceApi(residenceId: number, payload: ResidenceUpdate): Promise<Residence> {
  const response = await apiClient.patch<Residence>(`/config/residences/${residenceId}`, payload)
  return response.data
}
```

- [ ] **Step 4: Extend source contract for residence editing**

Modify `frontend/tests/admin-users-ui-contract.mjs`:

```js
const residencePanelSource = readSource('src/components/config/ResidenceLocationPanel.vue')

assert.match(residencePanelSource, /updateResidence/, 'residence panel should call updateResidence for edits')
assert.match(residencePanelSource, /openResidenceEdit/, 'residence panel should expose an edit action')
```

- [ ] **Step 5: Run source contract and confirm failure**

Run from `frontend`:

```powershell
node .\tests\admin-users-ui-contract.mjs
```

Expected: FAIL because `ResidenceLocationPanel.vue` does not yet call `updateResidence` or expose `openResidenceEdit`.

- [ ] **Step 6: Add configuration store action**

Modify `frontend/src/stores/configuration.ts` imports:

```ts
import {
  createAttributeDefinitionApi,
  createCategoryApi,
  createFamilyMemberApi,
  createLocationNodeApi,
  createResidenceApi,
  fetchConfigBootstrapApi,
  updateResidenceApi,
  type AttributeDefinitionCreate,
  type CategoryCreate,
  type ConfigBootstrap,
  type FamilyMemberCreate,
  type LocationNodeCreate,
  type ResidenceCreate,
  type ResidenceUpdate
} from '../api/configuration'
```

Add action:

```ts
async updateResidence(residenceId: number, payload: ResidenceUpdate) {
  await updateResidenceApi(residenceId, payload)
  await this.load()
}
```

- [ ] **Step 7: Add residence edit support**

Modify `frontend/src/components/config/ResidenceLocationPanel.vue` script imports:

```ts
import { CirclePlus, Edit, Plus } from '@element-plus/icons-vue'
import type { LocationNode, Residence } from '../../api/configuration'
```

Add state:

```ts
const residenceEditOpen = ref(false)
const editingResidence = ref<Residence | null>(null)

const residenceEditForm = reactive({
  name: '',
  description: '',
  address: '',
  sort_order: 0,
  is_active: true
})
```

Add functions:

```ts
function openResidenceEdit(residence: Residence) {
  editingResidence.value = residence
  Object.assign(residenceEditForm, {
    name: residence.name,
    description: residence.description,
    address: residence.address,
    sort_order: residence.sort_order,
    is_active: residence.is_active
  })
  residenceEditOpen.value = true
}

function trimResidenceEditForm() {
  residenceEditForm.name = residenceEditForm.name.trim()
  residenceEditForm.description = residenceEditForm.description.trim()
  residenceEditForm.address = residenceEditForm.address.trim()
}

async function updateResidence() {
  if (!editingResidence.value) return
  trimResidenceEditForm()
  residenceSaving.value = true
  try {
    await configuration.updateResidence(editingResidence.value.id, {
      name: residenceEditForm.name,
      description: residenceEditForm.description,
      address: residenceEditForm.address,
      sort_order: residenceEditForm.sort_order,
      is_active: residenceEditForm.is_active
    })
    residenceEditOpen.value = false
    ElMessage.success('住宅已更新')
  } catch (error) {
    ElMessage.error(getChineseErrorMessage(error))
  } finally {
    residenceSaving.value = false
  }
}
```

Update the residence table:

```vue
<el-table :data="residences" size="small" class="data-table">
  <el-table-column prop="name" label="名称" min-width="120" />
  <el-table-column prop="address" label="地址" min-width="180" show-overflow-tooltip />
  <el-table-column prop="description" label="描述" min-width="160" show-overflow-tooltip />
  <el-table-column label="状态" width="90">
    <template #default="{ row }">
      <el-tag size="small" :type="row.is_active ? 'success' : 'info'">
        {{ row.is_active ? '启用' : '停用' }}
      </el-tag>
    </template>
  </el-table-column>
  <el-table-column label="操作" width="90">
    <template #default="{ row }">
      <el-button link type="primary" :icon="Edit" @click="openResidenceEdit(row)">编辑</el-button>
    </template>
  </el-table-column>
</el-table>
```

Add the edit dialog:

```vue
<el-dialog v-model="residenceEditOpen" title="编辑住宅" width="min(520px, 96vw)">
  <el-form :model="residenceEditForm" label-position="top">
    <el-form-item label="住宅名称" prop="name" :rules="[{ required: true, message: '请输入住宅名称' }]">
      <el-input v-model="residenceEditForm.name" maxlength="40" />
    </el-form-item>
    <el-form-item label="描述">
      <el-input v-model="residenceEditForm.description" maxlength="120" />
    </el-form-item>
    <el-form-item label="地址">
      <el-input v-model="residenceEditForm.address" maxlength="160" />
    </el-form-item>
    <el-form-item label="排序">
      <el-input-number v-model="residenceEditForm.sort_order" :min="0" :max="9999" />
    </el-form-item>
    <el-form-item label="状态">
      <el-switch v-model="residenceEditForm.is_active" active-text="启用" inactive-text="停用" />
    </el-form-item>
  </el-form>
  <template #footer>
    <el-button @click="residenceEditOpen = false">取消</el-button>
    <el-button type="primary" :loading="residenceSaving" @click="updateResidence">保存</el-button>
  </template>
</el-dialog>
```

- [ ] **Step 8: Run source contract**

Run from `frontend`:

```powershell
node .\tests\admin-users-ui-contract.mjs
```

Expected: source contract passes.

- [ ] **Step 9: Run frontend build**

Run from `frontend`:

```powershell
npm.cmd run build
```

Expected: build passes.

- [ ] **Step 10: Commit Task 5**

```powershell
git add frontend/src/api/configuration.ts frontend/src/stores/configuration.ts frontend/src/components/config/ResidenceLocationPanel.vue frontend/tests/admin-users-ui-contract.mjs
git commit -m "feat: edit residences from configuration"
```

## Task 6: Full Verification And Finish

**Files:**
- Existing files changed by Tasks 1-5.

- [ ] **Step 1: Run frontend contracts**

Run from `frontend`:

```powershell
node .\tests\admin-users-ui-contract.mjs
node .\tests\reminder-ui-contract.mjs
node .\tests\phase-copy-contract.mjs
node .\tests\reminder-date-contract.mjs
node .\tests\reminders-store-runtime.mjs
.\node_modules\.bin\vue-tsc.cmd --noEmit -p tsconfig.contract.json
```

Expected: all commands exit 0. The Vite WebSocket port warning from `reminders-store-runtime.mjs` may appear if another local server is using the HMR port; it is acceptable only when the command exit code is 0.

- [ ] **Step 2: Run frontend production build**

Run from `frontend`:

```powershell
npm.cmd run build
```

Expected: build exits 0. Existing Rollup `#__PURE__` and chunk-size warnings may remain.

- [ ] **Step 3: Run backend full test suite**

Run from `backend`:

```powershell
python -m pytest -v
```

Expected: all backend tests pass.

- [ ] **Step 4: Run diff check**

Run from repository root:

```powershell
git diff --check
```

Expected: no whitespace errors. CRLF warnings are acceptable on Windows if exit code is 0.

- [ ] **Step 5: Review git status and recent commits**

Run from repository root:

```powershell
git status --short --branch
git log --oneline -6
```

Expected: branch is ahead only by the intentional Phase 4C-1 commits, with no unstaged work.

- [ ] **Step 6: Request code review**

Use `superpowers:requesting-code-review` with the base SHA before Task 1 and current HEAD. Review focus:

- User-management permission boundaries.
- Last-active-admin guard.
- Active-only residence-name uniqueness migration.
- Frontend route/nav guards and management UI behavior.

Fix any Critical or Important findings before proceeding.

- [ ] **Step 7: Handle review fixes if needed**

If review finds Critical or Important issues, write the smallest failing test for the issue, implement the fix, rerun the focused test, rerun the full verification commands from Steps 1-4, then commit with message `fix: address phase 4c management review`. If review finds no required fixes, do not create an empty commit.

- [ ] **Step 8: Push branch when user asks**

When the user asks to push:

```powershell
git push
```

Expected: current branch pushes to its upstream.

## Self-Review

Spec coverage:

- User management APIs and UI: Tasks 1, 3, and 4.
- System role visibility and role assignment: Tasks 1 and 4.
- User creation, profile update, activation/deactivation, and password reset: Tasks 1 and 4.
- Last active admin guard: Task 1.
- Residence active-only uniqueness migration: Task 2.
- Residence edit and activation UI: Task 5.
- Exclusions from 4B and 4C-2: no audit log, import/export, bulk operations, or custom role mutation tasks are included.

Placeholder scan:

- No vague file paths or unspecified commands remain.
- Test commands and expected outcomes are explicit.

Type consistency:

- Backend role field is consistently `role_codes` in create/update requests and `roles` in responses.
- Frontend filters use `search`, `role`, `is_active`, `page`, and `page_size`, matching backend query fields.
- Residence update uses `ResidenceUpdate` on both backend and frontend.
