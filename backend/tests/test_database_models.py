from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory
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

EXPECTED_CONFIGURATION_TABLES = {
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
}


def alembic_config(db_path: str) -> Config:
    backend_dir = Path(__file__).resolve().parents[1]
    database_url = f"sqlite:///{Path(db_path).resolve().as_posix()}"
    config = Config(str(backend_dir / "alembic.ini"))
    config.set_main_option("script_location", str(backend_dir / "alembic"))
    config.set_main_option("sqlalchemy.url", database_url)
    config.attributes["previous_database_url"] = os.environ.get("HOMEVAULT_DATABASE_URL")
    config.attributes["had_previous_database_url"] = "HOMEVAULT_DATABASE_URL" in os.environ
    os.environ["HOMEVAULT_DATABASE_URL"] = database_url
    get_settings.cache_clear()
    return config


def restore_alembic_database_url(config: Config) -> None:
    previous_database_url = config.attributes["previous_database_url"]
    if config.attributes["had_previous_database_url"]:
        os.environ["HOMEVAULT_DATABASE_URL"] = previous_database_url
    else:
        os.environ.pop("HOMEVAULT_DATABASE_URL", None)
    get_settings.cache_clear()


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


def test_configuration_migration_upgrade_and_downgrade_temp_sqlite(monkeypatch, tmp_path: Path) -> None:
    backend_dir = Path(__file__).resolve().parents[1]
    db_path = tmp_path / "homevault_configuration_migration_test.db"
    database_url = f"sqlite:///{db_path.resolve().as_posix()}"
    alembic_config = Config(str(backend_dir / "alembic.ini"))
    alembic_config.set_main_option("script_location", str(backend_dir / "alembic"))
    monkeypatch.setenv("HOMEVAULT_DATABASE_URL", database_url)
    get_settings.cache_clear()

    try:
        command.upgrade(alembic_config, "20260619_0002")
        upgraded_engine = create_engine(database_url)
        try:
            upgraded_tables = set(inspect(upgraded_engine).get_table_names())
        finally:
            upgraded_engine.dispose()
        assert EXPECTED_CONFIGURATION_TABLES.issubset(upgraded_tables)

        command.downgrade(alembic_config, "base")
        downgraded_engine = create_engine(database_url)
        try:
            downgraded_tables = set(inspect(downgraded_engine).get_table_names())
        finally:
            downgraded_engine.dispose()
        assert EXPECTED_CONFIGURATION_TABLES.isdisjoint(downgraded_tables)
    finally:
        get_settings.cache_clear()


def test_inventory_migration_upgrade_and_downgrade_temp_sqlite(tmp_path: Path) -> None:
    db_path = tmp_path / "inventory.sqlite3"
    cfg = alembic_config(str(db_path))

    try:
        command.upgrade(cfg, "head")

        engine = create_engine(f"sqlite:///{db_path}")
        inspector = inspect(engine)
        item_image_indexes = {index["name"] for index in inspector.get_indexes("item_images")}
        item_loan_indexes = {index["name"] for index in inspector.get_indexes("item_loans")}
        assert "items" in inspector.get_table_names()
        assert "item_attribute_values" in inspector.get_table_names()
        assert "item_images" in inspector.get_table_names()
        assert "item_attachments" in inspector.get_table_names()
        assert "tags" in inspector.get_table_names()
        assert "item_tags" in inspector.get_table_names()
        assert "item_movements" in inspector.get_table_names()
        assert "item_quantity_changes" in inspector.get_table_names()
        assert "item_loans" in inspector.get_table_names()
        assert "uq_item_images_active_primary_item_id" in item_image_indexes
        assert "uq_item_loans_active_item_id" in item_loan_indexes

        command.downgrade(cfg, "20260619_0002")
        inspector = inspect(engine)
        assert "items" not in inspector.get_table_names()
    finally:
        restore_alembic_database_url(cfg)


def test_inventory_partial_unique_index_guard_migration_exists(tmp_path: Path) -> None:
    cfg = alembic_config(str(tmp_path / "inventory_guard.sqlite3"))

    try:
        script = ScriptDirectory.from_config(cfg)
        revision = script.get_revision("20260620_0004")

        assert revision is not None
        assert revision.down_revision == "20260619_0003"
    finally:
        restore_alembic_database_url(cfg)


def test_residence_active_unique_index_migration_exists_and_upgrades(tmp_path: Path) -> None:
    db_path = tmp_path / "residence_active_unique.sqlite3"
    cfg = alembic_config(str(db_path))

    try:
        script = ScriptDirectory.from_config(cfg)
        revision = script.get_revision("20260627_0006")

        assert revision is not None
        assert revision.down_revision == "20260620_0005"

        command.upgrade(cfg, "head")

        engine = create_engine(f"sqlite:///{db_path}")
        try:
            residence_indexes = {index["name"] for index in inspect(engine).get_indexes("residences")}
        finally:
            engine.dispose()

        assert "ix_residences_name" in residence_indexes
        assert "uq_residences_active_name" in residence_indexes
    finally:
        restore_alembic_database_url(cfg)
