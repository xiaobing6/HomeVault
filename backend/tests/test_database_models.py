from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect
from sqlalchemy.exc import IntegrityError

from app.core.config import get_settings
from app.db.base import Base
from app.models import AuthSession, ExternalIdentity, Permission, Role, User


EXPECTED_AUTH_TABLES = {
    "users",
    "roles",
    "permissions",
    "user_roles",
    "role_permissions",
    "auth_sessions",
    "external_identities",
}


def session_expiry() -> datetime:
    return datetime.now(timezone.utc) + timedelta(hours=1)


def test_auth_tables_are_registered() -> None:
    assert EXPECTED_AUTH_TABLES.issubset(set(Base.metadata.tables))


def test_auth_mappers_can_persist_related_records(db_session) -> None:
    user = User(
        username="alice",
        password_hash="hashed-password",
        display_name="Alice",
    )
    role = Role(code="admin", name="Administrator")
    permission = Permission(code="vault:read", name="Read vault")
    role.permissions.append(permission)
    user.roles.append(role)
    user.sessions.append(AuthSession(session_id="session-alice", expires_at=session_expiry()))
    user.external_identities.append(
        ExternalIdentity(provider="oidc", provider_subject="alice-subject")
    )

    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    assert user.id is not None
    assert user.roles[0].permissions[0].code == "vault:read"
    assert user.sessions[0].user is user
    assert user.external_identities[0].user is user


def test_sqlite_rejects_auth_session_with_invalid_user_id(db_session) -> None:
    db_session.add(
        AuthSession(
            session_id="orphan-session",
            user_id=999,
            expires_at=session_expiry(),
        )
    )

    with pytest.raises(IntegrityError):
        db_session.commit()


def test_deleting_user_deletes_owned_sessions_and_external_identities(db_session) -> None:
    user = User(
        username="delete-me",
        password_hash="hashed-password",
        display_name="Delete Me",
    )
    user.sessions.append(AuthSession(session_id="session-delete-me", expires_at=session_expiry()))
    user.external_identities.append(
        ExternalIdentity(provider="oidc", provider_subject="delete-me-subject")
    )
    db_session.add(user)
    db_session.commit()

    db_session.delete(user)
    db_session.commit()

    assert db_session.query(User).count() == 0
    assert db_session.query(AuthSession).count() == 0
    assert db_session.query(ExternalIdentity).count() == 0


def test_alembic_upgrade_and_downgrade_round_trip_temp_sqlite(monkeypatch, tmp_path: Path) -> None:
    backend_dir = Path(__file__).resolve().parents[1]
    db_path = tmp_path / "homevault_migration_test.db"
    database_url = f"sqlite:///{db_path.resolve().as_posix()}"
    alembic_config = Config(str(backend_dir / "alembic.ini"))
    alembic_config.set_main_option("script_location", str(backend_dir / "alembic"))
    monkeypatch.setenv("HOMEVAULT_DATABASE_URL", database_url)
    get_settings.cache_clear()

    try:
        command.upgrade(alembic_config, "head")
        upgraded_engine = create_engine(database_url)
        try:
            upgraded_tables = set(inspect(upgraded_engine).get_table_names())
        finally:
            upgraded_engine.dispose()
        assert EXPECTED_AUTH_TABLES.issubset(upgraded_tables)

        command.downgrade(alembic_config, "base")
        downgraded_engine = create_engine(database_url)
        try:
            downgraded_tables = set(inspect(downgraded_engine).get_table_names())
        finally:
            downgraded_engine.dispose()
        assert EXPECTED_AUTH_TABLES.isdisjoint(downgraded_tables)
    finally:
        get_settings.cache_clear()
