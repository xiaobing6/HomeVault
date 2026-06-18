# HomeVault Phase 1 Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a runnable HomeVault foundation with FastAPI backend, SQLite migrations, token login, seeded RBAC roles, and a Vue/Element Plus login and dashboard shell.

**Architecture:** Phase 1 creates the API-first base that later inventory modules will reuse. The backend owns authentication, sessions, RBAC, database access, and structured Chinese errors; the frontend owns token storage, route guards, role-aware menus, and the warm desktop shell.

**Tech Stack:** FastAPI, SQLAlchemy 2, Alembic, Pydantic Settings, PyJWT, pwdlib Argon2, pytest, Vue 3, Vite, TypeScript, Vue Router, Pinia, Element Plus, Playwright CLI verification.

---

## Scope Check

The approved design describes a full product with several coupled modules. This plan intentionally implements the first independently testable slice:

- backend project scaffold
- SQLite database base with Alembic
- auth and RBAC tables
- initial admin seeding
- token login/logout/current-user APIs
- frontend login, route guard, dashboard shell, and permission-aware navigation
- Phase 1 backend tests and browser smoke verification

Separate implementation plans should cover the next slices:

- core configuration: family space, residences, location tree, members, categories, field definitions, dictionaries
- item inventory: items, images, custom values, tags, containers, movement history, quantity history, loan flow, reminders
- end-to-end acceptance: full Playwright browser flows across admin, editor, and viewer roles

## File Structure

Create this structure:

```text
backend/
  alembic.ini
  pyproject.toml
  .env.example
  alembic/
    env.py
    versions/
      20260618_0001_auth_base.py
  app/
    __init__.py
    main.py
    api/
      __init__.py
      deps.py
      router.py
      routes/
        __init__.py
        auth.py
        health.py
    core/
      __init__.py
      config.py
      errors.py
      security.py
    db/
      __init__.py
      base.py
      session.py
    models/
      __init__.py
      auth.py
    schemas/
      __init__.py
      auth.py
      user.py
    services/
      __init__.py
      auth.py
      seed.py
  tests/
    conftest.py
    test_auth_api.py
    test_database_models.py
    test_health.py
    test_security.py
    test_seed.py
frontend/
  index.html
  package.json
  tsconfig.json
  tsconfig.node.json
  vite.config.ts
  src/
    App.vue
    main.ts
    api/
      auth.ts
      client.ts
    components/
      PermissionGate.vue
    layouts/
      AppLayout.vue
    pages/
      DashboardPage.vue
      ForbiddenPage.vue
      LoginPage.vue
      NotFoundPage.vue
    router/
      index.ts
    stores/
      auth.ts
    styles/
      theme.css
output/
  playwright/
```

## Task 1: Backend Scaffold And Health API

**Files:**
- Create: `backend/pyproject.toml`
- Create: `backend/.env.example`
- Create: `backend/app/__init__.py`
- Create: `backend/app/main.py`
- Create: `backend/app/api/__init__.py`
- Create: `backend/app/api/router.py`
- Create: `backend/app/api/routes/__init__.py`
- Create: `backend/app/api/routes/health.py`
- Create: `backend/app/core/__init__.py`
- Create: `backend/app/core/config.py`
- Create: `backend/tests/test_health.py`

- [ ] **Step 1: Create backend dependency manifest**

Create `backend/pyproject.toml`:

```toml
[project]
name = "homevault-backend"
version = "0.1.0"
description = "HomeVault API service"
requires-python = ">=3.11"
dependencies = [
  "fastapi>=0.115,<1.0",
  "uvicorn[standard]>=0.30,<1.0",
  "SQLAlchemy>=2.0,<3.0",
  "alembic>=1.13,<2.0",
  "pydantic-settings>=2.4,<3.0",
  "PyJWT>=2.9,<3.0",
  "pwdlib[argon2]>=0.2,<1.0",
  "python-multipart>=0.0.9,<1.0"
]

[project.optional-dependencies]
dev = [
  "pytest>=8.2,<9.0",
  "httpx>=0.27,<1.0"
]

[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["."]
```

Create `backend/.env.example`:

```dotenv
HOMEVAULT_APP_NAME=HomeVault API
HOMEVAULT_DATABASE_URL=sqlite:///./homevault.db
HOMEVAULT_SECRET_KEY=replace-this-with-a-long-random-secret
HOMEVAULT_ACCESS_TOKEN_MINUTES=480
HOMEVAULT_ADMIN_USERNAME=admin
HOMEVAULT_ADMIN_PASSWORD=ChangeMe123!
```

- [ ] **Step 2: Write the failing health test**

Create `backend/tests/test_health.py`:

```python
from fastapi.testclient import TestClient

from app.main import app


def test_health_returns_ok() -> None:
    client = TestClient(app)

    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "HomeVault API"}
```

- [ ] **Step 3: Run the health test and confirm it fails**

Run:

```powershell
Set-Location backend
python -m pytest tests/test_health.py -v
```

Expected: FAIL because `app.main` does not exist.

- [ ] **Step 4: Create the minimal FastAPI app**

Create `backend/app/__init__.py`:

```python
"""HomeVault backend package."""
```

Create `backend/app/core/__init__.py`:

```python
"""Core backend utilities."""
```

Create `backend/app/core/config.py`:

```python
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "HomeVault API"
    database_url: str = "sqlite:///./homevault.db"
    secret_key: str = "dev-secret-change-before-production"
    access_token_minutes: int = 480
    admin_username: str = "admin"
    admin_password: str = "ChangeMe123!"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="HOMEVAULT_",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
```

Create `backend/app/api/__init__.py`:

```python
"""API package."""
```

Create `backend/app/api/routes/__init__.py`:

```python
"""API route modules."""
```

Create `backend/app/api/routes/health.py`:

```python
from fastapi import APIRouter

from app.core.config import get_settings

router = APIRouter(tags=["health"])


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": get_settings().app_name}
```

Create `backend/app/api/router.py`:

```python
from fastapi import APIRouter

from app.api.routes import health

api_router = APIRouter()
api_router.include_router(health.router)
```

Create `backend/app/main.py`:

```python
from fastapi import FastAPI

from app.api.router import api_router
from app.core.config import get_settings


def create_app() -> FastAPI:
    settings = get_settings()
    application = FastAPI(title=settings.app_name, version="0.1.0")
    application.include_router(api_router, prefix="/api")
    return application


app = create_app()
```

- [ ] **Step 5: Run the health test and confirm it passes**

Run:

```powershell
Set-Location backend
python -m pytest tests/test_health.py -v
```

Expected: PASS.

- [ ] **Step 6: Commit Task 1**

Run:

```powershell
git add backend
git commit -m "feat: scaffold backend health api"
```

## Task 2: Database Base, Auth Models, And Migration

