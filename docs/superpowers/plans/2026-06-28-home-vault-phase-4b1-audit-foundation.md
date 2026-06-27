# HomeVault Phase 4B-1 Audit Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the Phase 4B-1 backend-first audit foundation with persisted audit logs, read APIs, key operation logging, and frontend typed API contracts.

**Architecture:** Add a focused audit slice (`models/audit.py`, `schemas/audit.py`, `services/audit.py`, `api/routes/audit.py`) instead of scattering query logic across business domains. Business services record audit entries inside their existing transactions, while read APIs are guarded by the existing `logs:view` permission. The frontend only receives typed API helpers in this slice; the visible audit workbench stays out of 4B-1.

**Tech Stack:** FastAPI, SQLAlchemy 2.x ORM, Alembic, Pydantic v2, SQLite, pytest, Vue 3 TypeScript API helpers, existing Vite/vue-tsc contract checks.

---

## Spec

Implement from:

- `docs/superpowers/specs/2026-06-27-home-vault-phase-4b1-audit-foundation-design.md`

Important implementation note:

- SQLAlchemy declarative reserves the name `metadata`, so the ORM attribute must be `metadata_json = mapped_column("metadata", JSON, ...)`.
- API and schemas should still expose the field as `metadata`.
- Audit writes must not store passwords, tokens, password hashes, or full request bodies.

## File Structure

Create:

- `backend/app/models/audit.py`: SQLAlchemy `AuditLog` model.
- `backend/alembic/versions/20260628_0007_audit_logs.py`: migration for `audit_logs`.
- `backend/app/schemas/audit.py`: query, response, and list schemas.
- `backend/app/services/audit.py`: record/list/detail audit service functions.
- `backend/app/api/routes/audit.py`: `/api/audit/logs` read routes.
- `backend/tests/test_audit_service.py`: service-level tests.
- `backend/tests/test_audit_api.py`: API permission and query tests.
- `frontend/src/api/audit.ts`: typed audit API helpers.
- `frontend/tests/audit-contract.ts`: TypeScript API contract.
- `frontend/tests/audit-contract.mjs`: source-level contract.

Modify:

- `backend/app/models/__init__.py`: export `AuditLog`.
- `backend/app/api/router.py`: include audit router.
- `backend/app/api/routes/auth.py`: record login/logout audit events.
- `backend/app/services/auth.py`: make login/logout session helpers transaction-friendly.
- `backend/app/api/routes/admin.py`: pass actor into admin service mutations.
- `backend/app/services/admin.py`: record admin user mutation audit entries.
- `backend/app/api/routes/configuration.py`: pass actor into audited config service mutations.
- `backend/app/services/configuration.py`: record core configuration mutation audit entries.
- `backend/tests/test_database_models.py`: model and migration assertions.
- `backend/tests/test_auth_api.py`: auth audit assertions.
- `backend/tests/test_admin_users.py`: admin mutation audit assertions.
- `backend/tests/test_configuration_api.py`: configuration mutation audit assertions.

---

## Task 1: Audit Model And Migration

**Files:**
- Create: `backend/app/models/audit.py`
- Create: `backend/alembic/versions/20260628_0007_audit_logs.py`
- Modify: `backend/app/models/__init__.py`
- Modify: `backend/tests/test_database_models.py`

- [ ] **Step 1: Write failing model and migration tests**

Add `AuditLog` to the model imports and expected table checks in `backend/tests/test_database_models.py`.

```python
from app.models import AuditLog, AuthSession, ExternalIdentity, Permission, Role, User

EXPECTED_AUDIT_TABLES = {
    "audit_logs",
}
```

Add these tests near the other model/migration tests:

```python
def test_audit_log_table_is_registered() -> None:
    assert EXPECTED_AUDIT_TABLES.issubset(set(Base.metadata.tables))


def test_audit_log_model_persists_actor_resource_and_metadata(db_session) -> None:
    user = User(
        username="audit-admin",
        password_hash="hashed-password",
        display_name="Audit Admin",
    )
    db_session.add(user)
    db_session.flush()

    log = AuditLog(
        actor_user_id=user.id,
        actor_username=user.username,
        action="admin.user.create",
        resource_type="user",
        resource_id="42",
        resource_label="manager",
        result="success",
        metadata_json={"changed_fields": ["display_name"], "role_codes": ["viewer"]},
    )
    db_session.add(log)
    db_session.commit()
    db_session.refresh(log)

    assert log.id is not None
    assert log.occurred_at is not None
    assert log.actor is user
    assert log.metadata_json == {"changed_fields": ["display_name"], "role_codes": ["viewer"]}


def test_audit_log_migration_exists_and_round_trips(tmp_path: Path) -> None:
    db_path = tmp_path / "audit_logs.sqlite3"
    cfg = alembic_config(str(db_path))

    try:
        script = ScriptDirectory.from_config(cfg)
        revision = script.get_revision("20260628_0007")

        assert revision is not None
        assert revision.down_revision == "20260627_0006"

        command.upgrade(cfg, "head")

        engine = create_engine(f"sqlite:///{db_path}")
        try:
            inspector = inspect(engine)
            audit_columns = {column["name"] for column in inspector.get_columns("audit_logs")}
            audit_indexes = {index["name"] for index in inspector.get_indexes("audit_logs")}
        finally:
            engine.dispose()

        assert {
            "id",
            "occurred_at",
            "actor_user_id",
            "actor_username",
            "action",
            "resource_type",
            "resource_id",
            "resource_label",
            "result",
            "metadata",
        }.issubset(audit_columns)
        assert {
            "ix_audit_logs_occurred_at",
            "ix_audit_logs_action",
            "ix_audit_logs_resource_type",
            "ix_audit_logs_actor_user_id",
            "ix_audit_logs_result",
        }.issubset(audit_indexes)

        command.downgrade(cfg, "20260627_0006")
        engine = create_engine(f"sqlite:///{db_path}")
        try:
            assert "audit_logs" not in inspect(engine).get_table_names()
        finally:
            engine.dispose()
    finally:
        restore_alembic_database_url(cfg)
```

