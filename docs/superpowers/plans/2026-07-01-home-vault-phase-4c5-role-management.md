# HomeVault Phase 4C-5 Role Management Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add custom role management inside the existing user-management page while keeping permission points system-owned and system roles read-only.

**Architecture:** Extend the existing admin slice instead of adding a separate role subsystem. The backend keeps permission codes seeded and immutable, adds soft activation for roles, exposes create/update APIs for custom roles only, and reuses current user-role assignment and last-admin guards. The frontend keeps `/admin/users` as the single route and turns the page into two Element Plus tabs: personnel management and role management.

**Tech Stack:** FastAPI, SQLAlchemy, Alembic, Pydantic, pytest, Vue 3, Pinia, Vue Router, Element Plus, TypeScript, Vite.

---

## File Structure

Backend:

- Modify `backend/app/models/auth.py`: add `Role.is_active`.
- Create `backend/alembic/versions/20260701_0008_role_is_active.py`: add `roles.is_active`.
- Modify `backend/app/schemas/admin.py`: add role create/update payloads and active state on role responses.
- Modify `backend/app/services/seed.py`: keep system roles active and continue syncing only system role permissions.
- Modify `backend/app/services/admin.py`: add custom role create/update services, role validation, active-role assignment guard, and audit writes.
- Modify `backend/app/api/routes/admin.py`: add `POST /admin/roles` and `PATCH /admin/roles/{role_id}`.
- Create `backend/tests/test_admin_roles.py`: role-management API, validation, assignment, and audit coverage.
- Modify `backend/tests/test_seed.py`: assert seeded system roles are active.

Frontend:

- Modify `frontend/src/api/admin.ts`: add role active field, role create/update payloads, and role API helpers.
- Modify `frontend/src/stores/adminUsers.ts`: add custom-role mutation actions and role refresh behavior.
- Modify `frontend/src/pages/AdminUsersPage.vue`: split into `人员管理` and `角色管理` tabs; add custom role dialog and active-role assignment filtering.
- Modify `frontend/tests/admin-users-contract.ts`: add TypeScript API/store contract coverage for role management.
- Modify `frontend/tests/admin-users-ui-contract.mjs`: add source-level checks for tabs, role management, system read-only behavior, and active-role filtering.

Docs:

- Modify `docs/superpowers/phase-4-closeout.md`: mark Phase 4C-5 custom role management as implemented after code completion.

## Task 1: Backend Role Model And Contracts

**Files:**
- Modify: `backend/app/models/auth.py`
- Create: `backend/alembic/versions/20260701_0008_role_is_active.py`
- Modify: `backend/app/schemas/admin.py`
- Modify: `backend/tests/test_seed.py`
- Create: `backend/tests/test_admin_roles.py`

- [ ] **Step 1: Write failing model/seed tests**

Add to `backend/tests/test_seed.py`:

```python
def test_seeded_system_roles_are_active(db_session: Session) -> None:
    seed_auth_baseline(db_session, admin_username="admin", admin_password="ChangeMe123!")

    roles = db_session.scalars(select(Role)).all()

    assert {role.code for role in roles} == {"admin", "editor", "viewer"}
    assert all(role.is_system for role in roles)
    assert all(role.is_active for role in roles)
```

Create `backend/tests/test_admin_roles.py` with this initial smoke test:

```python
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.main import app
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


def test_roles_response_includes_active_state(client: TestClient) -> None:
    headers = login(client)

    response = client.get("/api/admin/roles", headers=headers)

    assert response.status_code == 200
    assert all("is_active" in role for role in response.json())
    assert {role["code"]: role["is_active"] for role in response.json()} == {
        "admin": True,
        "editor": True,
        "viewer": True,
    }
```

- [ ] **Step 2: Run tests and verify RED**

Run from `backend`:

```powershell
python -m pytest tests/test_seed.py::test_seeded_system_roles_are_active tests/test_admin_roles.py::test_roles_response_includes_active_state -q
```

Expected: FAIL because `Role.is_active` and `AdminRoleResponse.is_active` do not exist.

- [ ] **Step 3: Add `Role.is_active` model field**

Modify `backend/app/models/auth.py` inside `class Role`:

```python
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
```

Place it after `is_system`.

- [ ] **Step 4: Add Alembic migration**

Create `backend/alembic/versions/20260701_0008_role_is_active.py`:

```python
"""add role active flag

Revision ID: 20260701_0008
Revises: 20260628_0007
Create Date: 2026-07-01 00:08:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "20260701_0008"
down_revision = "20260628_0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "roles",
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    op.alter_column("roles", "is_active", server_default=None)


def downgrade() -> None:
    op.drop_column("roles", "is_active")
```

- [ ] **Step 5: Extend role response schema**

Modify `backend/app/schemas/admin.py`:

```python
class AdminRoleResponse(BaseModel):
    id: int
    code: str
    name: str
    description: str
    is_system: bool
    is_active: bool
    permissions: list[AdminPermissionResponse] = Field(default_factory=list)
```

- [ ] **Step 6: Keep seeded roles active**

Modify `backend/app/services/seed.py` in the role loop:

```python
        role.name = name
        role.description = description
        role.is_system = True
        role.is_active = True
        role.permissions = [permissions_by_code[item] for item in ROLE_PERMISSIONS[code]]
```

Keep this synchronization limited to built-in roles from `ROLES`.

- [ ] **Step 7: Run focused tests and verify GREEN**

Run from `backend`:

```powershell
python -m pytest tests/test_seed.py::test_seeded_system_roles_are_active tests/test_admin_roles.py::test_roles_response_includes_active_state -q
```

Expected: 2 passed.

- [ ] **Step 8: Commit Task 1**

```powershell
git add backend/app/models/auth.py backend/alembic/versions/20260701_0008_role_is_active.py backend/app/schemas/admin.py backend/app/services/seed.py backend/tests/test_seed.py backend/tests/test_admin_roles.py
git commit -m "feat: add active state to roles"
```

## Task 2: Backend Custom Role Services And APIs

**Files:**
- Modify: `backend/tests/test_admin_roles.py`
- Modify: `backend/app/schemas/admin.py`
- Modify: `backend/app/services/admin.py`
- Modify: `backend/app/api/routes/admin.py`

- [ ] **Step 1: Add failing API tests for custom roles**

Append to `backend/tests/test_admin_roles.py`:

```python
from sqlalchemy import select

from app.models import AuditLog
from app.models.auth import Role, User


def test_admin_can_create_update_deactivate_and_reactivate_custom_role(
    client: TestClient,
    db_session: Session,
) -> None:
    headers = login(client)

    created = client.post(
        "/api/admin/roles",
        headers=headers,
        json={
            "code": "caretaker",
            "name": "Caretaker",
            "description": "Maintains daily inventory",
            "permission_codes": ["items:view", "items:create"],
            "is_active": True,
        },
    )
    assert created.status_code == 201
    role_id = created.json()["id"]
    assert created.json()["code"] == "caretaker"
    assert created.json()["is_system"] is False
    assert created.json()["is_active"] is True
    assert {permission["code"] for permission in created.json()["permissions"]} == {
        "items:view",
        "items:create",
    }

    updated = client.patch(
        f"/api/admin/roles/{role_id}",
        headers=headers,
        json={
            "name": "Caretaker Plus",
            "description": "Can edit inventory",
            "permission_codes": ["items:view", "items:edit"],
            "is_active": False,
        },
    )
    assert updated.status_code == 200
    assert updated.json()["name"] == "Caretaker Plus"
    assert updated.json()["is_active"] is False
    assert {permission["code"] for permission in updated.json()["permissions"]} == {
        "items:view",
        "items:edit",
    }

    reactivated = client.patch(
        f"/api/admin/roles/{role_id}",
        headers=headers,
        json={
            "name": "Caretaker Plus",
            "description": "Can edit inventory",
            "permission_codes": ["items:view", "items:edit"],
            "is_active": True,
        },
    )
    assert reactivated.status_code == 200
    assert reactivated.json()["is_active"] is True

    saved = db_session.scalar(select(Role).where(Role.code == "caretaker"))
    assert saved is not None
    assert saved.is_system is False
    assert saved.is_active is True
```

- [ ] **Step 2: Add failing validation and audit tests**

Append to `backend/tests/test_admin_roles.py`:

```python
def test_custom_role_management_rejects_system_roles_bad_permissions_and_duplicates(
    client: TestClient,
) -> None:
    headers = login(client)

    duplicate_system = client.post(
        "/api/admin/roles",
        headers=headers,
        json={
            "code": "admin",
            "name": "Admin Copy",
            "description": "",
            "permission_codes": ["items:view"],
            "is_active": True,
        },
    )
    assert duplicate_system.status_code == 400

    blank_code = client.post(
        "/api/admin/roles",
        headers=headers,
        json={
            "code": "   ",
            "name": "Blank",
            "description": "",
            "permission_codes": ["items:view"],
            "is_active": True,
        },
    )
    assert blank_code.status_code == 422

    bad_permission = client.post(
        "/api/admin/roles",
        headers=headers,
        json={
            "code": "badperm",
            "name": "Bad Permission",
            "description": "",
            "permission_codes": ["items:view", "missing:permission"],
            "is_active": True,
        },
    )
    assert bad_permission.status_code == 400
    assert bad_permission.json()["message"] == "权限不存在"

    empty_permissions = client.post(
        "/api/admin/roles",
        headers=headers,
        json={
            "code": "emptyperm",
            "name": "Empty Permission",
            "description": "",
            "permission_codes": [],
            "is_active": True,
        },
    )
    assert empty_permissions.status_code == 400
    assert empty_permissions.json()["message"] == "角色至少需要一个权限"

    system_roles = client.get("/api/admin/roles", headers=headers)
    admin_role_id = next(role["id"] for role in system_roles.json() if role["code"] == "admin")
    update_system = client.patch(
        f"/api/admin/roles/{admin_role_id}",
        headers=headers,
        json={
            "name": "Changed Admin",
            "description": "",
            "permission_codes": ["items:view"],
            "is_active": True,
        },
    )
    assert update_system.status_code == 400
    assert update_system.json()["message"] == "系统角色不能编辑"


def test_custom_role_mutations_write_audit_logs(
    client: TestClient,
    db_session: Session,
) -> None:
    headers = login(client)
    created = client.post(
        "/api/admin/roles",
        headers=headers,
        json={
            "code": "auditor",
            "name": "Auditor",
            "description": "Reads logs",
            "permission_codes": ["logs:view"],
            "is_active": True,
        },
    )
    assert created.status_code == 201
    role_id = created.json()["id"]

    updated = client.patch(
        f"/api/admin/roles/{role_id}",
        headers=headers,
        json={
            "name": "Auditor Disabled",
            "description": "Paused",
            "permission_codes": ["logs:view", "items:view"],
            "is_active": False,
        },
    )
    assert updated.status_code == 200

    logs = db_session.scalars(
        select(AuditLog)
        .where(AuditLog.resource_type == "role", AuditLog.resource_id == str(role_id))
        .order_by(AuditLog.id)
    ).all()

    assert [log.action for log in logs] == [
        "admin.role.create",
        "admin.role.update",
        "admin.role.deactivate",
    ]
    assert logs[0].metadata_json == {
        "permission_codes": ["logs:view"],
        "is_active": True,
    }
    assert logs[1].metadata_json["permission_codes"] == ["items:view", "logs:view"]
    assert "permission_codes" in logs[1].metadata_json["changed_fields"]
    assert logs[2].metadata_json == {"is_active": False}
```

