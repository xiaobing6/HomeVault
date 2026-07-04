from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import IntegrityError

from app.core.config import get_settings
from app.db.base import Base
from app.models import AuthSession, AuditLog, Category, ExternalIdentity, Item, ItemStatus, Permission, Role, User


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

EXPECTED_AUDIT_TABLES = {"audit_logs"}


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


def _insert_home_space(connection, name: str = "Home") -> int:
    now = datetime.now(timezone.utc)
    result = connection.execute(
        text(
            "INSERT INTO home_spaces (name, description, is_active, created_at, updated_at) "
            "VALUES (:name, '', 1, :created_at, :updated_at)"
        ),
        {"name": name, "created_at": now, "updated_at": now},
    )
    return result.lastrowid


def _insert_residence(connection, home_space_id: int, name: str, is_active: bool) -> None:
    now = datetime.now(timezone.utc)
    connection.execute(
        text(
            "INSERT INTO residences "
            "(home_space_id, name, description, address, is_active, created_at, updated_at) "
            "VALUES (:home_space_id, :name, '', '', :is_active, :created_at, :updated_at)"
        ),
        {
            "home_space_id": home_space_id,
            "name": name,
            "is_active": int(is_active),
            "created_at": now,
            "updated_at": now,
        },
    )


def make_item(db_session: Session, name: str = "Item") -> Item:
    category = Category(code=f"category-{name}", name=f"{name} category")
    status = ItemStatus(code=f"status-{name}", name=f"{name} status", semantic="available")
    db_session.add_all([category, status])
    db_session.flush()
    item = Item(
        name=name,
        category_id=category.id,
        status_id=status.id,
    )
    db_session.add(item)
    db_session.commit()
    db_session.refresh(item)
    return item


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
            with engine.begin() as connection:
                active_index_sql = connection.execute(
                    text(
                        "SELECT sql FROM sqlite_master "
                        "WHERE type = 'index' AND name = 'uq_residences_active_name'"
                    )
                ).scalar_one()
                home_space_id = _insert_home_space(connection)
                _insert_residence(connection, home_space_id, "Lake House", is_active=True)

            with pytest.raises(IntegrityError):
                with engine.begin() as connection:
                    _insert_residence(connection, home_space_id, "Lake House", is_active=True)

            with engine.begin() as connection:
                _insert_residence(connection, home_space_id, "Lake House", is_active=False)
        finally:
            engine.dispose()

        assert "ix_residences_name" in residence_indexes
        assert "uq_residences_active_name" in residence_indexes
        assert "WHERE is_active = 1" in active_index_sql
    finally:
        restore_alembic_database_url(cfg)


def test_residence_active_unique_downgrade_refuses_duplicates_before_dropping_indexes(
    tmp_path: Path,
) -> None:
    db_path = tmp_path / "residence_active_unique_downgrade_guard.sqlite3"
    cfg = alembic_config(str(db_path))

    try:
        command.upgrade(cfg, "head")

        engine = create_engine(f"sqlite:///{db_path}")
        try:
            with engine.begin() as connection:
                home_space_id = _insert_home_space(connection)
                _insert_residence(connection, home_space_id, "Lake House", is_active=True)
                _insert_residence(connection, home_space_id, "Lake House", is_active=False)

            with pytest.raises(RuntimeError, match="duplicate residence names"):
                command.downgrade(cfg, "20260620_0005")

            residence_indexes = {index["name"] for index in inspect(engine).get_indexes("residences")}
        finally:
            engine.dispose()

        assert "ix_residences_name" in residence_indexes
        assert "uq_residences_active_name" in residence_indexes
    finally:
        restore_alembic_database_url(cfg)


def test_audit_log_table_is_registered() -> None:
    assert EXPECTED_AUDIT_TABLES.issubset(set(Base.metadata.tables))