**Files:**
- Create: `backend/app/db/__init__.py`
- Create: `backend/app/db/base.py`
- Create: `backend/app/db/session.py`
- Create: `backend/app/models/__init__.py`
- Create: `backend/app/models/auth.py`
- Create: `backend/alembic.ini`
- Create: `backend/alembic/env.py`
- Create: `backend/alembic/versions/20260618_0001_auth_base.py`
- Create: `backend/tests/conftest.py`
- Create: `backend/tests/test_database_models.py`

- [ ] **Step 1: Write the failing database model test**

Create `backend/tests/conftest.py`:

```python
from collections.abc import Iterator

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.db.base import Base
from app import models as _models


@pytest.fixture()
def db_session() -> Iterator[Session]:
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        future=True,
    )
    TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
```

Create `backend/tests/test_database_models.py`:

```python
from app.db.base import Base


def test_auth_tables_are_registered() -> None:
    expected_tables = {
        "users",
        "roles",
        "permissions",
        "user_roles",
        "role_permissions",
        "auth_sessions",
        "external_identities",
    }

    assert expected_tables.issubset(set(Base.metadata.tables))
```

- [ ] **Step 2: Run the database model test and confirm it fails**

Run:

```powershell
Set-Location backend
python -m pytest tests/test_database_models.py -v
```

Expected: FAIL because the database base and models do not exist.

- [ ] **Step 3: Create the SQLAlchemy database base and session**

Create `backend/app/db/__init__.py`:

```python
"""Database package."""
```

Create `backend/app/db/base.py`:

```python
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass
```

Create `backend/app/db/session.py`:

```python
from collections.abc import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings


def _connect_args(database_url: str) -> dict[str, bool]:
    if database_url.startswith("sqlite"):
        return {"check_same_thread": False}
    return {}


settings = get_settings()
engine = create_engine(
    settings.database_url,
    connect_args=_connect_args(settings.database_url),
    future=True,
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def get_db() -> Iterator[Session]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

- [ ] **Step 4: Create auth and RBAC models**

Create `backend/app/models/__init__.py`:

```python
from app.models.auth import AuthSession, ExternalIdentity, Permission, Role, User

__all__ = ["AuthSession", "ExternalIdentity", "Permission", "Role", "User"]
```

Create `backend/app/models/auth.py`:

```python
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Table, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


