from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.core.security import verify_password
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
    admin_role = next(role for role in roles.json() if role["code"] == "admin")
    assert all(set(permission) == {"code", "name", "description"} for permission in admin_role["permissions"])
    assert "users:manage" in {permission["code"] for permission in admin_role["permissions"]}

    created = client.post(
        "/api/admin/users",
        headers=headers,
        json={
            "username": "manager",
            "display_name": "Manager",
            "password": "Manager123!",
            "role_codes": [" editor ", "editor"],
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
    for username, role_code in [("viewer", "viewer"), ("editor", "editor")]:
        created = client.post(
            "/api/admin/users",
            headers=admin_headers,
            json={
                "username": username,
                "display_name": username.title(),
                "password": f"{username.title()}123!",
                "role_codes": [role_code],
            },
        )
        assert created.status_code == 201
        headers = login(client, username, f"{username.title()}123!")

        response = client.get("/api/admin/users", headers=headers)
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

    blank_roles = client.post(
        "/api/admin/users",
        headers=headers,
        json={
            "username": "blankroles",
            "display_name": "Blank Roles",
            "password": "Blank123!",
            "role_codes": ["   "],
        },
    )
    assert blank_roles.status_code == 400
    assert blank_roles.json()["message"] == "用户至少需要一个角色"

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