- [ ] **Step 3: Run tests and verify RED**

Run from `backend`:

```powershell
python -m pytest tests/test_admin_roles.py -q
```

Expected: FAIL because role create/update schemas, services, and routes do not exist.

- [ ] **Step 4: Add role request schemas**

Modify `backend/app/schemas/admin.py`:

```python
ROLE_REQUIRED_MESSAGE = "角色至少需要一个权限"


class AdminRoleCreate(RequestModel):
    code: str = Field(min_length=1, max_length=80, pattern=r"^[a-z][a-z0-9:_-]*$")
    name: str = Field(min_length=1, max_length=120)
    description: str = Field(default="", max_length=255)
    permission_codes: list[str] = Field(min_length=1)
    is_active: bool = True

    @field_validator("permission_codes", mode="before")
    @classmethod
    def ensure_permission_codes_present(cls, value: object) -> object:
        if isinstance(value, list) and not value:
            raise bad_request(ROLE_REQUIRED_MESSAGE)
        return value


class AdminRoleUpdate(RequestModel):
    name: str = Field(min_length=1, max_length=120)
    description: str = Field(default="", max_length=255)
    permission_codes: list[str] = Field(min_length=1)
    is_active: bool

    @field_validator("permission_codes", mode="before")
    @classmethod
    def ensure_permission_codes_present(cls, value: object) -> object:
        if isinstance(value, list) and not value:
            raise bad_request(ROLE_REQUIRED_MESSAGE)
        return value
```

- [ ] **Step 5: Add role service helpers**

Modify `backend/app/services/admin.py` imports:

```python
from app.models.auth import AuthSession, Permission, Role, User
from app.schemas.admin import AdminRoleCreate, AdminRoleUpdate
```

Add constants and helpers near `normalize_role_codes`:

```python
ROLE_REQUIRED_MESSAGE = "角色至少需要一个权限"
PERMISSION_NOT_FOUND_MESSAGE = "权限不存在"
SYSTEM_ROLE_READONLY_MESSAGE = "系统角色不能编辑"
INACTIVE_ROLE_ASSIGNMENT_MESSAGE = "角色未启用"


def normalize_permission_codes(permission_codes: list[str]) -> list[str]:
    unique_codes = sorted({code.strip() for code in permission_codes if code.strip()})
    if not unique_codes:
        raise bad_request(ROLE_REQUIRED_MESSAGE)
    return unique_codes


def permission_map_by_code(db: Session, permission_codes: list[str]) -> dict[str, Permission]:
    unique_codes = normalize_permission_codes(permission_codes)
    permissions = db.scalars(select(Permission).where(Permission.code.in_(unique_codes))).all()
    permissions_by_code = {permission.code: permission for permission in permissions}
    if set(permissions_by_code) != set(unique_codes):
        raise bad_request(PERMISSION_NOT_FOUND_MESSAGE)
    return permissions_by_code


def get_role_for_admin(db: Session, role_id: int) -> Role:
    role = db.scalar(
        select(Role)
        .where(Role.id == role_id)
        .options(selectinload(Role.permissions))
    )
    if role is None:
        raise not_found("角色不存在")
    return role
```

- [ ] **Step 6: Reject inactive custom role assignment**

Replace `role_map_by_code` in `backend/app/services/admin.py` with:

```python
def role_map_by_code(db: Session, role_codes: list[str]) -> dict[str, Role]:
    unique_codes = normalize_role_codes(role_codes)

    roles = db.scalars(
        select(Role)
        .where(Role.code.in_(unique_codes))
        .options(selectinload(Role.permissions))
    ).all()
    roles_by_code = {role.code: role for role in roles}
    if set(roles_by_code) != set(unique_codes):
        raise bad_request("角色不存在")
    inactive_custom_roles = [
        role.code
        for role in roles
        if not role.is_system and not role.is_active
    ]
    if inactive_custom_roles:
        raise bad_request(INACTIVE_ROLE_ASSIGNMENT_MESSAGE)
    return roles_by_code
```

- [ ] **Step 7: Add create/update role services**

Add to `backend/app/services/admin.py` after `list_roles`:

```python
def create_role(
    db: Session,
    payload: AdminRoleCreate,
    actor: User | None = None,
) -> AdminRoleResponse:
    permissions_by_code = permission_map_by_code(db, payload.permission_codes)
    existing = db.scalar(select(Role.id).where(Role.code == payload.code))
    if existing is not None:
        raise bad_request("角色编码已存在")

    role = Role(
        code=payload.code,
        name=payload.name,
        description=payload.description,
        is_system=False,
        is_active=payload.is_active,
    )
    role.permissions = [permissions_by_code[code] for code in sorted(permissions_by_code)]
    db.add(role)
    try:
        db.flush()
        record_audit_log(
            db,
            action="admin.role.create",
            resource_type="role",
            actor=actor,
            resource_id=role.id,
            resource_label=role.code,
            metadata={
                "permission_codes": sorted(permissions_by_code),
                "is_active": role.is_active,
            },
        )
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise bad_request("角色编码已存在") from exc
    db.refresh(role)
    return serialize_admin_role(role)


def update_role(
    db: Session,
    role_id: int,
    payload: AdminRoleUpdate,
    actor: User | None = None,
) -> AdminRoleResponse:
    role = get_role_for_admin(db, role_id)
    if role.is_system:
        raise bad_request(SYSTEM_ROLE_READONLY_MESSAGE)

    permissions_by_code = permission_map_by_code(db, payload.permission_codes)
    next_permission_codes = sorted(permissions_by_code)
    current_permission_codes = sorted({permission.code for permission in role.permissions})
    changed_fields: list[str] = []
    if role.name != payload.name:
        changed_fields.append("name")
    if role.description != payload.description:
        changed_fields.append("description")
    if current_permission_codes != next_permission_codes:
        changed_fields.append("permission_codes")
    active_changed = role.is_active != payload.is_active

    role.name = payload.name
    role.description = payload.description
    role.permissions = [permissions_by_code[code] for code in next_permission_codes]
    role.is_active = payload.is_active

    if changed_fields:
        record_audit_log(
            db,
            action="admin.role.update",
            resource_type="role",
            actor=actor,
            resource_id=role.id,
            resource_label=role.code,
            metadata={
                "changed_fields": changed_fields,
                "permission_codes": next_permission_codes,
                "is_active": role.is_active,
            },
        )
    if active_changed:
        record_audit_log(
            db,
            action="admin.role.activate" if role.is_active else "admin.role.deactivate",
            resource_type="role",
            actor=actor,
            resource_id=role.id,
            resource_label=role.code,
            metadata={"is_active": role.is_active},
        )
    db.commit()
    db.refresh(role)
    return serialize_admin_role(role)
```

- [ ] **Step 8: Add role routes**

Modify `backend/app/api/routes/admin.py` schema imports:

```python
    AdminRoleCreate,
    AdminRoleResponse,
    AdminRoleUpdate,
```

Modify service imports:

```python
    create_role as create_role_record,
    update_role as update_role_record,
```

Add routes after `GET /roles`:

```python
@router.post("/roles", response_model=AdminRoleResponse, status_code=status.HTTP_201_CREATED)
def create_role(
    payload: AdminRoleCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("users:manage")),
) -> AdminRoleResponse:
    return create_role_record(db, payload, actor=user)


@router.patch("/roles/{role_id}", response_model=AdminRoleResponse)
def update_role(
    role_id: int,
    payload: AdminRoleUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("users:manage")),
) -> AdminRoleResponse:
    return update_role_record(db, role_id, payload, actor=user)
```

- [ ] **Step 9: Add inactive-role assignment test**

Append to `backend/tests/test_admin_roles.py`:

```python
def test_inactive_custom_role_cannot_be_assigned_to_user(client: TestClient) -> None:
    headers = login(client)
    created_role = client.post(
        "/api/admin/roles",
        headers=headers,
        json={
            "code": "inactivekeeper",
            "name": "Inactive Keeper",
            "description": "",
            "permission_codes": ["items:view"],
            "is_active": False,
        },
    )
    assert created_role.status_code == 201

    created_user = client.post(
        "/api/admin/users",
        headers=headers,
        json={
            "username": "inactiveuser",
            "display_name": "Inactive User",
            "password": "InactiveUser123!",
            "role_codes": ["inactivekeeper"],
        },
    )
    assert created_user.status_code == 400
    assert created_user.json()["message"] == "角色未启用"

    role_id = created_role.json()["id"]
    reactivated_role = client.patch(
        f"/api/admin/roles/{role_id}",
        headers=headers,
        json={
            "name": "Inactive Keeper",
            "description": "",
            "permission_codes": ["items:view"],
            "is_active": True,
        },
    )
    assert reactivated_role.status_code == 200

    created_user = client.post(
        "/api/admin/users",
        headers=headers,
        json={
            "username": "activecustomuser",
            "display_name": "Active Custom User",
            "password": "ActiveCustom123!",
            "role_codes": ["inactivekeeper"],
        },
    )
    assert created_user.status_code == 201
    assert created_user.json()["roles"] == ["inactivekeeper"]
```

- [ ] **Step 10: Run focused backend tests**

Run from `backend`:

```powershell
python -m pytest tests/test_admin_roles.py tests/test_admin_users.py -q
```

Expected: all tests pass.

- [ ] **Step 11: Commit Task 2**

```powershell
git add backend/app/schemas/admin.py backend/app/services/admin.py backend/app/api/routes/admin.py backend/tests/test_admin_roles.py
git commit -m "feat: manage custom roles"
```

## Task 3: Frontend API And Store Contracts

**Files:**
- Modify: `frontend/tests/admin-users-contract.ts`
- Modify: `frontend/src/api/admin.ts`
- Modify: `frontend/src/stores/adminUsers.ts`

- [ ] **Step 1: Extend TypeScript contract test**

Modify `frontend/tests/admin-users-contract.ts` imports from `../src/api/admin` to include:

```ts
  createAdminRoleApi,
  updateAdminRoleApi,
  type AdminRoleCreateRequest,
  type AdminRoleUpdateRequest,
```

Add a contract function:

```ts
async function assertAdminRoleManagementContract() {
  const createPayload: AdminRoleCreateRequest = {
    code: 'caretaker',
    name: 'Caretaker',
    description: '',
    permission_codes: ['items:view'],
    is_active: true
  }
  const updatePayload: AdminRoleUpdateRequest = {
    name: 'Caretaker Plus',
    description: 'Can edit inventory',
    permission_codes: ['items:view', 'items:edit'],
    is_active: false
  }

  expectType<boolean>((await createAdminRoleApi(createPayload)).is_active)
  expectType<boolean>((await updateAdminRoleApi(1, updatePayload)).is_active)

  const store = useAdminUsersStore()
  expectType<AdminRole>(await store.createRole(createPayload))
  expectType<AdminRole>(await store.updateRole(1, updatePayload))
}

void assertAdminRoleManagementContract
```

- [ ] **Step 2: Run contract and verify RED**

Run from `frontend`:

```powershell
.\node_modules\.bin\vue-tsc.cmd --noEmit -p tsconfig.contract.json
```

Expected: FAIL because role create/update types, API helpers, and store actions do not exist.

- [ ] **Step 3: Extend admin API types and helpers**

Modify `frontend/src/api/admin.ts`:

```ts
export interface AdminRole {
  id: number
  code: string
  name: string
  description: string
  is_system: boolean
  is_active: boolean
  permissions: AdminPermission[]
}

export interface AdminRoleCreateRequest {
  code: string
  name: string
  description: string
  permission_codes: string[]
  is_active: boolean
}

export interface AdminRoleUpdateRequest {
  name: string
  description: string
  permission_codes: string[]
  is_active: boolean
}

export async function createAdminRoleApi(payload: AdminRoleCreateRequest): Promise<AdminRole> {
  const response = await apiClient.post<AdminRole>('/admin/roles', payload)
  return response.data
}

export async function updateAdminRoleApi(
  roleId: number,
  payload: AdminRoleUpdateRequest
): Promise<AdminRole> {
  const response = await apiClient.patch<AdminRole>(`/admin/roles/${roleId}`, payload)
  return response.data
}
```

- [ ] **Step 4: Add store actions**

Modify `frontend/src/stores/adminUsers.ts` imports:

```ts
  createAdminRoleApi,
  updateAdminRoleApi,
  type AdminRoleCreateRequest,
  type AdminRoleUpdateRequest,
```

Add actions:

```ts
    async createRole(payload: AdminRoleCreateRequest): Promise<AdminRole> {
      return await this.saveRoleAndRefresh(() => createAdminRoleApi(payload))
    },
    async updateRole(roleId: number, payload: AdminRoleUpdateRequest): Promise<AdminRole> {
      return await this.saveRoleAndRefresh(() => updateAdminRoleApi(roleId, payload))
    },
    async saveRoleAndRefresh(operation: () => Promise<AdminRole>): Promise<AdminRole> {
      this.saving = true
      try {
        const result = await operation()
        try {
          await Promise.all([this.loadRoles(), this.loadUsers()])
        } catch {
          // A successful role mutation should not be reported as failed because follow-up refresh failed.
        }
        return result
      } finally {
        this.saving = false
      }
    },
```

- [ ] **Step 5: Run contract and verify GREEN**

Run from `frontend`:

```powershell
.\node_modules\.bin\vue-tsc.cmd --noEmit -p tsconfig.contract.json
```

Expected: contract type check passes.

- [ ] **Step 6: Commit Task 3**

```powershell
git add frontend/src/api/admin.ts frontend/src/stores/adminUsers.ts frontend/tests/admin-users-contract.ts
git commit -m "feat: add custom role frontend contracts"
```

## Task 4: Frontend Role Management UI

**Files:**
- Modify: `frontend/tests/admin-users-ui-contract.mjs`
- Modify: `frontend/src/pages/AdminUsersPage.vue`

- [ ] **Step 1: Add failing UI source contract**

Append to `frontend/tests/admin-users-ui-contract.mjs`:

```js
assert.match(adminUsersPage, /<el-tabs[\s\S]*v-model="activeAdminTab"/, 'Admin users page should use tabs')
assert.match(adminUsersPage, /name="personnel"/, 'Admin users page should include personnel tab')
assert.match(adminUsersPage, /name="roles"/, 'Admin users page should include roles tab')
assert.match(adminUsersPage, /人员管理/, 'Personnel tab should use Chinese label')
assert.match(adminUsersPage, /角色管理/, 'Role tab should use Chinese label')

assert.match(adminUsersPage, /const\s+assignableRoles\s*=\s*computed/, 'User role assignment should use computed assignable roles')
assert.match(adminUsersPage, /role\.is_system\s*\|\|\s*role\.is_active/, 'Assignable roles should include system roles and active custom roles')
assert.match(adminUsersPage, /v-for="role in assignableRoles"/, 'User role checkboxes should use assignable roles')

assert.match(adminUsersPage, /const\s+systemRoles\s*=\s*computed/, 'Page should keep system roles as a computed group')
assert.match(adminUsersPage, /const\s+customRoles\s*=\s*computed/, 'Page should keep custom roles as a computed group')
assert.match(adminUsersPage, /openCreateRoleDialog/, 'Role tab should expose create role action')
assert.match(adminUsersPage, /openEditRoleDialog/, 'Role tab should expose edit role action')
assert.match(adminUsersPage, /saveRole/, 'Role dialog should save roles through the store')
assert.match(adminUsersPage, /adminUsers\.createRole/, 'Role create should call store createRole')
assert.match(adminUsersPage, /adminUsers\.updateRole/, 'Role update should call store updateRole')
assert.match(adminUsersPage, /roleForm\.permission_codes/, 'Role form should bind selected permission codes')
assert.match(adminUsersPage, /permission\.description/, 'Role management should display permission descriptions')
assert.match(adminUsersPage, /row\.is_system/, 'System roles should be treated as read-only in the UI')
assert.doesNotMatch(adminUsersPage, /deleteRole|removeRole|destroyRole/, 'Role UI should not expose role deletion')
```