- [ ] **Step 2: Run tests to verify RED**

Run from `backend`:

```powershell
python -m pytest tests/test_database_models.py::test_audit_log_table_is_registered tests/test_database_models.py::test_audit_log_model_persists_actor_resource_and_metadata tests/test_database_models.py::test_audit_log_migration_exists_and_round_trips -v
```

Expected: FAIL because `AuditLog` and revision `20260628_0007` do not exist.

- [ ] **Step 3: Add the AuditLog model**

Create `backend/app/models/audit.py`:

```python
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Index, Integer, JSON, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.auth import User


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class AuditLog(Base):
    __tablename__ = "audit_logs"
    __table_args__ = (
        Index("ix_audit_logs_occurred_at", "occurred_at"),
        Index("ix_audit_logs_action", "action"),
        Index("ix_audit_logs_resource_type", "resource_type"),
        Index("ix_audit_logs_actor_user_id", "actor_user_id"),
        Index("ix_audit_logs_result", "result"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    actor_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    actor_username: Mapped[str | None] = mapped_column(String(80), nullable=True)
    action: Mapped[str] = mapped_column(String(120), nullable=False)
    resource_type: Mapped[str] = mapped_column(String(80), nullable=False)
    resource_id: Mapped[str | None] = mapped_column(String(120), nullable=True)
    resource_label: Mapped[str | None] = mapped_column(String(255), nullable=True)
    result: Mapped[str] = mapped_column(String(40), default="success", nullable=False)
    metadata_json: Mapped[dict[str, Any] | None] = mapped_column("metadata", JSON, nullable=True)

    actor: Mapped[User | None] = relationship(lazy="selectin")
```

- [ ] **Step 4: Export AuditLog**

Modify `backend/app/models/__init__.py`:

```python
from app.models.audit import AuditLog
```

Add `"AuditLog"` to `__all__`.

- [ ] **Step 5: Add Alembic migration**

Create `backend/alembic/versions/20260628_0007_audit_logs.py`:

```python
from alembic import op
import sqlalchemy as sa

revision = "20260628_0007"
down_revision = "20260627_0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "audit_logs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("actor_user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("actor_username", sa.String(length=80), nullable=True),
        sa.Column("action", sa.String(length=120), nullable=False),
        sa.Column("resource_type", sa.String(length=80), nullable=False),
        sa.Column("resource_id", sa.String(length=120), nullable=True),
        sa.Column("resource_label", sa.String(length=255), nullable=True),
        sa.Column("result", sa.String(length=40), nullable=False, server_default="success"),
        sa.Column("metadata", sa.JSON(), nullable=True),
    )
    op.create_index("ix_audit_logs_occurred_at", "audit_logs", ["occurred_at"])
    op.create_index("ix_audit_logs_action", "audit_logs", ["action"])
    op.create_index("ix_audit_logs_resource_type", "audit_logs", ["resource_type"])
    op.create_index("ix_audit_logs_actor_user_id", "audit_logs", ["actor_user_id"])
    op.create_index("ix_audit_logs_result", "audit_logs", ["result"])


def downgrade() -> None:
    op.drop_index("ix_audit_logs_result", table_name="audit_logs")
    op.drop_index("ix_audit_logs_actor_user_id", table_name="audit_logs")
    op.drop_index("ix_audit_logs_resource_type", table_name="audit_logs")
    op.drop_index("ix_audit_logs_action", table_name="audit_logs")
    op.drop_index("ix_audit_logs_occurred_at", table_name="audit_logs")
    op.drop_table("audit_logs")
```

- [ ] **Step 6: Run model and migration tests**

Run from `backend`:

```powershell
python -m pytest tests/test_database_models.py::test_audit_log_table_is_registered tests/test_database_models.py::test_audit_log_model_persists_actor_resource_and_metadata tests/test_database_models.py::test_audit_log_migration_exists_and_round_trips -v
```

Expected: PASS.

- [ ] **Step 7: Commit Task 1**

```powershell
git add backend/app/models/audit.py backend/app/models/__init__.py backend/alembic/versions/20260628_0007_audit_logs.py backend/tests/test_database_models.py
git commit -m "feat: add audit log model"
```

---

## Task 2: Audit Schemas And Service

**Files:**
- Create: `backend/app/schemas/audit.py`
- Create: `backend/app/services/audit.py`
- Create: `backend/tests/test_audit_service.py`

- [ ] **Step 1: Write failing service tests**

Create `backend/tests/test_audit_service.py`:

```python
from datetime import datetime, timedelta, timezone

import pytest

from app.models import AuditLog, User
from app.services.audit import (
    get_audit_log,
    list_audit_logs,
    record_audit_log,
)
from app.schemas.audit import AuditLogListQuery


def create_actor(db_session, username: str = "auditor") -> User:
    user = User(
        username=username,
        password_hash="hashed-password",
        display_name=username.title(),
    )
    db_session.add(user)
    db_session.flush()
    return user


def test_record_audit_log_sanitizes_metadata_without_committing(db_session) -> None:
    actor = create_actor(db_session)

    log = record_audit_log(
        db_session,
        actor=actor,
        action="admin.user.update",
        resource_type="user",
        resource_id=42,
        resource_label="manager",
        metadata={
            "changed_fields": {"roles", "display_name"},
            "ignored": object(),
            "password": "Secret123!",
            "token": "secret-token",
        },
    )

    assert log.id is None
    assert log.actor_user_id == actor.id
    assert log.actor_username == "auditor"
    assert log.resource_id == "42"
    assert log.metadata_json == {
        "changed_fields": ["display_name", "roles"],
    }

    db_session.commit()
    assert db_session.query(AuditLog).count() == 1


def test_list_audit_logs_filters_and_searches(db_session) -> None:
    actor = create_actor(db_session, "admin")
    other = create_actor(db_session, "other")
    record_audit_log(
        db_session,
        actor=actor,
        action="auth.login",
        resource_type="auth_session",
        resource_id="session-1",
        resource_label="admin",
        result="success",
        metadata={"ip": "127.0.0.1"},
    )
    record_audit_log(
        db_session,
        actor=other,
        action="config.residence.update",
        resource_type="residence",
        resource_id="7",
        resource_label="Lake House",
        result="success",
        metadata={"is_active": False},
    )
    db_session.commit()

    response = list_audit_logs(
        db_session,
        AuditLogListQuery(
            resource_type="residence",
            search="lake",
            page=1,
            page_size=20,
        ),
    )

    assert response.total == 1
    assert response.items[0].action == "config.residence.update"
    assert response.items[0].metadata == {"is_active": False}


def test_list_audit_logs_filters_by_date_range(db_session) -> None:
    actor = create_actor(db_session)
    old_log = record_audit_log(
        db_session,
        actor=actor,
        action="auth.login",
        resource_type="auth_session",
        resource_id="old",
    )
    new_log = record_audit_log(
        db_session,
        actor=actor,
        action="auth.logout",
        resource_type="auth_session",
        resource_id="new",
    )
    db_session.commit()

    old_log.occurred_at = datetime.now(timezone.utc) - timedelta(days=3)
    new_log.occurred_at = datetime.now(timezone.utc)
    db_session.commit()

    response = list_audit_logs(
        db_session,
        AuditLogListQuery(
            occurred_from=datetime.now(timezone.utc) - timedelta(days=1),
            page=1,
            page_size=20,
        ),
    )

    assert response.total == 1
    assert response.items[0].resource_id == "new"


def test_get_audit_log_returns_detail_or_not_found(db_session) -> None:
    actor = create_actor(db_session)
    log = record_audit_log(
        db_session,
        actor=actor,
        action="auth.logout",
        resource_type="auth_session",
        resource_id="session-1",
    )
    db_session.commit()

    detail = get_audit_log(db_session, log.id)
    assert detail.id == log.id
    assert detail.action == "auth.logout"

    with pytest.raises(Exception) as exc_info:
        get_audit_log(db_session, 9999)
    assert getattr(exc_info.value, "detail", {}).get("message") == "日志不存在"
```

- [ ] **Step 2: Run tests to verify RED**

Run from `backend`:

```powershell
python -m pytest tests/test_audit_service.py -v
```

Expected: FAIL because `app.schemas.audit` and `app.services.audit` do not exist.

- [ ] **Step 3: Add audit schemas**

Create `backend/app/schemas/audit.py`:

```python
from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class AuditLogListQuery(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    action: str | None = Field(default=None, max_length=120)
    resource_type: str | None = Field(default=None, max_length=80)
    result: str | None = Field(default=None, max_length=40)
    actor_user_id: int | None = None
    search: str | None = Field(default=None, max_length=120)
    occurred_from: datetime | None = None
    occurred_to: datetime | None = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)


class AuditLogResponse(BaseModel):
    id: int
    occurred_at: datetime
    actor_user_id: int | None
    actor_username: str | None
    action: str
    resource_type: str
    resource_id: str | None
    resource_label: str | None
    result: str
    metadata: dict[str, Any] | None = None


class AuditLogListResponse(BaseModel):
    items: list[AuditLogResponse]
    total: int
    page: int
    page_size: int
```

- [ ] **Step 4: Add audit service**

Create `backend/app/services/audit.py`:

```python
from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from typing import Any

from fastapi import HTTPException
from sqlalchemy import Select, func, or_, select
from sqlalchemy.orm import Session

from app.core.errors import not_found
from app.models.audit import AuditLog
from app.models.auth import User
from app.schemas.audit import AuditLogListQuery, AuditLogListResponse, AuditLogResponse

SENSITIVE_METADATA_KEYS = {"password", "token", "access_token", "password_hash"}


def _json_safe(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, set):
        return sorted(str(item) for item in value)
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value if _json_safe(item) is not None]
    if isinstance(value, Mapping):
        return sanitize_metadata(value)
    return None


def sanitize_metadata(metadata: Mapping[str, Any] | None) -> dict[str, Any] | None:
    if not metadata:
        return None

    sanitized: dict[str, Any] = {}
    for key, value in metadata.items():
        if key in SENSITIVE_METADATA_KEYS:
            continue
        safe_value = _json_safe(value)
        if safe_value is not None:
            sanitized[key] = safe_value
    return sanitized or None


def serialize_audit_log(log: AuditLog) -> AuditLogResponse:
    return AuditLogResponse(
        id=log.id,
        occurred_at=log.occurred_at,
        actor_user_id=log.actor_user_id,
        actor_username=log.actor_username,
        action=log.action,
        resource_type=log.resource_type,
        resource_id=log.resource_id,
        resource_label=log.resource_label,
        result=log.result,
        metadata=log.metadata_json,
    )


def record_audit_log(
    db: Session,
    *,
    action: str,
    resource_type: str,
    actor: User | None = None,
    actor_user_id: int | None = None,
    actor_username: str | None = None,
    resource_id: str | int | None = None,
    resource_label: str | None = None,
    result: str = "success",
    metadata: Mapping[str, Any] | None = None,
) -> AuditLog:
    log = AuditLog(
        actor_user_id=actor.id if actor is not None else actor_user_id,
        actor_username=actor.username if actor is not None else actor_username,
        action=action,
        resource_type=resource_type,
        resource_id=str(resource_id) if resource_id is not None else None,
        resource_label=resource_label,
        result=result,
        metadata_json=sanitize_metadata(metadata),
    )
    db.add(log)
    return log


def _apply_filters(statement: Select[tuple[AuditLog]], query: AuditLogListQuery) -> Select[tuple[AuditLog]]:
    if query.action:
        statement = statement.where(AuditLog.action == query.action)
    if query.resource_type:
        statement = statement.where(AuditLog.resource_type == query.resource_type)
    if query.result:
        statement = statement.where(AuditLog.result == query.result)
    if query.actor_user_id is not None:
        statement = statement.where(AuditLog.actor_user_id == query.actor_user_id)
    if query.occurred_from is not None:
        statement = statement.where(AuditLog.occurred_at >= query.occurred_from)
    if query.occurred_to is not None:
        statement = statement.where(AuditLog.occurred_at <= query.occurred_to)
    if query.search:
        pattern = f"%{query.search}%"
        statement = statement.where(
            or_(
                AuditLog.actor_username.ilike(pattern),
                AuditLog.action.ilike(pattern),
                AuditLog.resource_type.ilike(pattern),
                AuditLog.resource_id.ilike(pattern),
                AuditLog.resource_label.ilike(pattern),
            )
        )
    return statement


def list_audit_logs(db: Session, query: AuditLogListQuery) -> AuditLogListResponse:
    filtered = _apply_filters(select(AuditLog), query)
    count_statement = _apply_filters(select(func.count(AuditLog.id)), query)

    total = db.scalar(count_statement) or 0
    logs = db.scalars(
        filtered
        .order_by(AuditLog.occurred_at.desc(), AuditLog.id.desc())
        .offset((query.page - 1) * query.page_size)
        .limit(query.page_size)
    ).all()

    return AuditLogListResponse(
        items=[serialize_audit_log(log) for log in logs],
        total=total,
        page=query.page,
        page_size=query.page_size,
    )


def get_audit_log(db: Session, log_id: int) -> AuditLogResponse:
    log = db.get(AuditLog, log_id)
    if log is None:
        raise not_found("日志不存在")
    return serialize_audit_log(log)
```

- [ ] **Step 5: Run service tests**

Run from `backend`:

```powershell
python -m pytest tests/test_audit_service.py -v
```

Expected: PASS.

- [ ] **Step 6: Commit Task 2**

```powershell
git add backend/app/schemas/audit.py backend/app/services/audit.py backend/tests/test_audit_service.py
git commit -m "feat: add audit log service"
```

---

## Task 3: Audit Read API

**Files:**
- Create: `backend/app/api/routes/audit.py`
- Create: `backend/tests/test_audit_api.py`
- Modify: `backend/app/api/router.py`

- [ ] **Step 1: Write failing API tests**

Create `backend/tests/test_audit_api.py`:

```python
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.main import app
from app.services.audit import record_audit_log
from app.services.admin import create_user
from app.schemas.admin import AdminUserCreate
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


def test_admin_can_list_and_view_audit_logs(client: TestClient, db_session: Session) -> None:
    headers = login(client)
    record = record_audit_log(
        db_session,
        action="admin.user.create",
        resource_type="user",
        resource_id=7,
        resource_label="manager",
        actor_username="admin",
        metadata={"changed_fields": ["roles"]},
    )
    db_session.commit()

    listed = client.get(
        "/api/audit/logs",
        headers=headers,
        params={"resource_type": "user", "search": "manager"},
    )
    assert listed.status_code == 200
    body = listed.json()
    assert body["total"] == 1
    assert body["items"][0]["id"] == record.id
    assert body["items"][0]["metadata"] == {"changed_fields": ["roles"]}

    detail = client.get(f"/api/audit/logs/{record.id}", headers=headers)
    assert detail.status_code == 200
    assert detail.json()["action"] == "admin.user.create"


def test_audit_logs_reject_viewer_without_logs_view(client: TestClient, db_session: Session) -> None:
    admin_headers = login(client)
    created = client.post(
        "/api/admin/users",
        headers=admin_headers,
        json={
            "username": "viewer",
            "display_name": "Viewer",
            "password": "Viewer123!",
            "role_codes": ["viewer"],
        },
    )
    assert created.status_code == 201
    viewer_headers = login(client, "viewer", "Viewer123!")

    listed = client.get("/api/audit/logs", headers=viewer_headers)
    assert listed.status_code == 403

    detail = client.get("/api/audit/logs/1", headers=viewer_headers)
    assert detail.status_code == 403


def test_audit_log_detail_returns_not_found(client: TestClient) -> None:
    headers = login(client)

    response = client.get("/api/audit/logs/9999", headers=headers)

    assert response.status_code == 404
    assert response.json()["message"] == "日志不存在"
```

- [ ] **Step 2: Run tests to verify RED**

Run from `backend`:

```powershell
python -m pytest tests/test_audit_api.py -v
```

Expected: FAIL because `/api/audit/logs` is not registered.

- [ ] **Step 3: Add audit routes**

Create `backend/app/api/routes/audit.py`:

```python
from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_permission
from app.models.auth import User
from app.schemas.audit import AuditLogListQuery, AuditLogListResponse, AuditLogResponse
from app.services.audit import get_audit_log, list_audit_logs

router = APIRouter(prefix="/audit", tags=["audit"])


@router.get("/logs", response_model=AuditLogListResponse)
def audit_logs(
    action: str | None = Query(default=None, max_length=120),
    resource_type: str | None = Query(default=None, max_length=80),
    result: str | None = Query(default=None, max_length=40),
    actor_user_id: int | None = None,
    search: str | None = Query(default=None, max_length=120),
    occurred_from: datetime | None = None,
    occurred_to: datetime | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("logs:view")),
) -> AuditLogListResponse:
    query = AuditLogListQuery(
        action=action,
        resource_type=resource_type,
        result=result,
        actor_user_id=actor_user_id,
        search=search,
        occurred_from=occurred_from,
        occurred_to=occurred_to,
        page=page,
        page_size=page_size,
    )
    return list_audit_logs(db, query)


@router.get("/logs/{log_id}", response_model=AuditLogResponse)
def audit_log_detail(
    log_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("logs:view")),
) -> AuditLogResponse:
    return get_audit_log(db, log_id)
```

- [ ] **Step 4: Include audit router**

Modify `backend/app/api/router.py`:

```python
from app.api.routes import admin, audit, auth, configuration, health, inventory, reminders
```

Add:

```python
api_router.include_router(audit.router)
```

Place it after `admin.router` or before `configuration.router`.

- [ ] **Step 5: Run API tests**

Run from `backend`:

```powershell
python -m pytest tests/test_audit_api.py -v
```

Expected: PASS.

- [ ] **Step 6: Commit Task 3**

```powershell
git add backend/app/api/routes/audit.py backend/app/api/router.py backend/tests/test_audit_api.py
git commit -m "feat: expose audit log api"
```

---

## Task 4: Authentication Audit Writes

**Files:**
- Modify: `backend/app/services/auth.py`
- Modify: `backend/app/api/routes/auth.py`
- Modify: `backend/tests/test_auth_api.py`

- [ ] **Step 1: Write failing auth audit tests**

In `backend/tests/test_auth_api.py`, import `AuditLog`:

```python
from app.models import AuditLog
```

Add assertions to existing login/logout tests or add focused tests:

```python
def test_login_success_and_failure_write_audit_logs(client: TestClient, db_session) -> None:
    success = client.post(
        "/api/auth/login",
        json={"username": "admin", "password": "ChangeMe123!"},
    )
    assert success.status_code == 200

    failure = client.post(
        "/api/auth/login",
        json={"username": "admin", "password": "wrong"},
    )
    assert failure.status_code == 401

    logs = db_session.query(AuditLog).order_by(AuditLog.id).all()
    assert [log.action for log in logs[-2:]] == ["auth.login", "auth.login"]
    assert [log.result for log in logs[-2:]] == ["success", "failure"]
    assert logs[-1].metadata_json == {"attempted_username": "admin"}
    assert "password" not in (logs[-1].metadata_json or {})


def test_logout_writes_audit_log(client: TestClient, db_session) -> None:
    login = client.post(
        "/api/auth/login",
        json={"username": "admin", "password": "ChangeMe123!"},
    )
    token = login.json()["access_token"]

    logout = client.post("/api/auth/logout", headers={"Authorization": f"Bearer {token}"})

    assert logout.status_code == 204
    log = db_session.query(AuditLog).order_by(AuditLog.id.desc()).first()
    assert log is not None
    assert log.action == "auth.logout"
    assert log.resource_type == "auth_session"
    assert log.result == "success"
```

- [ ] **Step 2: Run tests to verify RED**

Run from `backend`:

```powershell
python -m pytest tests/test_auth_api.py::test_login_success_and_failure_write_audit_logs tests/test_auth_api.py::test_logout_writes_audit_log -v
```

Expected: FAIL because auth routes do not record audit entries.

- [ ] **Step 3: Make auth session helpers transaction-friendly**

Modify `backend/app/services/auth.py`.

Change `create_login_session` so it flushes but does not commit:

```python
def create_login_session(db: Session, user: User) -> tuple[str, AuthSession]:
    settings = get_settings()
    session = AuthSession(
        session_id=uuid4().hex,
        user_id=user.id,
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=settings.access_token_minutes),
        is_active=True,
    )
    db.add(session)
    db.flush()
    token = create_access_token(
        user_id=user.id,
        session_id=session.session_id,
        secret_key=settings.secret_key,
        minutes=settings.access_token_minutes,
    )
    return token, session
```

Change `revoke_session` so it mutates but does not commit:

```python
def revoke_session(db: Session, session: AuthSession) -> None:
    session.is_active = False
    session.revoked_at = datetime.now(timezone.utc)
```

- [ ] **Step 4: Record audit entries in auth routes**

Modify `backend/app/api/routes/auth.py` imports:

```python
from app.services.audit import record_audit_log
```

Update `login`:

```python
@router.post("/login", response_model=LoginResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> LoginResponse:
    user = authenticate_user(db, payload.username, payload.password)
    if user is None:
        record_audit_log(
            db,
            action="auth.login",
            resource_type="auth_session",
            result="failure",
            metadata={"attempted_username": payload.username},
        )
        db.commit()
        raise unauthorized("账号或密码不正确")

    access_token, session = create_login_session(db, user)
    record_audit_log(
        db,
        actor=user,
        action="auth.login",
        resource_type="auth_session",
        resource_id=session.session_id,
        resource_label=user.username,
        result="success",
    )
    db.commit()
    return LoginResponse(access_token=access_token, user=serialize_current_user(user))
```

Update `logout`:

```python
@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    user_and_session: tuple[User, AuthSession] = Depends(get_current_user_and_session),
    db: Session = Depends(get_db),
) -> Response:
    user, session = user_and_session
    revoke_session(db, session)
    record_audit_log(
        db,
        actor=user,
        action="auth.logout",
        resource_type="auth_session",
        resource_id=session.session_id,
        resource_label=user.username,
        result="success",
    )
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
```