user_roles = Table(
    "user_roles",
    Base.metadata,
    Column("user_id", ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
    Column("role_id", ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True),
)


role_permissions = Table(
    "role_permissions",
    Base.metadata,
    Column("role_id", ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True),
    Column("permission_id", ForeignKey("permissions.id", ondelete="CASCADE"), primary_key=True),
)


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    username: Mapped[str] = mapped_column(String(80), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    display_name: Mapped[str] = mapped_column(String(120), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utcnow,
        onupdate=utcnow,
        nullable=False,
    )

    roles: Mapped[list[Role]] = relationship(
        secondary=user_roles,
        back_populates="users",
        lazy="selectin",
    )
    sessions: Mapped[list[AuthSession]] = relationship(back_populates="user", lazy="selectin")


class Role(Base):
    __tablename__ = "roles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    code: Mapped[str] = mapped_column(String(80), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    is_system: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    users: Mapped[list[User]] = relationship(
        secondary=user_roles,
        back_populates="roles",
        lazy="selectin",
    )
    permissions: Mapped[list[Permission]] = relationship(
        secondary=role_permissions,
        back_populates="roles",
        lazy="selectin",
    )


class Permission(Base):
    __tablename__ = "permissions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    code: Mapped[str] = mapped_column(String(120), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str] = mapped_column(String(255), default="", nullable=False)

    roles: Mapped[list[Role]] = relationship(
        secondary=role_permissions,
        back_populates="permissions",
        lazy="selectin",
    )


class AuthSession(Base):
    __tablename__ = "auth_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    session_id: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    user: Mapped[User] = relationship(back_populates="sessions", lazy="selectin")


class ExternalIdentity(Base):
    __tablename__ = "external_identities"
    __table_args__ = (
        UniqueConstraint("provider", "provider_subject", name="uq_external_identity_provider_subject"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    provider: Mapped[str] = mapped_column(String(40), nullable=False)
    provider_subject: Mapped[str] = mapped_column(String(160), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
```

- [ ] **Step 5: Create Alembic configuration and migration**

Create `backend/alembic.ini`:

```ini
[alembic]
script_location = alembic
prepend_sys_path = .
sqlalchemy.url = sqlite:///./homevault.db

[loggers]
keys = root,sqlalchemy,alembic

[handlers]
keys = console

[formatters]
keys = generic

[logger_root]
level = WARN
handlers = console

[logger_sqlalchemy]
level = WARN
handlers =
qualname = sqlalchemy.engine

[logger_alembic]
level = INFO
handlers =
qualname = alembic

[handler_console]
class = StreamHandler
args = (sys.stderr,)
level = NOTSET
formatter = generic

[formatter_generic]
format = %(levelname)-5.5s [%(name)s] %(message)s
datefmt = %H:%M:%S
```

Create `backend/alembic/env.py`:

```python
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from app.core.config import get_settings
from app.db.base import Base
from app.models import auth

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

config.set_main_option("sqlalchemy.url", get_settings().database_url)
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(url=url, target_metadata=target_metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
```

Create `backend/alembic/versions/20260618_0001_auth_base.py`:

```python
from alembic import op
import sqlalchemy as sa

revision = "20260618_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("username", sa.String(length=80), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("display_name", sa.String(length=120), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_users_id", "users", ["id"])
    op.create_index("ix_users_username", "users", ["username"], unique=True)

    op.create_table(
        "roles",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("code", sa.String(length=80), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("description", sa.String(length=255), nullable=False, server_default=""),
        sa.Column("is_system", sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    op.create_index("ix_roles_id", "roles", ["id"])
    op.create_index("ix_roles_code", "roles", ["code"], unique=True)

    op.create_table(
        "permissions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("code", sa.String(length=120), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("description", sa.String(length=255), nullable=False, server_default=""),
    )
    op.create_index("ix_permissions_id", "permissions", ["id"])
    op.create_index("ix_permissions_code", "permissions", ["code"], unique=True)

    op.create_table(
        "user_roles",
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("role_id", sa.Integer(), sa.ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True),
    )

    op.create_table(
        "role_permissions",
        sa.Column("role_id", sa.Integer(), sa.ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("permission_id", sa.Integer(), sa.ForeignKey("permissions.id", ondelete="CASCADE"), primary_key=True),
    )

    op.create_table(
        "auth_sessions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("session_id", sa.String(length=64), nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_auth_sessions_id", "auth_sessions", ["id"])
    op.create_index("ix_auth_sessions_session_id", "auth_sessions", ["session_id"], unique=True)

    op.create_table(
        "external_identities",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("provider", sa.String(length=40), nullable=False),
        sa.Column("provider_subject", sa.String(length=160), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("provider", "provider_subject", name="uq_external_identity_provider_subject"),
    )
    op.create_index("ix_external_identities_id", "external_identities", ["id"])


def downgrade() -> None:
    op.drop_index("ix_external_identities_id", table_name="external_identities")
    op.drop_table("external_identities")
    op.drop_index("ix_auth_sessions_session_id", table_name="auth_sessions")
    op.drop_index("ix_auth_sessions_id", table_name="auth_sessions")
    op.drop_table("auth_sessions")
    op.drop_table("role_permissions")
    op.drop_table("user_roles")
    op.drop_index("ix_permissions_code", table_name="permissions")
    op.drop_index("ix_permissions_id", table_name="permissions")
    op.drop_table("permissions")
    op.drop_index("ix_roles_code", table_name="roles")
    op.drop_index("ix_roles_id", table_name="roles")
    op.drop_table("roles")
    op.drop_index("ix_users_username", table_name="users")
    op.drop_index("ix_users_id", table_name="users")
    op.drop_table("users")
```

- [ ] **Step 6: Run the database model test and migration**

Run:

```powershell
Set-Location backend
python -m pytest tests/test_database_models.py -v
python -m alembic upgrade head
```

Expected: PASS for the model test, and Alembic creates the auth base schema.

- [ ] **Step 7: Commit Task 2**

Run:

```powershell
git add backend
git commit -m "feat: add auth database model"
```

## Task 3: Password Hashing And Token Security

**Files:**
- Create: `backend/app/core/security.py`
- Create: `backend/app/services/__init__.py`
- Create: `backend/app/services/seed.py`
- Create: `backend/tests/test_security.py`
- Create: `backend/tests/test_seed.py`

- [ ] **Step 1: Write security tests**

Create `backend/tests/test_security.py`:

```python
from datetime import datetime, timezone

import pytest

from app.core.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)


def test_password_hash_verifies_plain_password() -> None:
    password_hash = hash_password("ChangeMe123!")

    assert password_hash != "ChangeMe123!"
    assert verify_password("ChangeMe123!", password_hash) is True
    assert verify_password("wrong-password", password_hash) is False


def test_access_token_round_trip() -> None:
    token = create_access_token(
        user_id=7,
        session_id="session-123",
        secret_key="unit-test-secret",
        minutes=30,
    )

    payload = decode_access_token(token, secret_key="unit-test-secret")

    assert payload.user_id == 7
    assert payload.session_id == "session-123"
    assert payload.expires_at > datetime.now(timezone.utc)


def test_access_token_rejects_wrong_secret() -> None:
    token = create_access_token(
        user_id=7,
        session_id="session-123",
        secret_key="unit-test-secret",
        minutes=30,
    )

    with pytest.raises(ValueError, match="登录状态无效"):
        decode_access_token(token, secret_key="different-secret")
```

- [ ] **Step 2: Run the security tests and confirm they fail**

Run:

```powershell
Set-Location backend
python -m pytest tests/test_security.py -v
```

Expected: FAIL because `app.core.security` does not exist.

- [ ] **Step 3: Implement security helpers**

Create `backend/app/core/security.py`:

```python
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

import jwt
from pwdlib import PasswordHash

ALGORITHM = "HS256"
password_hasher = PasswordHash.recommended()


@dataclass(frozen=True)
class AccessTokenPayload:
    user_id: int
    session_id: str
    expires_at: datetime


def hash_password(password: str) -> str:
    return password_hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return password_hasher.verify(password, password_hash)


def create_access_token(user_id: int, session_id: str, secret_key: str, minutes: int) -> str:
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=minutes)
    payload = {
        "sub": str(user_id),
        "sid": session_id,
        "exp": expires_at,
    }
    return jwt.encode(payload, secret_key, algorithm=ALGORITHM)


def decode_access_token(token: str, secret_key: str) -> AccessTokenPayload:
    try:
        payload = jwt.decode(token, secret_key, algorithms=[ALGORITHM])
        user_id = int(payload["sub"])
        session_id = str(payload["sid"])
        expires_at = datetime.fromtimestamp(int(payload["exp"]), tz=timezone.utc)
    except Exception as exc:
        raise ValueError("登录状态无效，请重新登录") from exc
    return AccessTokenPayload(user_id=user_id, session_id=session_id, expires_at=expires_at)
```

- [ ] **Step 4: Run security and seed tests**

Run:

```powershell
Set-Location backend
python -m pytest tests/test_security.py -v
```

Expected: PASS.

- [ ] **Step 5: Write seed test**

Create `backend/tests/test_seed.py`:

```python
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.auth import Permission, Role, User
from app.services.seed import seed_auth_baseline


def test_seed_auth_baseline_creates_admin_user(db_session: Session) -> None:
    admin = seed_auth_baseline(
        db_session,
        admin_username="admin",
        admin_password="ChangeMe123!",
    )

    roles = db_session.scalars(select(Role)).all()
    permissions = db_session.scalars(select(Permission)).all()
    users = db_session.scalars(select(User)).all()

    assert admin.username == "admin"
    assert admin.is_active is True
    assert {role.code for role in roles} == {"admin", "editor", "viewer"}
    assert "items:view" in {permission.code for permission in permissions}
    assert users == [admin]
    assert {role.code for role in admin.roles} == {"admin"}
```

- [ ] **Step 6: Run seed test and confirm it fails**

Run:

```powershell
Set-Location backend
python -m pytest tests/test_seed.py -v
```

Expected: FAIL because `app.services.seed` does not exist.

- [ ] **Step 7: Create seed service**

Create `backend/app/services/__init__.py`:

```python
"""Business services."""
```

Create `backend/app/services/seed.py`:

```python
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models.auth import Permission, Role, User

PERMISSIONS = [
    ("items:view", "查看物品", "查看物品列表和详情"),
    ("items:create", "新增物品", "创建新的物品记录"),
    ("items:edit", "编辑物品", "修改物品、位置、状态和数量"),
    ("items:archive", "归档物品", "软删除或归档物品"),
    ("config:manage", "管理配置", "管理住宅、位置、分类、字段和字典"),
    ("users:manage", "管理用户", "管理账号、角色和家庭成员"),
    ("logs:view", "查看日志", "查看全局操作日志"),
]

ROLE_PERMISSIONS = {
    "admin": [code for code, _name, _description in PERMISSIONS],
    "editor": ["items:view", "items:create", "items:edit"],
    "viewer": ["items:view"],
}

ROLES = [
    ("admin", "管理员", "拥有全部管理权限"),
    ("editor", "编辑者", "可维护物品但不能管理系统配置"),
    ("viewer", "查看者", "只能查看和搜索物品"),
]


def seed_auth_baseline(db: Session, admin_username: str, admin_password: str) -> User:
    permissions_by_code: dict[str, Permission] = {}
    for code, name, description in PERMISSIONS:
        permission = db.scalar(select(Permission).where(Permission.code == code))
        if permission is None:
            permission = Permission(code=code, name=name, description=description)
            db.add(permission)
        permissions_by_code[code] = permission

    roles_by_code: dict[str, Role] = {}
    for code, name, description in ROLES:
        role = db.scalar(select(Role).where(Role.code == code))
        if role is None:
            role = Role(code=code, name=name, description=description, is_system=True)
            db.add(role)
        role.permissions = [permissions_by_code[item] for item in ROLE_PERMISSIONS[code]]
        roles_by_code[code] = role

    admin = db.scalar(select(User).where(User.username == admin_username))
    if admin is None:
        admin = User(
            username=admin_username,
            password_hash=hash_password(admin_password),
            display_name="管理员",
            is_active=True,
        )
        db.add(admin)
    admin.roles = [roles_by_code["admin"]]
    db.commit()
    db.refresh(admin)
    return admin
```

- [ ] **Step 8: Run security and seed tests**

Run:

```powershell
Set-Location backend
python -m pytest tests/test_security.py tests/test_seed.py -v
```

Expected: PASS.

- [ ] **Step 9: Commit Task 3**

Run:

```powershell
git add backend
git commit -m "feat: add password and token security"
```

## Task 4: Auth API, Current User, Logout, And RBAC Dependency

**Files:**
- Create: `backend/app/core/errors.py`
- Create: `backend/app/schemas/__init__.py`
- Create: `backend/app/schemas/auth.py`
- Create: `backend/app/schemas/user.py`
- Create: `backend/app/services/auth.py`
- Create: `backend/app/api/deps.py`
- Create: `backend/app/api/routes/auth.py`
- Modify: `backend/app/api/router.py`
- Create: `backend/tests/test_auth_api.py`

- [ ] **Step 1: Write auth API tests**

Create `backend/tests/test_auth_api.py`:

```python
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.db.base import Base
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


def test_login_returns_token_and_user(client: TestClient) -> None:
    response = client.post(
        "/api/auth/login",
        json={"username": "admin", "password": "ChangeMe123!"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"]
    assert body["user"]["username"] == "admin"
    assert body["user"]["roles"] == ["admin"]
    assert "users:manage" in body["user"]["permissions"]


def test_login_failure_returns_chinese_message(client: TestClient) -> None:
    response = client.post(
        "/api/auth/login",
        json={"username": "admin", "password": "wrong"},
    )

    assert response.status_code == 401
    assert response.json()["message"] == "账号或密码不正确"


def test_me_requires_token(client: TestClient) -> None:
    response = client.get("/api/auth/me")

    assert response.status_code == 401
    assert response.json()["message"] == "请先登录"


def test_me_returns_current_user(client: TestClient) -> None:
    login = client.post(
        "/api/auth/login",
        json={"username": "admin", "password": "ChangeMe123!"},
    )
    token = login.json()["access_token"]

    response = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200
    assert response.json()["username"] == "admin"


def test_logout_revokes_session(client: TestClient) -> None:
    login = client.post(
        "/api/auth/login",
        json={"username": "admin", "password": "ChangeMe123!"},
    )
    token = login.json()["access_token"]

    logout = client.post("/api/auth/logout", headers={"Authorization": f"Bearer {token}"})
    after_logout = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})

    assert logout.status_code == 204
    assert after_logout.status_code == 401
    assert after_logout.json()["message"] == "登录状态已失效，请重新登录"
```

- [ ] **Step 2: Run auth API tests and confirm they fail**

Run:

```powershell
Set-Location backend
python -m pytest tests/test_auth_api.py -v
```

Expected: FAIL because auth routes and dependencies do not exist.

- [ ] **Step 3: Add structured Chinese errors**

Create `backend/app/core/errors.py`:

```python
from fastapi import HTTPException, status


def unauthorized(message: str = "请先登录") -> HTTPException:
    return HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail={"message": message})


def forbidden(message: str = "你没有权限执行此操作") -> HTTPException:
    return HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail={"message": message})


def bad_request(message: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail={"message": message})
```

- [ ] **Step 4: Normalize FastAPI error output**

Modify `backend/app/main.py`:

```python
from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.api.router import api_router
from app.core.config import get_settings


def create_app() -> FastAPI:
    settings = get_settings()
    application = FastAPI(title=settings.app_name, version="0.1.0")
    application.include_router(api_router, prefix="/api")

    @application.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
        detail = exc.detail
        if isinstance(detail, dict) and isinstance(detail.get("message"), str):
            message = detail["message"]
        elif isinstance(detail, str):
            message = detail
        else:
            message = "请求无法处理"
        return JSONResponse(status_code=exc.status_code, content={"message": message})

    @application.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request,
        exc: RequestValidationError,
    ) -> JSONResponse:
        return JSONResponse(status_code=422, content={"message": "提交内容不完整或格式不正确"})

    @application.exception_handler(Exception)
    async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        return JSONResponse(status_code=500, content={"message": "系统暂时无法处理，请稍后重试"})

    return application


app = create_app()
```

- [ ] **Step 5: Add schemas**

Create `backend/app/schemas/__init__.py`:

```python
"""Pydantic schemas."""
```

Create `backend/app/schemas/user.py`:

```python
from pydantic import BaseModel


class CurrentUserResponse(BaseModel):
    id: int
    username: str
    display_name: str
    roles: list[str]
    permissions: list[str]
```

Create `backend/app/schemas/auth.py`:

```python
from pydantic import BaseModel, Field

from app.schemas.user import CurrentUserResponse


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=80)
    password: str = Field(min_length=1, max_length=200)


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: CurrentUserResponse
```

- [ ] **Step 6: Add auth service**

Create `backend/app/services/auth.py`:

```python
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.config import get_settings
from app.core.security import create_access_token, verify_password
from app.models.auth import AuthSession, Role, User
from app.schemas.user import CurrentUserResponse


def serialize_current_user(user: User) -> CurrentUserResponse:
    permissions = sorted(
        {
            permission.code
            for role in user.roles
            for permission in role.permissions
        }
    )
    roles = sorted({role.code for role in user.roles})
    return CurrentUserResponse(
        id=user.id,
        username=user.username,
        display_name=user.display_name,
        roles=roles,
        permissions=permissions,
    )


def get_user_by_username(db: Session, username: str) -> User | None:
    return db.scalar(
        select(User)
        .where(User.username == username)
        .options(selectinload(User.roles).selectinload(Role.permissions))
    )


def authenticate_user(db: Session, username: str, password: str) -> User | None:
    user = get_user_by_username(db, username)
    if user is None or not user.is_active:
        return None
    if not verify_password(password, user.password_hash):
        return None
    return user


def create_login_session(db: Session, user: User) -> tuple[str, AuthSession]:
    settings = get_settings()
    session = AuthSession(
        session_id=uuid4().hex,
        user_id=user.id,
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=settings.access_token_minutes),
        is_active=True,
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    token = create_access_token(
        user_id=user.id,
        session_id=session.session_id,
        secret_key=settings.secret_key,
        minutes=settings.access_token_minutes,
    )
    return token, session


def revoke_session(db: Session, session: AuthSession) -> None:
    session.is_active = False
    session.revoked_at = datetime.now(timezone.utc)
    db.commit()
```

- [ ] **Step 7: Add API dependencies and RBAC helper**

Create `backend/app/api/deps.py`:

```python
from collections.abc import Iterator
from datetime import datetime, timezone

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.config import get_settings
from app.core.errors import forbidden, unauthorized
from app.core.security import decode_access_token
from app.db.session import get_db as session_get_db
from app.models.auth import AuthSession, Role, User

bearer_scheme = HTTPBearer(auto_error=False)


def get_db() -> Iterator[Session]:
    yield from session_get_db()


def get_current_user_and_session(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> tuple[User, AuthSession]:
    if credentials is None:
        raise unauthorized()
    try:
        payload = decode_access_token(credentials.credentials, get_settings().secret_key)
    except ValueError as exc:
        raise unauthorized(str(exc)) from exc

    session = db.scalar(
        select(AuthSession)
        .where(AuthSession.session_id == payload.session_id)
        .options(selectinload(AuthSession.user).selectinload(User.roles).selectinload(Role.permissions))
    )
    now = datetime.now(timezone.utc)
    if session is None or not session.is_active:
        raise unauthorized("登录状态已失效，请重新登录")
    expires_at = session.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at <= now:
        raise unauthorized("登录状态已失效，请重新登录")
    if session.user_id != payload.user_id or not session.user.is_active:
        raise unauthorized("登录状态已失效，请重新登录")
    return session.user, session


def get_current_user(
    user_and_session: tuple[User, AuthSession] = Depends(get_current_user_and_session),
) -> User:
    user, _session = user_and_session
    return user


def require_permission(permission_code: str):
    def dependency(user: User = Depends(get_current_user)) -> User:
        user_permissions = {
            permission.code
            for role in user.roles
            for permission in role.permissions
        }
        if permission_code not in user_permissions:
            raise forbidden()
        return user

    return dependency
```

- [ ] **Step 8: Add auth routes**

Create `backend/app/api/routes/auth.py`:

```python
from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_current_user_and_session, get_db
from app.core.errors import unauthorized
from app.models.auth import AuthSession, User
from app.schemas.auth import LoginRequest, LoginResponse
from app.schemas.user import CurrentUserResponse
from app.services.auth import (
    authenticate_user,
    create_login_session,
    revoke_session,
    serialize_current_user,
)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=LoginResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> LoginResponse:
    user = authenticate_user(db, payload.username, payload.password)
    if user is None:
        raise unauthorized("账号或密码不正确")
    access_token, _session = create_login_session(db, user)
    return LoginResponse(access_token=access_token, user=serialize_current_user(user))


@router.get("/me", response_model=CurrentUserResponse)
def me(user: User = Depends(get_current_user)) -> CurrentUserResponse:
    return serialize_current_user(user)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    response: Response,
    user_and_session: tuple[User, AuthSession] = Depends(get_current_user_and_session),
    db: Session = Depends(get_db),
) -> Response:
    _user, session = user_and_session
    revoke_session(db, session)
    return response
```

Modify `backend/app/api/router.py`:

```python
from fastapi import APIRouter

from app.api.routes import auth, health

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(auth.router)
```

- [ ] **Step 9: Run backend test suite**

Run:

```powershell
Set-Location backend
python -m pytest -v
```

Expected: PASS for health, security, seed, and auth API tests.

- [ ] **Step 10: Commit Task 4**

Run:

```powershell
git add backend
git commit -m "feat: add token auth api"
```

## Task 5: Frontend Scaffold, Theme, And API Client

**Files:**
- Create: `frontend/package.json`
- Create: `frontend/index.html`
- Create: `frontend/tsconfig.json`
- Create: `frontend/tsconfig.node.json`
- Create: `frontend/vite.config.ts`
- Create: `frontend/src/main.ts`
- Create: `frontend/src/App.vue`
- Create: `frontend/src/styles/theme.css`
- Create: `frontend/src/api/client.ts`

- [ ] **Step 1: Create frontend package manifest**

Create `frontend/package.json`:

```json
{
  "name": "homevault-frontend",
  "version": "0.1.0",
  "private": true,
  "type": "module",
  "scripts": {
    "dev": "vite --host 127.0.0.1",
    "build": "vue-tsc --noEmit && vite build",
    "preview": "vite preview --host 127.0.0.1"
  },
  "dependencies": {
    "@element-plus/icons-vue": "^2.3.1",
    "axios": "^1.7.0",
    "element-plus": "^2.8.0",
    "pinia": "^2.2.0",
    "vue": "^3.5.0",
    "vue-router": "^4.4.0"
  },
  "devDependencies": {
    "@vitejs/plugin-vue": "^5.1.0",
    "typescript": "^5.5.0",
    "vite": "^5.4.0",
    "vue-tsc": "^2.1.0"
  }
}
```

- [ ] **Step 2: Create Vite and TypeScript config**

Create `frontend/index.html`:

```html
<!doctype html>
<html lang="zh-CN">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>HomeVault</title>
  </head>
  <body>
    <div id="app"></div>
    <script type="module" src="/src/main.ts"></script>
  </body>
</html>
```

Create `frontend/tsconfig.json`:

```json
{
  "compilerOptions": {
    "target": "ES2020",
    "useDefineForClassFields": true,
    "module": "ESNext",
    "lib": ["ES2020", "DOM", "DOM.Iterable"],
    "skipLibCheck": true,
    "moduleResolution": "Bundler",
    "allowImportingTsExtensions": true,
    "resolveJsonModule": true,
    "isolatedModules": true,
    "noEmit": true,
    "jsx": "preserve",
    "strict": true
  },
  "include": ["src/**/*.ts", "src/**/*.vue"],
  "references": [{ "path": "./tsconfig.node.json" }]
}
```

Create `frontend/tsconfig.node.json`:

```json
{
  "compilerOptions": {
    "composite": true,
    "skipLibCheck": true,
    "module": "ESNext",
    "moduleResolution": "Bundler",
    "allowSyntheticDefaultImports": true
  },
  "include": ["vite.config.ts"]
}
```

Create `frontend/vite.config.ts`:

```ts
import vue from '@vitejs/plugin-vue'
import { defineConfig } from 'vite'

export default defineConfig({
  plugins: [vue()],
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true
      }
    }
  }
})
```

- [ ] **Step 3: Create warm visual theme**

Create `frontend/src/styles/theme.css`:

```css
:root {
  font-family: Inter, "Microsoft YaHei", "PingFang SC", system-ui, sans-serif;
  color: #29342f;
  background: #f8f3ea;
}