- [ ] **Step 2: Run source contract and verify RED**

Run from `frontend`:

```powershell
node .\tests\admin-users-ui-contract.mjs
```

Expected: FAIL because tabs and role-management UI do not exist.

- [ ] **Step 3: Add role UI state**

Modify `frontend/src/pages/AdminUsersPage.vue` script imports:

```ts
import { Check, Edit, Key, Plus, Refresh, Search } from '@element-plus/icons-vue'
import type {
  AdminRole,
  AdminRoleCreateRequest,
  AdminRoleUpdateRequest,
  AdminUser,
  AdminUserCreateRequest,
  AdminUserFilters,
  AdminUserUpdateRequest
} from '../api/admin'
```

Add types and state:

```ts
type AdminTab = 'personnel' | 'roles'
type RoleDialogMode = 'create' | 'edit'

interface RoleFormModel {
  code: string
  name: string
  description: string
  permission_codes: string[]
  is_active: boolean
}

const activeAdminTab = ref<AdminTab>('personnel')
const roleDialogOpen = ref(false)
const roleDialogMode = ref<RoleDialogMode>('create')
const editingRole = ref<AdminRole | null>(null)
const roleFormRef = ref<FormInstance>()

const defaultRoleForm = (): RoleFormModel => ({
  code: '',
  name: '',
  description: '',
  permission_codes: ['items:view'],
  is_active: true
})

const roleForm = reactive<RoleFormModel>(defaultRoleForm())
const isRoleCreateMode = computed(() => roleDialogMode.value === 'create')
const roleDialogTitle = computed(() => (isRoleCreateMode.value ? '新建角色' : '编辑角色'))
const allPermissions = computed(() => {
  const byCode = new Map<string, AdminRole['permissions'][number]>()
  roles.value.forEach((role) => {
    role.permissions.forEach((permission) => byCode.set(permission.code, permission))
  })
  return [...byCode.values()].sort((left, right) => left.code.localeCompare(right.code))
})
const systemRoles = computed(() => roles.value.filter((role) => role.is_system))
const customRoles = computed(() => roles.value.filter((role) => !role.is_system))
const assignableRoles = computed(() => roles.value.filter((role) => role.is_system || role.is_active))
```

- [ ] **Step 4: Add role form rules and helpers**

Add to `frontend/src/pages/AdminUsersPage.vue`:

```ts
const roleRules: FormRules<RoleFormModel> = {
  code: [
    {
      validator: (_rule: unknown, value: string, callback: ValidationCallback) => {
        if (!value.trim()) callback(new Error('请输入角色编码'))
        else if (!/^[a-z][a-z0-9:_-]*$/.test(value.trim())) callback(new Error('角色编码只能使用小写字母、数字、冒号、下划线和短横线'))
        else callback()
      },
      trigger: 'blur'
    }
  ],
  name: [
    {
      validator: (_rule: unknown, value: string, callback: ValidationCallback) => {
        if (!value.trim()) callback(new Error('请输入角色名称'))
        else callback()
      },
      trigger: 'blur'
    }
  ],
  permission_codes: [
    {
      type: 'array',
      required: true,
      min: 1,
      message: '请至少选择一个权限',
      trigger: 'change'
    }
  ]
}

async function clearRoleValidation() {
  await nextTick()
  roleFormRef.value?.clearValidate()
}

function clearRoleDialogState() {
  editingRole.value = null
  Object.assign(roleForm, defaultRoleForm())
}

function permissionCodes(role: AdminRole): string[] {
  return role.permissions.map((permission) => permission.code).sort()
}

function openCreateRoleDialog() {
  roleDialogMode.value = 'create'
  editingRole.value = null
  Object.assign(roleForm, defaultRoleForm())
  roleDialogOpen.value = true
  void clearRoleValidation()
}

function openEditRoleDialog(role: AdminRole) {
  if (role.is_system) return
  roleDialogMode.value = 'edit'
  editingRole.value = role
  Object.assign(roleForm, {
    code: role.code,
    name: role.name,
    description: role.description,
    permission_codes: permissionCodes(role),
    is_active: role.is_active
  })
  roleDialogOpen.value = true
  void clearRoleValidation()
}

async function toggleRoleActive(role: AdminRole) {
  if (role.is_system) return
  try {
    await adminUsers.updateRole(role.id, {
      name: role.name,
      description: role.description,
      permission_codes: permissionCodes(role),
      is_active: !role.is_active
    })
    ElMessage.success(role.is_active ? '角色已停用' : '角色已启用')
  } catch (error) {
    ElMessage.error(getChineseErrorMessage(error))
  }
}

async function saveRole() {
  const valid = await validateForm(roleFormRef.value)
  if (!valid) return

  try {
    if (isRoleCreateMode.value) {
      const payload: AdminRoleCreateRequest = {
        code: roleForm.code.trim(),
        name: roleForm.name.trim(),
        description: roleForm.description.trim(),
        permission_codes: [...roleForm.permission_codes],
        is_active: roleForm.is_active
      }
      await adminUsers.createRole(payload)
      ElMessage.success('角色已创建')
    } else if (editingRole.value) {
      const payload: AdminRoleUpdateRequest = {
        name: roleForm.name.trim(),
        description: roleForm.description.trim(),
        permission_codes: [...roleForm.permission_codes],
        is_active: roleForm.is_active
      }
      await adminUsers.updateRole(editingRole.value.id, payload)
      ElMessage.success('角色已更新')
    }
    roleDialogOpen.value = false
    clearRoleDialogState()
  } catch (error) {
    ElMessage.error(getChineseErrorMessage(error))
  }
}
```