- [ ] **Step 5: Run auth tests**

Run from `backend`:

```powershell
python -m pytest tests/test_auth_api.py -v
```

Expected: PASS.

- [ ] **Step 6: Commit Task 4**

```powershell
git add backend/app/services/auth.py backend/app/api/routes/auth.py backend/tests/test_auth_api.py
git commit -m "feat: audit authentication events"
```

---

## Task 5: Admin And Configuration Audit Writes

**Files:**
- Modify: `backend/app/api/routes/admin.py`
- Modify: `backend/app/services/admin.py`
- Modify: `backend/app/api/routes/configuration.py`
- Modify: `backend/app/services/configuration.py`
- Modify: `backend/tests/test_admin_users.py`
- Modify: `backend/tests/test_configuration_api.py`

- [ ] **Step 1: Write failing admin audit tests**

In `backend/tests/test_admin_users.py`, import `AuditLog` if not already available:

```python
from app.models.auth import AuthSession, User
from app.models.audit import AuditLog
```

Add this focused test:

```python
def test_admin_user_mutations_write_audit_logs(client: TestClient, db_session: Session) -> None:
    headers = login(client)

    created = client.post(
        "/api/admin/users",
        headers=headers,
        json={
            "username": "audited",
            "display_name": "Audited",
            "password": "Audited123!",
            "role_codes": ["viewer"],
        },
    )
    assert created.status_code == 201
    user_id = created.json()["id"]

    updated = client.patch(
        f"/api/admin/users/{user_id}",
        headers=headers,
        json={"display_name": "Audited User", "is_active": False, "role_codes": ["viewer"]},
    )
    assert updated.status_code == 200

    reset = client.post(
        f"/api/admin/users/{user_id}/reset-password",
        headers=headers,
        json={"password": "NewAudited123!"},
    )
    assert reset.status_code == 200

    logs = db_session.query(AuditLog).filter(AuditLog.resource_id == str(user_id)).order_by(AuditLog.id).all()
    assert [log.action for log in logs] == [
        "admin.user.create",
        "admin.user.update",
        "admin.user.reset_password",
    ]
    assert all(log.actor_username == "admin" for log in logs)
    assert logs[1].metadata_json == {
        "changed_fields": ["display_name", "is_active", "role_codes"],
        "role_codes": ["viewer"],
        "is_active": False,
    }
    assert "password" not in (logs[2].metadata_json or {})
```

- [ ] **Step 2: Write failing configuration audit test**

In `backend/tests/test_configuration_api.py`, import `AuditLog`:

```python
from app.models.audit import AuditLog
```

Add a focused test:

```python
def test_configuration_mutations_write_audit_logs(client: TestClient, db_session: Session) -> None:
    headers = login(client)

    residence = client.post(
        "/api/config/residences",
        headers=headers,
        json={"name": "Audit Home", "description": "", "address": "", "sort_order": 1},
    )
    assert residence.status_code == 201
    residence_id = residence.json()["id"]

    updated = client.patch(
        f"/api/config/residences/{residence_id}",
        headers=headers,
        json={
            "name": "Audit Home",
            "description": "Updated",
            "address": "",
            "sort_order": 1,
            "is_active": False,
        },
    )
    assert updated.status_code == 200

    location = client.post(
        "/api/config/location-nodes",
        headers=headers,
        json={"residence_id": residence_id, "name": "Shelf", "node_type": "area"},
    )
    assert location.status_code == 201

    actions = [
        log.action
        for log in db_session.query(AuditLog).order_by(AuditLog.id).all()
        if log.action.startswith("config.")
    ]
    assert "config.residence.create" in actions
    assert "config.residence.update" in actions
    assert "config.location.create" in actions
```

- [ ] **Step 3: Run tests to verify RED**

Run from `backend`:

```powershell
python -m pytest tests/test_admin_users.py::test_admin_user_mutations_write_audit_logs tests/test_configuration_api.py::test_configuration_mutations_write_audit_logs -v
```

Expected: FAIL because admin/configuration mutations do not write audit entries.

- [ ] **Step 4: Record admin user audit events**

Modify `backend/app/api/routes/admin.py` so the authenticated route user is passed into mutation services:

```python
return create_user_record(db, payload, actor=user)
return update_user_record(db, user_id, payload, actor=user)
return reset_user_password_record(db, user_id, payload, actor=user)
```

Modify `backend/app/services/admin.py` imports:

```python
from app.services.audit import record_audit_log
```

Change signatures:

```python
def create_user(db: Session, payload: AdminUserCreate, actor: User | None = None) -> AdminUserResponse:
def update_user(db: Session, user_id: int, payload: AdminUserUpdate, actor: User | None = None) -> AdminUserResponse:
def reset_user_password(db: Session, user_id: int, payload: AdminPasswordReset, actor: User | None = None) -> AdminUserResponse:
```

In `create_user`, after `db.add(user)` and before `db.commit()`, flush so the id exists, then record:

```python
db.add(user)
db.flush()
record_audit_log(
    db,
    actor=actor,
    action="admin.user.create",
    resource_type="user",
    resource_id=user.id,
    resource_label=user.username,
    metadata={"role_codes": sorted(roles_by_code)},
)
```

In `update_user`, before mutating, compute changed fields:

```python
changed_fields = []
if user.display_name != payload.display_name:
    changed_fields.append("display_name")
if user.is_active != payload.is_active:
    changed_fields.append("is_active")
if sorted(role.code for role in user.roles) != normalized_role_codes:
    changed_fields.append("role_codes")
```

After assigning fields and before commit:

```python
record_audit_log(
    db,
    actor=actor,
    action="admin.user.update",
    resource_type="user",
    resource_id=user.id,
    resource_label=user.username,
    metadata={
        "changed_fields": changed_fields,
        "role_codes": normalized_role_codes,
        "is_active": user.is_active,
    },
)
```

