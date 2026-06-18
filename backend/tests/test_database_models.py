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