- [ ] **Step 5: Change user role assignment to active roles**

In the user dialog role checkbox group, change:

```vue
v-for="role in roles"
```

to:

```vue
v-for="role in assignableRoles"
```

Keep `roleName(roleCode)` unchanged so inactive roles still display in user tables.

- [ ] **Step 6: Wrap page content in tabs**

In `frontend/src/pages/AdminUsersPage.vue`, wrap the current toolbar/table/pagination/user dialogs in:

```vue
<el-tabs v-model="activeAdminTab" class="admin-tabs">
  <el-tab-pane label="人员管理" name="personnel">
    <div class="tab-panel">
      <!-- existing toolbar, user table, pagination, and user dialogs stay here -->
    </div>
  </el-tab-pane>
  <el-tab-pane label="角色管理" name="roles">
    <div class="tab-panel role-management">
      <!-- role management markup from Step 7 goes here -->
    </div>
  </el-tab-pane>
</el-tabs>
```

Keep the page heading and "新建用户" button. Optionally make the heading button switch by tab:

```vue
<el-button
  v-if="activeAdminTab === 'personnel'"
  type="primary"
  :icon="Plus"
  @click="openCreateDialog"
>
  新建用户
</el-button>
<el-button
  v-else
  type="primary"
  :icon="Plus"
  @click="openCreateRoleDialog"
>
  新建角色
</el-button>
```

- [ ] **Step 7: Add role management markup**

Inside the `roles` tab add:

```vue
<div class="roles-panel">
  <div class="panel-heading">
    <h2>系统角色</h2>
    <p>系统角色只读，用于保留默认权限边界。</p>
  </div>
  <el-table :data="systemRoles" row-key="id" size="small" empty-text="暂无系统角色">
    <el-table-column prop="name" label="名称" min-width="130" />
    <el-table-column prop="code" label="编码" min-width="130" show-overflow-tooltip />
    <el-table-column prop="description" label="说明" min-width="220" show-overflow-tooltip />
    <el-table-column label="权限" min-width="280">
      <template #default="{ row: role }">
        <div class="tag-list">
          <el-tag v-for="permission in role.permissions" :key="permission.code" size="small" effect="plain" type="info">
            {{ permission.code }}
          </el-tag>
        </div>
      </template>
    </el-table-column>
    <el-table-column label="操作" width="100">
      <template #default="{ row }">
        <el-tag v-if="row.is_system" size="small" type="info" effect="plain">只读</el-tag>
      </template>
    </el-table-column>
  </el-table>
</div>

<div class="roles-panel">
  <div class="panel-heading">
    <h2>自定义角色</h2>
    <p>自定义角色可维护名称、说明、权限和启停状态。</p>
  </div>
  <el-table :data="customRoles" row-key="id" size="small" empty-text="暂无自定义角色">
    <el-table-column prop="name" label="名称" min-width="140" />
    <el-table-column prop="code" label="编码" min-width="140" show-overflow-tooltip />
    <el-table-column label="状态" width="100">
      <template #default="{ row }">
        <el-tag :type="row.is_active ? 'success' : 'info'" effect="plain">
          {{ row.is_active ? '启用' : '停用' }}
        </el-tag>
      </template>
    </el-table-column>
    <el-table-column label="权限" min-width="280">
      <template #default="{ row: role }">
        <div class="tag-list">
          <el-tag v-for="permission in role.permissions" :key="permission.code" size="small" effect="plain">
            {{ permission.code }}
          </el-tag>
        </div>
      </template>
    </el-table-column>
    <el-table-column label="操作" width="180" fixed="right">
      <template #default="{ row }">
        <div class="row-actions">
          <el-button link type="primary" :icon="Edit" @click="openEditRoleDialog(row)">编辑</el-button>
          <el-button link type="primary" :icon="Check" @click="toggleRoleActive(row)">
            {{ row.is_active ? '停用' : '启用' }}
          </el-button>
        </div>
      </template>
    </el-table-column>
  </el-table>
</div>
```

- [ ] **Step 8: Add role dialog markup**

Add after the existing user/reset dialogs:

```vue
<el-dialog
  v-model="roleDialogOpen"
  :title="roleDialogTitle"
  width="min(680px, 96vw)"
  destroy-on-close
  @closed="clearRoleDialogState"
>
  <el-form
    ref="roleFormRef"
    :model="roleForm"
    :rules="roleRules"
    label-position="top"
    class="dialog-form"
    @submit.prevent
  >
    <div class="form-grid">
      <el-form-item label="角色编码" prop="code">
        <el-input v-model="roleForm.code" maxlength="80" :disabled="!isRoleCreateMode" autocomplete="off" />
      </el-form-item>
      <el-form-item label="角色名称" prop="name">
        <el-input v-model="roleForm.name" maxlength="120" autocomplete="off" />
      </el-form-item>
      <el-form-item label="说明">
        <el-input v-model="roleForm.description" maxlength="255" />
      </el-form-item>
      <el-form-item label="状态">
        <el-switch v-model="roleForm.is_active" active-text="启用" inactive-text="停用" />
      </el-form-item>
    </div>

    <el-form-item label="权限" prop="permission_codes">
      <el-checkbox-group v-model="roleForm.permission_codes" class="permission-checkboxes">
        <el-checkbox
          v-for="permission in allPermissions"
          :key="permission.code"
          :value="permission.code"
          class="permission-checkbox"
        >
          <span>{{ permission.name }}</span>
          <small>{{ permission.code }}</small>
          <em>{{ permission.description }}</em>
        </el-checkbox>
      </el-checkbox-group>
    </el-form-item>
  </el-form>

  <template #footer>
    <el-button @click="roleDialogOpen = false">取消</el-button>
    <el-button type="primary" :loading="saving" @click="saveRole">保存</el-button>
  </template>
</el-dialog>
```