* {
  box-sizing: border-box;
}

body {
  margin: 0;
  min-width: 1080px;
  min-height: 100vh;
  background:
    linear-gradient(180deg, rgba(255, 255, 255, 0.8), rgba(248, 243, 234, 0.95)),
    #f8f3ea;
}

.page-title {
  margin: 0;
  color: #25342d;
  font-size: 24px;
  font-weight: 700;
}

.page-subtitle {
  margin: 8px 0 0;
  color: #6c756f;
  font-size: 14px;
}
```

- [ ] **Step 4: Create API client with Chinese error extraction**

Create `frontend/src/api/client.ts`:

```ts
import axios, { AxiosError } from 'axios'

export const apiClient = axios.create({
  baseURL: '/api',
  timeout: 10000
})

export function setAccessToken(token: string | null) {
  if (token) {
    apiClient.defaults.headers.common.Authorization = `Bearer ${token}`
  } else {
    delete apiClient.defaults.headers.common.Authorization
  }
}

export function getChineseErrorMessage(error: unknown): string {
  if (error instanceof AxiosError) {
    const data = error.response?.data as { message?: string; detail?: { message?: string } } | undefined
    return data?.message || data?.detail?.message || '操作失败，请稍后重试'
  }
  return '操作失败，请稍后重试'
}
```

- [ ] **Step 5: Create Vue entry**

Create `frontend/src/App.vue`:

```vue
<template>
  <RouterView />