In `reset_user_password`, before commit:

```python
record_audit_log(
    db,
    actor=actor,
    action="admin.user.reset_password",
    resource_type="user",
    resource_id=user.id,
    resource_label=user.username,
    metadata={"revoked_session_count": len(sessions)},
)
```

- [ ] **Step 5: Record configuration audit events**

Modify `backend/app/api/routes/configuration.py` so mutation routes pass `actor=user` into service functions for these routes:

```python
return create_residence_record(db, payload, actor=user)
return update_residence_record(db, residence_id, payload, actor=user)
return create_location_node_record(db, payload, actor=user)
return create_family_member_record(db, payload, actor=user)
return create_category_record(db, payload, actor=user)
return create_attribute_definition_record(db, payload, actor=user)
```

Modify `backend/app/services/configuration.py` imports:

```python
from app.models.auth import User
from app.services.audit import record_audit_log
```

Change these signatures:

```python
def create_residence(db: Session, payload: ResidenceCreate, actor: User | None = None) -> ResidenceResponse:
def update_residence(db: Session, residence_id: int, payload: ResidenceUpdate, actor: User | None = None) -> ResidenceResponse:
def create_location_node(db: Session, payload: LocationNodeCreate, actor: User | None = None) -> LocationNodeResponse:
def create_family_member(db: Session, payload: FamilyMemberCreate, actor: User | None = None) -> FamilyMemberResponse:
def create_category(db: Session, payload: CategoryCreate, actor: User | None = None) -> CategoryResponse:
def create_attribute_definition(db: Session, payload: AttributeDefinitionCreate, actor: User | None = None) -> AttributeDefinitionResponse:
```

For create functions, call `db.flush()` after adding the object and before commit when an id is needed. Record events before the existing commit. Use these action/resource mappings:

```python
record_audit_log(
    db,
    actor=actor,
    action="config.residence.create",
    resource_type="residence",
    resource_id=residence.id,
    resource_label=residence.name,
    metadata={"is_active": residence.is_active},
)
```

```python
record_audit_log(
    db,
    actor=actor,
    action="config.residence.update",
    resource_type="residence",
    resource_id=residence.id,
    resource_label=residence.name,
    metadata={"is_active": residence.is_active},
)
```

```python
record_audit_log(
    db,
    actor=actor,
    action="config.location.create",
    resource_type="location_node",
    resource_id=node.id,
    resource_label=node.name,
    metadata={"residence_id": node.residence_id},
)
```

```python
record_audit_log(
    db,
    actor=actor,
    action="config.family_member.create",
    resource_type="family_member",
    resource_id=member.id,
    resource_label=member.name,
)
```

```python
record_audit_log(
    db,
    actor=actor,
    action="config.category.create",
    resource_type="category",
    resource_id=category.id,
    resource_label=category.name,
    metadata={"code": category.code},
)
```

```python
record_audit_log(
    db,
    actor=actor,
    action="config.attribute_definition.create",
    resource_type="attribute_definition",
    resource_id=definition.id,
    resource_label=definition.name,
    metadata={"category_id": definition.category_id, "key": definition.key},
)
```

- [ ] **Step 6: Run focused audit mutation tests**

Run from `backend`:

```powershell
python -m pytest tests/test_admin_users.py::test_admin_user_mutations_write_audit_logs tests/test_configuration_api.py::test_configuration_mutations_write_audit_logs -v
```

Expected: PASS.

- [ ] **Step 7: Run broader touched suites**

Run from `backend`:

```powershell
python -m pytest tests/test_admin_users.py tests/test_configuration_api.py -v
```

Expected: PASS.

- [ ] **Step 8: Commit Task 5**

```powershell
git add backend/app/api/routes/admin.py backend/app/services/admin.py backend/app/api/routes/configuration.py backend/app/services/configuration.py backend/tests/test_admin_users.py backend/tests/test_configuration_api.py
git commit -m "feat: audit admin and configuration changes"
```

---

## Task 6: Frontend Audit API Contract

**Files:**
- Create: `frontend/src/api/audit.ts`
- Create: `frontend/tests/audit-contract.ts`
- Create: `frontend/tests/audit-contract.mjs`

- [ ] **Step 1: Write failing TypeScript contract**

Create `frontend/tests/audit-contract.ts`:

```ts
import {
  getAuditLogApi,
  listAuditLogsApi,
  type AuditLogEntry,
  type AuditLogFilters,
  type AuditLogListResponse
} from '../src/api/audit'

function expectType<T>(_value: T): void {}

const filters: AuditLogFilters = {
  action: 'auth.login',
  resource_type: 'auth_session',
  result: 'success',
  actor_user_id: 1,
  search: 'admin',
  occurred_from: '2026-06-01T00:00:00Z',
  occurred_to: '2026-06-30T23:59:59Z',
  page: 1,
  page_size: 20
}

async function assertAuditApiContract() {
  expectType<AuditLogListResponse>(await listAuditLogsApi(filters))
  expectType<AuditLogEntry>(await getAuditLogApi(1))
}

void assertAuditApiContract
```

- [ ] **Step 2: Write failing source contract**

Create `frontend/tests/audit-contract.mjs`:

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

const auditApi = readSource('src/api/audit.ts')
const routerSource = readSource('src/router/index.ts')
const layoutSource = readSource('src/layouts/AppLayout.vue')