- [ ] **Step 9: Add styles**

Add to the scoped style:

```css
.admin-tabs,
.tab-panel,
.role-management {
  min-width: 0;
}

.tab-panel,
.role-management {
  display: grid;
  gap: 14px;
}

.permission-checkboxes {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 8px;
  width: 100%;
}

.permission-checkbox {
  align-items: flex-start;
  height: auto;
  min-height: 68px;
  margin-right: 0;
  padding: 8px 10px;
  border: 1px solid #e2e8df;
  border-radius: 8px;
}

.permission-checkbox :deep(.el-checkbox__label) {
  display: grid;
  gap: 3px;
  min-width: 0;
  white-space: normal;
}

.permission-checkbox small,
.permission-checkbox em {
  color: #7b857f;
  font-size: 12px;
  font-style: normal;
}

@media (max-width: 640px) {
  .permission-checkboxes {
    grid-template-columns: 1fr;
  }
}
```

- [ ] **Step 10: Run UI contract and type check**

Run from `frontend`:

```powershell
node .\tests\admin-users-ui-contract.mjs
.\node_modules\.bin\vue-tsc.cmd --noEmit -p tsconfig.contract.json
```

Expected: both pass.

- [ ] **Step 11: Commit Task 4**

```powershell
git add frontend/src/pages/AdminUsersPage.vue frontend/tests/admin-users-ui-contract.mjs
git commit -m "feat: add role management tab"
```

## Task 5: Closeout Update And Full Verification

**Files:**
- Modify: `docs/superpowers/phase-4-closeout.md`

- [ ] **Step 1: Update closeout doc**

Modify `docs/superpowers/phase-4-closeout.md`:

- Move "custom role management" out of "Deliberately Deferred Work".
- Add a Phase 4C-5 bullet under Phase 4C:

```markdown
- 4C-5: custom role management with read-only system permissions, read-only built-in roles, custom role create/edit/activate/deactivate, active-role assignment, and role mutation audit logging.
```

- Keep permission editing itself in deferred work:

```markdown
- Permission-code editing remains deferred. Permission codes are still system-owned and are not administrator-created records.
```

- [ ] **Step 2: Run backend focused tests**

Run from `backend`:

```powershell
python -m pytest tests/test_admin_roles.py tests/test_admin_users.py tests/test_seed.py -q
```

Expected: all pass.

- [ ] **Step 3: Run backend full suite**

Run from `backend`:

```powershell
python -m pytest -q
```

Expected: all pass. Existing TestClient deprecation warning is acceptable.

- [ ] **Step 4: Run frontend contracts and build**

Run from `frontend`:

```powershell
Get-ChildItem -Path .\tests -Filter *.mjs | ForEach-Object { node $_.FullName }
.\node_modules\.bin\vue-tsc.cmd --noEmit -p tsconfig.contract.json
npm.cmd run build
```

Expected: all commands exit 0. Existing Vite/Rollup pure annotation and chunk-size warnings are acceptable.

- [ ] **Step 5: Run repository checks**

Run from repository root:

```powershell
git diff --check
git status --short --branch
```

Expected: no whitespace errors. `git status` shows only intentional closeout doc change before the final commit.

- [ ] **Step 6: Commit closeout update**

```powershell
git add docs/superpowers/phase-4-closeout.md
git commit -m "docs: update phase closeout for role management"
```

- [ ] **Step 7: Final review checkpoint**

Review the final diff and confirm:

- no permission-code mutation UI or API exists;
- system role updates are rejected in backend service tests;
- custom roles are soft-disabled with `is_active`;
- inactive custom roles cannot be assigned;
- user management still preserves last-active-admin guard;
- role events are audited;
- frontend route remains `/admin/users`;
- the page has exactly the two management tabs for this feature.

## Self-Review

Spec coverage:

- Two tabs inside user management: Task 4.
- System permission points read-only: Tasks 2 and 4; no permission mutation endpoints are introduced.
- Built-in roles read-only: Task 2 service tests and Task 4 UI read-only display.
- Custom role create/edit/activate/deactivate: Tasks 2 and 4.
- Active custom roles assignable to users: Tasks 2, 3, and 4.
- Inactive custom roles not newly assignable: Task 2 and Task 4.
- Last-active-admin protection: existing guard stays covered by `test_admin_users.py`; Task 5 reruns it.
- Audit records: Task 2 audit test.

Marker scan:

- No marker words for unfinished content are present.
- Each task lists exact files, commands, and expected outcomes.

Type consistency:

- Backend payload names are `permission_codes` for role mutations and `role_codes` for user mutations.
- Frontend payload names match backend schemas.
- `is_active` is the active flag for both users and roles.
- Role responses contain `permissions`, not `permission_codes`, matching current API response style.