</template>
```

Create `frontend/src/main.ts`:

```ts
import 'element-plus/dist/index.css'
import './styles/theme.css'

import ElementPlus from 'element-plus'
import { createPinia } from 'pinia'
import { createApp } from 'vue'

import App from './App.vue'
import { router } from './router'

createApp(App).use(createPinia()).use(router).use(ElementPlus).mount('#app')
```

- [ ] **Step 6: Run frontend build and confirm the expected failure**

Run:

```powershell
Set-Location frontend
npm install
npm run build
```

Expected: FAIL because `src/router` does not exist. This failure becomes the starting point for Task 6.

- [ ] **Step 7: Commit Task 5**

Run:

```powershell
git add frontend
git commit -m "feat: scaffold frontend shell"
```

## Task 6: Frontend Login, Auth Store, Route Guards, And Dashboard Shell

**Files:**
- Create: `frontend/src/api/auth.ts`
- Create: `frontend/src/stores/auth.ts`
- Create: `frontend/src/router/index.ts`
- Create: `frontend/src/layouts/AppLayout.vue`
- Create: `frontend/src/pages/LoginPage.vue`
- Create: `frontend/src/pages/DashboardPage.vue`
- Create: `frontend/src/pages/ForbiddenPage.vue`
- Create: `frontend/src/pages/NotFoundPage.vue`
- Create: `frontend/src/components/PermissionGate.vue`

- [ ] **Step 1: Create auth API module**

Create `frontend/src/api/auth.ts`:

```ts
import { apiClient } from './client'