assert.match(auditApi, /export interface AuditLogEntry/, 'Audit API should export AuditLogEntry')
assert.match(auditApi, /export interface AuditLogFilters/, 'Audit API should export AuditLogFilters')
assert.match(auditApi, /export interface AuditLogListResponse/, 'Audit API should export AuditLogListResponse')
assert.match(auditApi, /apiClient\.get<AuditLogListResponse>\('\/audit\/logs'/, 'Audit API should list logs')
assert.match(auditApi, /apiClient\.get<AuditLogEntry>\(`\/audit\/logs\/\$\{logId\}`\)/, 'Audit API should get one log')
assert.doesNotMatch(routerSource, /admin\/logs/, 'Phase 4B-1 should not add a visible admin logs route')
assert.doesNotMatch(layoutSource, /\/admin\/logs/, 'Phase 4B-1 should not add an admin logs nav item')
```

- [ ] **Step 3: Run contracts to verify RED**

Run from `frontend`:

```powershell
node .\tests\audit-contract.mjs
.\node_modules\.bin\vue-tsc.cmd --noEmit -p tsconfig.contract.json
```

Expected: FAIL because `src/api/audit.ts` does not exist.

- [ ] **Step 4: Add typed audit API helpers**

Create `frontend/src/api/audit.ts`:

```ts
import { apiClient } from './client'

export interface AuditLogEntry {
  id: number
  occurred_at: string
  actor_user_id: number | null
  actor_username: string | null
  action: string
  resource_type: string
  resource_id: string | null
  resource_label: string | null
  result: string
  metadata: Record<string, unknown> | null
}

export interface AuditLogListResponse {
  items: AuditLogEntry[]
  total: number
  page: number
  page_size: number
}

export interface AuditLogFilters {
  action?: string | null
  resource_type?: string | null
  result?: string | null
  actor_user_id?: number | null
  search?: string | null
  occurred_from?: string | null
  occurred_to?: string | null
  page?: number
  page_size?: number
}

export async function listAuditLogsApi(filters: AuditLogFilters = {}): Promise<AuditLogListResponse> {
  const response = await apiClient.get<AuditLogListResponse>('/audit/logs', { params: filters })
  return response.data
}

export async function getAuditLogApi(logId: number): Promise<AuditLogEntry> {
  const response = await apiClient.get<AuditLogEntry>(`/audit/logs/${logId}`)
  return response.data
}
```

- [ ] **Step 5: Run frontend contracts**

Run from `frontend`:

```powershell
node .\tests\audit-contract.mjs
.\node_modules\.bin\vue-tsc.cmd --noEmit -p tsconfig.contract.json
```

Expected: PASS.

- [ ] **Step 6: Commit Task 6**

```powershell
git add frontend/src/api/audit.ts frontend/tests/audit-contract.ts frontend/tests/audit-contract.mjs
git commit -m "feat: add audit frontend contract"
```

---

## Task 7: Full Verification And Review

**Files:**
- Existing files changed by Tasks 1-6.

- [ ] **Step 1: Run backend full test suite**

Run from `backend`:

```powershell
python -m pytest -v
```

Expected: all tests pass. The existing Starlette/httpx deprecation warning may remain.

- [ ] **Step 2: Run frontend contracts**

Run from `frontend`:

```powershell
node .\tests\audit-contract.mjs
node .\tests\admin-users-ui-contract.mjs
node .\tests\reminder-ui-contract.mjs
node .\tests\phase-copy-contract.mjs
node .\tests\reminder-date-contract.mjs
node .\tests\reminders-store-runtime.mjs
node .\tests\admin-users-store-runtime.mjs
.\node_modules\.bin\vue-tsc.cmd --noEmit -p tsconfig.contract.json
```

Expected: all commands exit 0. A Vite WebSocket port warning from runtime scripts is acceptable only if the command exit code is 0.

- [ ] **Step 3: Run frontend production build**

Run from `frontend`:

```powershell
npm.cmd run build
```

Expected: build exits 0. Existing Rollup `#__PURE__` and chunk-size warnings may remain.

- [ ] **Step 4: Run diff and status checks**

Run from repository root:

```powershell
git diff --check
git status --short --branch
git log --oneline -10
```

Expected: no whitespace errors; worktree clean; recent commits are the intentional Phase 4B-1 commits.

- [ ] **Step 5: Request final code review**

Use `superpowers:requesting-code-review` with the base SHA before Task 1 and current HEAD.

Review focus:

- Audit model and migration correctness.
- Audit write atomicity with auth/admin/config operations.
- Permission boundary for `logs:view`.
- Metadata privacy: no password/token/hash/request-body storage.
- Frontend contract stability without adding the 4B-2 UI route.

- [ ] **Step 6: Handle required review fixes**

If the reviewer finds Critical or Important issues:

1. Write the smallest failing test for the issue.
2. Implement the fix.
3. Rerun focused tests.
4. Rerun full verification from Steps 1-4.
5. Commit with:

```powershell
git add <changed files>
git commit -m "fix: address phase 4b audit review"
```

If the reviewer finds no Critical or Important issues, do not create an empty commit.

- [ ] **Step 7: Push when ready**

When verification and review are complete:

```powershell
git push
```

Expected: current `phase-1-foundation` branch pushes to `origin/phase-1-foundation`.

---

## Plan Self-Review Checklist

- Spec coverage:
  - Persisted audit model and migration: Task 1.
  - Audit service record/list/detail: Task 2.
  - Read API guarded by `logs:view`: Task 3.
  - Auth audit events: Task 4.
  - Admin/config mutation audit events: Task 5.
  - Frontend typed helpers without visible UI route: Task 6.
  - Full verification and review: Task 7.
- Red-flag scan: no unfinished markers are intentionally left in the plan.
- Type consistency:
  - ORM field is `metadata_json`.
  - API/schema/frontend field is `metadata`.
  - Date filters are `occurred_from` and `occurred_to`.
  - List payload uses `items`, `total`, `page`, and `page_size`.