def test_audit_log_model_persists_actor_resource_and_metadata(db_session) -> None:
    user = User(
        username="audit-admin",
        password_hash="hashed-password",
        display_name="Audit Admin",
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    audit_log = AuditLog(
        actor_user_id=user.id,
        actor_username=user.username,
        action="admin.user.create",
        resource_type="user",
        resource_id="42",
        resource_label="manager",
        result="success",
        metadata_json={"changed_fields": ["display_name"], "role_codes": ["viewer"]},
    )
    db_session.add(audit_log)
    db_session.commit()
    db_session.refresh(audit_log)

    assert audit_log.id is not None
    assert audit_log.occurred_at is not None
    assert audit_log.actor is user
    assert audit_log.metadata_json == {
        "changed_fields": ["display_name"],
        "role_codes": ["viewer"],
    }


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
            upgraded_tables = set(inspector.get_table_names())
            audit_column_details = inspector.get_columns("audit_logs")
            audit_columns = {column["name"] for column in audit_column_details}
            audit_column_defaults = {
                column["name"]: column.get("default") for column in audit_column_details
            }
            audit_indexes = {index["name"] for index in inspector.get_indexes("audit_logs")}
            with engine.begin() as connection:
                connection.execute(
                    text(
                        "INSERT INTO audit_logs (action, resource_type, result) "
                        "VALUES (:action, :resource_type, :result)"
                    ),
                    {
                        "action": "auth.login.success",
                        "resource_type": "auth_session",
                        "result": "success",
                    },
                )
                defaulted_occurred_at = connection.execute(
                    text(
                        "SELECT occurred_at FROM audit_logs "
                        "WHERE action = :action AND resource_type = :resource_type"
                    ),
                    {
                        "action": "auth.login.success",
                        "resource_type": "auth_session",
                    },
                ).scalar_one()
        finally:
            engine.dispose()

        assert "audit_logs" in upgraded_tables
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
        assert audit_column_defaults["occurred_at"] is not None
        assert defaulted_occurred_at is not None

        command.downgrade(cfg, "20260627_0006")

        downgraded_engine = create_engine(f"sqlite:///{db_path}")
        try:
            downgraded_tables = set(inspect(downgraded_engine).get_table_names())
        finally:
            downgraded_engine.dispose()

        assert "audit_logs" not in downgraded_tables
    finally:
        restore_alembic_database_url(cfg)


def test_item_importance_migration_removes_storage_condition_dictionary_options(
    tmp_path: Path,
) -> None:
    db_path = tmp_path / "item_importance_storage_conditions.sqlite3"
    cfg = alembic_config(str(db_path))
    inserted_value = "legacy-room-temperature"

    try:
        script = ScriptDirectory.from_config(cfg)
        revision = script.get_revision("20260701_0009")

        assert revision is not None
        assert revision.down_revision == "20260701_0008"

        command.upgrade(cfg, "20260701_0008")

        engine = create_engine(f"sqlite:///{db_path}")
        try:
            with engine.begin() as connection:
                group_id = connection.execute(
                    text(
                        "INSERT INTO dictionary_groups (code, name, is_system, is_active) "
                        "VALUES ('storage_conditions', 'Storage conditions', 1, 1)"
                    )
                ).lastrowid
                connection.execute(
                    text(
                        "INSERT INTO dictionary_options (group_id, label, value, sort_order, is_active) "
                        "VALUES (:group_id, 'Room temperature', :value, 10, 1)"
                    ),
                    {"group_id": group_id, "value": inserted_value},
                )

            command.upgrade(cfg, "20260701_0009")

            item_columns = {column["name"] for column in inspect(engine).get_columns("items")}
            with engine.connect() as connection:
                storage_group_count = connection.execute(
                    text(
                        "SELECT COUNT(*) FROM dictionary_groups "
                        "WHERE code = 'storage_conditions' AND is_system = 1"
                    )
                ).scalar_one()
                inserted_option_count = connection.execute(
                    text("SELECT COUNT(*) FROM dictionary_options WHERE value = :value"),
                    {"value": inserted_value},
                ).scalar_one()
        finally:
            engine.dispose()

        assert storage_group_count == 0
        assert inserted_option_count == 0
        assert "importance" in item_columns
    finally:
        restore_alembic_database_url(cfg)


def test_item_importance_migration_uses_typed_boolean_binds() -> None:
    migration_path = (
        Path(__file__).resolve().parents[1]
        / "alembic"
        / "versions"
        / "20260701_0009_item_importance_and_dictionary_options.py"
    )
    migration_text = migration_path.read_text(encoding="utf-8")

    assert "is_system = 1" not in migration_text
    assert "SELECT :code, :name, 1, 1" not in migration_text
    assert "is_system = :is_system" in migration_text
    assert 'sa.bindparam("is_system", value=True, type_=sa.Boolean())' in migration_text
    assert 'sa.bindparam("is_active", value=True, type_=sa.Boolean())' in migration_text


def test_item_importance_defaults_to_medium(db_session: Session) -> None:
    item = make_item(db_session, name="Importance default")

    assert item.importance == "medium"