export interface CurrentUser {
  id: number
  username: string
  display_name: string
  roles: string[]
  permissions: string[]
}

export interface LoginResponse {
  access_token: string
  token_type: 'bearer'
  user: CurrentUser
}

export async function loginApi(username: string, password: string): Promise<LoginResponse> {
  const response = await apiClient.post<LoginResponse>('/auth/login', { username, password })
  return response.data
}

export async function fetchCurrentUserApi(): Promise<CurrentUser> {
  const response = await apiClient.get<CurrentUser>('/auth/me')
  return response.data
}

export async function logoutApi(): Promise<void> {
  await apiClient.post('/auth/logout')
}
```

- [ ] **Step 2: Create auth store**

Create `frontend/src/stores/auth.ts`:

```ts
import { defineStore } from 'pinia'

import { fetchCurrentUserApi, loginApi, logoutApi, type CurrentUser } from '../api/auth'
import { setAccessToken } from '../api/client'

const TOKEN_KEY = 'homevault_access_token'

interface AuthState {
  token: string | null
  user: CurrentUser | null
  initialized: boolean
}

export const useAuthStore = defineStore('auth', {
  state: (): AuthState => ({
    token: sessionStorage.getItem(TOKEN_KEY),
    user: null,
    initialized: false
  }),
  getters: {
    isAuthenticated: (state) => Boolean(state.token && state.user),
    permissions: (state) => new Set(state.user?.permissions ?? []),
    hasPermission: (state) => {
      const permissions = new Set(state.user?.permissions ?? [])
      return (permission: string) => permissions.has(permission)
    }
  },
  actions: {
    async initialize() {
      if (this.initialized) return
      if (!this.token) {
        this.initialized = true
        return
      }
      setAccessToken(this.token)
      try {
        this.user = await fetchCurrentUserApi()
      } catch {
        this.clearSession()
      } finally {
        this.initialized = true
      }
    },
    async login(username: string, password: string) {
      const result = await loginApi(username, password)
      this.token = result.access_token
      this.user = result.user
      sessionStorage.setItem(TOKEN_KEY, result.access_token)
      setAccessToken(result.access_token)
    },
    async logout() {
      try {
        if (this.token) await logoutApi()
      } finally {
        this.clearSession()
      }
    },
    clearSession() {
      this.token = null
      this.user = null
      sessionStorage.removeItem(TOKEN_KEY)
      setAccessToken(null)
    }
  }
})
```

- [ ] **Step 3: Create router with permission guard**

Create `frontend/src/router/index.ts`:

```ts
import { createRouter, createWebHistory, type RouteRecordRaw } from 'vue-router'

import { useAuthStore } from '../stores/auth'

const routes: RouteRecordRaw[] = [
  { path: '/login', name: 'login', component: () => import('../pages/LoginPage.vue') },
  {
    path: '/',
    component: () => import('../layouts/AppLayout.vue'),
    meta: { requiresAuth: true },
    children: [
      { path: '', name: 'dashboard', component: () => import('../pages/DashboardPage.vue') },
      {
        path: 'admin',
        name: 'admin-placeholder',
        component: () => import('../pages/ForbiddenPage.vue'),
        meta: { permission: 'users:manage' }
      }
    ]
  },
  { path: '/403', name: 'forbidden', component: () => import('../pages/ForbiddenPage.vue') },
  { path: '/:pathMatch(.*)*', name: 'not-found', component: () => import('../pages/NotFoundPage.vue') }
]

export const router = createRouter({
  history: createWebHistory(),
  routes
})

router.beforeEach(async (to) => {
  const auth = useAuthStore()
  await auth.initialize()

  if (to.meta.requiresAuth && !auth.isAuthenticated) {
    return { name: 'login', query: { redirect: to.fullPath } }
  }
  if (to.name === 'login' && auth.isAuthenticated) {
    return { name: 'dashboard' }
  }
  const permission = to.meta.permission
  if (typeof permission === 'string' && !auth.hasPermission(permission)) {
    return { name: 'forbidden' }
  }
  return true
})
```

- [ ] **Step 4: Create permission gate component**

Create `frontend/src/components/PermissionGate.vue`:

```vue
<script setup lang="ts">
import { useAuthStore } from '../stores/auth'

const props = defineProps<{ permission: string }>()
const auth = useAuthStore()
</script>

<template>
  <slot v-if="auth.hasPermission(props.permission)" />
</template>
```

- [ ] **Step 5: Create app layout with role-aware menu**

Create `frontend/src/layouts/AppLayout.vue`:

```vue
<script setup lang="ts">
import { Box, House, LogOut, Setting, User } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { useRouter } from 'vue-router'

import PermissionGate from '../components/PermissionGate.vue'
import { getChineseErrorMessage } from '../api/client'
import { useAuthStore } from '../stores/auth'

const auth = useAuthStore()
const router = useRouter()

async function handleLogout() {
  try {
    await auth.logout()
    ElMessage.success('已退出登录')
    await router.push({ name: 'login' })
  } catch (error) {
    ElMessage.error(getChineseErrorMessage(error))
  }
}
</script>

<template>
  <el-container class="app-shell">
    <el-aside width="248px" class="side-nav">
      <div class="brand">
        <div class="brand-mark">
          <el-icon><House /></el-icon>
        </div>
        <div>
          <strong>HomeVault</strong>
          <span>家庭物品记录</span>
        </div>
      </div>

      <el-menu router default-active="/" class="nav-menu">
        <el-menu-item index="/">
          <el-icon><Box /></el-icon>
          <span>仪表盘</span>
        </el-menu-item>
        <PermissionGate permission="items:view">
          <el-menu-item index="/">
            <el-icon><House /></el-icon>
            <span>物品</span>
          </el-menu-item>
        </PermissionGate>
        <PermissionGate permission="users:manage">
          <el-menu-item index="/admin">
            <el-icon><Setting /></el-icon>
            <span>后台管理</span>
          </el-menu-item>
        </PermissionGate>
      </el-menu>
    </el-aside>

    <el-container>
      <el-header class="top-bar">
        <div>
          <div class="welcome">欢迎回来，{{ auth.user?.display_name }}</div>
          <div class="role-line">{{ auth.user?.roles.join(' / ') }}</div>
        </div>
        <el-button :icon="LogOut" @click="handleLogout">退出</el-button>
      </el-header>
      <el-main class="main-content">
        <RouterView />
      </el-main>
    </el-container>
  </el-container>
</template>

<style scoped>
.app-shell {
  min-height: 100vh;
}

.side-nav {
  background: #fffaf1;
  border-right: 1px solid #eadfce;
}

.brand {
  display: flex;
  gap: 12px;
  align-items: center;
  padding: 22px 20px;
}

.brand-mark {
  display: grid;
  width: 42px;
  height: 42px;
  place-items: center;
  color: #fff;
  background: #4f8f72;
  border-radius: 8px;
}

.brand span {
  display: block;
  margin-top: 3px;
  color: #768078;
  font-size: 12px;
}

.nav-menu {
  border-right: none;
  background: transparent;
}

.top-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: rgba(255, 255, 255, 0.76);
  border-bottom: 1px solid #eadfce;
}

.welcome {
  font-weight: 700;
}

.role-line {
  margin-top: 4px;
  color: #7d867f;
  font-size: 12px;
}

.main-content {
  padding: 28px;
}
</style>
```

- [ ] **Step 6: Create pages**

Create `frontend/src/pages/LoginPage.vue`:

```vue
<script setup lang="ts">
import { Lock, User } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { getChineseErrorMessage } from '../api/client'
import { useAuthStore } from '../stores/auth'

const auth = useAuthStore()
const route = useRoute()
const router = useRouter()
const loading = ref(false)
const form = reactive({ username: 'admin', password: 'ChangeMe123!' })

async function submit() {
  loading.value = true
  try {
    await auth.login(form.username, form.password)
    ElMessage.success('登录成功')
    await router.push((route.query.redirect as string) || '/')
  } catch (error) {
    ElMessage.error(getChineseErrorMessage(error))
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <main class="login-page">
    <section class="login-panel">
      <div class="login-copy">
        <p class="eyebrow">HomeVault</p>
        <h1>把家里的东西安稳地记下来</h1>
        <p>登录后可以查看家庭物品、位置、角色权限和后续管理功能。</p>
      </div>
      <el-form class="login-form" @submit.prevent="submit">
        <el-form-item>
          <el-input v-model="form.username" :prefix-icon="User" size="large" placeholder="账号" />
        </el-form-item>
        <el-form-item>
          <el-input
            v-model="form.password"
            :prefix-icon="Lock"
            size="large"
            type="password"
            placeholder="密码"
            show-password
            @keyup.enter="submit"
          />
        </el-form-item>
        <el-button type="primary" size="large" class="login-button" :loading="loading" @click="submit">
          登录
        </el-button>
      </el-form>
    </section>
  </main>
</template>

<style scoped>
.login-page {
  display: grid;
  min-height: 100vh;
  place-items: center;
  padding: 48px;
}

.login-panel {
  display: grid;
  grid-template-columns: 1.05fr 360px;
  gap: 40px;
  width: min(900px, 100%);
  padding: 44px;
  background: rgba(255, 255, 255, 0.84);
  border: 1px solid #eadfce;
  border-radius: 8px;
  box-shadow: 0 18px 50px rgba(84, 68, 45, 0.12);
}

.eyebrow {
  margin: 0 0 12px;
  color: #4f8f72;
  font-weight: 700;
}

h1 {
  margin: 0;
  color: #26342e;
  font-size: 34px;
  line-height: 1.2;
}

.login-copy p:last-child {
  color: #6f796f;
  line-height: 1.7;
}

.login-form {
  align-self: center;
}

.login-button {
  width: 100%;
}
</style>
```

Create `frontend/src/pages/DashboardPage.vue`:

```vue
<script setup lang="ts">
import { Bell, Box, Key, UserFilled } from '@element-plus/icons-vue'
</script>

<template>
  <section>
    <h1 class="page-title">仪表盘</h1>
    <p class="page-subtitle">第一阶段先确认登录、权限和基础布局，物品统计会在库存模块接入后显示真实数据。</p>

    <div class="summary-grid">
      <el-card shadow="never">
        <el-icon><Box /></el-icon>
        <strong>物品基础</strong>
        <span>准备接入住宅、位置和物品卡片</span>
      </el-card>
      <el-card shadow="never">
        <el-icon><UserFilled /></el-icon>
        <strong>角色权限</strong>
        <span>管理员、编辑者、查看者已预留</span>
      </el-card>
      <el-card shadow="never">
        <el-icon><Bell /></el-icon>
        <strong>站内提醒</strong>
        <span>后续展示保修、有效期和检查提醒</span>
      </el-card>
      <el-card shadow="never">
        <el-icon><Key /></el-icon>
        <strong>安全登录</strong>
        <span>token 登录和退出已接入</span>
      </el-card>
    </div>
  </section>
</template>

<style scoped>
.summary-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 16px;
  margin-top: 24px;
}

.summary-grid :deep(.el-card__body) {
  display: grid;
  gap: 10px;
  min-height: 150px;
}

.summary-grid .el-icon {
  color: #4f8f72;
  font-size: 28px;
}

.summary-grid strong {
  color: #26342e;
}

.summary-grid span {
  color: #748078;
  line-height: 1.6;
}
</style>
```

Create `frontend/src/pages/ForbiddenPage.vue`:

```vue
<template>
  <section>
    <h1 class="page-title">没有权限</h1>
    <p class="page-subtitle">你没有权限查看这个页面，请联系管理员调整角色。</p>
  </section>
</template>
```

Create `frontend/src/pages/NotFoundPage.vue`:

```vue
<template>
  <section>
    <h1 class="page-title">页面不存在</h1>
    <p class="page-subtitle">请从左侧导航重新选择要访问的功能。</p>
  </section>
</template>
```

- [ ] **Step 7: Build frontend**

Run:

```powershell
Set-Location frontend
npm run build
```

Expected: PASS.

- [ ] **Step 8: Commit Task 6**

Run:

```powershell
git add frontend
git commit -m "feat: add frontend auth shell"
```

## Task 7: Local Run Scripts And Manual Seed Command

**Files:**
- Create: `backend/app/cli.py`
- Modify: `backend/pyproject.toml`
- Create: `README.md`

- [ ] **Step 1: Add CLI entry for seeding**

Create `backend/app/cli.py`:

```python
from app.core.config import get_settings
from app.db.session import SessionLocal
from app.services.seed import seed_auth_baseline


def main() -> None:
    settings = get_settings()
    db = SessionLocal()
    try:
        admin = seed_auth_baseline(
            db,
            admin_username=settings.admin_username,
            admin_password=settings.admin_password,
        )
        print(f"管理员账号已就绪: {admin.username}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Add console script**

Modify `backend/pyproject.toml` by adding this block after `[project.optional-dependencies]`:

```toml
[project.scripts]
homevault-seed = "app.cli:main"
```

- [ ] **Step 3: Create README run instructions**

Create `README.md`:

````markdown
# HomeVault

HomeVault 是一个家庭物品管理系统。第一阶段包含 FastAPI 后端、SQLite 数据库迁移、token 登录、RBAC 基础角色，以及 Vue/Element Plus 登录和仪表盘骨架。

## 后端启动

```powershell
Set-Location backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
python -m alembic upgrade head
python -m app.cli
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

默认管理员账号来自 `backend/.env.example`：

- 账号：`admin`
- 密码：`ChangeMe123!`

## 前端启动

```powershell
Set-Location frontend
npm install
npm run dev
```

打开 `http://127.0.0.1:5173`。

## 测试

```powershell
Set-Location backend
python -m pytest -v

Set-Location ..\frontend
npm run build
```
````

- [ ] **Step 4: Verify backend migration and seed on a real SQLite file**

Run:

```powershell
Set-Location backend
python -m pip install -e ".[dev]"
python -m alembic upgrade head
python -m app.cli
```

Expected:

```text
管理员账号已就绪: admin
```

- [ ] **Step 5: Commit Task 7**

Run:

```powershell
git add README.md backend
git commit -m "feat: add local run instructions"
```

## Task 8: Phase 1 Verification

**Files:**
- No source files should change in this task.
- Use: `output/playwright/`

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

- [ ] **Step 3: Start backend server**

Run in one terminal:

```powershell
Set-Location backend
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Expected: server listens on `http://127.0.0.1:8000`.

- [ ] **Step 4: Start frontend server**

Run in a second terminal:

```powershell
Set-Location frontend
npm run dev
```

Expected: Vite serves `http://127.0.0.1:5173`.

- [ ] **Step 5: Run Playwright CLI smoke verification**

Use the Playwright skill wrapper. Before interacting with element refs, take a fresh snapshot and use the refs returned by that snapshot.

Run:

```powershell
$env:CODEX_HOME = "$HOME\.codex"
$env:PWCLI = "$env:CODEX_HOME\skills\playwright\scripts\playwright_cli.sh"
New-Item -ItemType Directory -Force -Path output\playwright
& $env:PWCLI open http://127.0.0.1:5173 --headed
& $env:PWCLI snapshot
```

Then use the returned refs to complete this exact browser flow:

```text
1. Fill the account field with admin.
2. Fill the password field with ChangeMe123!.
3. Click 登录.
4. Snapshot the dashboard.
5. Confirm the page shows 仪表盘.
6. Confirm the side navigation shows 后台管理 for the admin role.
7. Capture a screenshot into output/playwright/phase-1-dashboard.png.
8. Click 退出.
9. Confirm the login page is visible again.
```

Expected: dashboard and logout flow work in a real browser, and the screenshot file is created under `output/playwright/`.

- [ ] **Step 6: Commit verification artifacts only if they are intentionally kept**

If a screenshot is useful to keep:

```powershell
git add output/playwright/phase-1-dashboard.png
git commit -m "test: capture phase 1 browser smoke"
```

If the screenshot is only temporary evidence, leave it untracked and mention it in the completion report.

## Completion Criteria

Phase 1 is complete when:

- `python -m pytest -v` passes in `backend`.
- `npm run build` passes in `frontend`.
- `python -m alembic upgrade head` creates the SQLite schema.
- `python -m app.cli` seeds the default admin.
- The web app opens at `http://127.0.0.1:5173`.
- Admin can log in with `admin / ChangeMe123!`.
- Dashboard shell renders with a warm desktop layout.
- Admin sees the management menu entry.
- Logout invalidates the session and returns to login.
- Frontend error messages are readable Chinese text rather than raw error codes.

## Self-Review Notes

Spec coverage in this phase:

- Covered: API-first foundation, FastAPI backend, SQLite through SQLAlchemy and Alembic, token-based login, role and permission model, seeded administrator, Chinese error messages, Vue 3 and Element Plus shell, role-aware navigation, and Playwright CLI smoke verification.
- Assigned to the core configuration plan: family space, multiple residences, custom location trees, family members, category tree, custom fields, options, and dictionaries.
- Assigned to the item inventory plan: item cards, item detail, images, attachments, tags, ownership, keeper, status changes, containers, movements, quantity history, loan flow, reminders, and global audit log expansion.
- Assigned to the acceptance plan: full browser automation across admin, editor, and viewer workflows after the inventory slice exists.

Plan quality check:

- Placeholder scan found no red-flag placeholders.
- SQLAlchemy relationship loading uses explicit `Role.permissions` paths.
- HTTP errors are normalized to `{ "message": "中文提示" }` for frontend display.
- Phase 1 produces working, testable software without depending on unfinished inventory modules.
