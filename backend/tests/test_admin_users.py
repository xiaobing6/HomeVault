from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor
from threading import Event

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from app.api.deps import get_db
from app.core.security import verify_password
from app.main import app
from app.models.auth import AuthSession, User
from app.schemas.admin import AdminUserCreate, AdminUserUpdate
from app.services import admin as admin_service
from app.services.seed import seed_auth_baseline


ROLE_REQUIRED_MESSAGE = "\u7528\u6237\u81f3\u5c11\u9700\u8981\u4e00\u4e2a\u89d2\u8272"
ROLE_NOT_FOUND_MESSAGE = "\u89d2\u8272\u4e0d\u5b58\u5728"
LAST_ACTIVE_ADMIN_MESSAGE = "至少保留一个启用的管理员"


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
    listed_body = listed.json()
    assert listed_body["total"] == 1
    assert listed_body["page"] == 1
    assert listed_body["page_size"] == 20
    user_id = listed_body["items"][0]["id"]

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


def test_admin_password_reset_revokes_existing_target_sessions(
    client: TestClient,
    db_session: Session,
) -> None:
    admin_headers = login(client)
    created = client.post(
        "/api/admin/users",
        headers=admin_headers,
        json={
            "username": "resetme",
            "display_name": "Reset Me",
            "password": "ResetMe123!",
            "role_codes": ["viewer"],
        },
    )
    assert created.status_code == 201
    user_id = created.json()["id"]
    target_headers = login(client, "resetme", "ResetMe123!")

    reset = client.post(
        f"/api/admin/users/{user_id}/reset-password",
        headers=admin_headers,
        json={"password": "NewResetMe123!"},
    )
    assert reset.status_code == 200

    stale_me = client.get("/api/auth/me", headers=target_headers)
    assert stale_me.status_code == 401

    sessions = db_session.scalars(select(AuthSession).where(AuthSession.user_id == user_id)).all()
    assert sessions
    assert all(not session.is_active and session.revoked_at is not None for session in sessions)
    login(client, "resetme", "NewResetMe123!")


def test_admin_user_requests_strip_whitespace_before_storage_and_filtering(
    client: TestClient,
    db_session: Session,
) -> None:
    headers = login(client)

    created = client.post(
        "/api/admin/users",
        headers=headers,
        json={
            "username": " manager ",
            "display_name": " Manager ",
            "password": "Manager123!",
            "role_codes": [" editor "],
        },
    )
    assert created.status_code == 201
    body = created.json()
    assert body["username"] == "manager"
    assert body["display_name"] == "Manager"
    assert body["roles"] == ["editor"]

    saved = db_session.get(User, body["id"])
    assert saved is not None
    assert saved.username == "manager"
    assert saved.display_name == "Manager"

    listed = client.get(
        "/api/admin/users",
        headers=headers,
        params={"search": " manager ", "role": " editor "},
    )
    assert listed.status_code == 200
    assert listed.json()["total"] == 1
    assert listed.json()["items"][0]["username"] == "manager"


def test_admin_user_requests_reject_blank_names_after_trimming(client: TestClient) -> None:
    headers = login(client)

    blank_username = client.post(
        "/api/admin/users",
        headers=headers,
        json={
            "username": "   ",
            "display_name": "Blank Username",
            "password": "BlankUser123!",
            "role_codes": ["viewer"],
        },
    )
    assert blank_username.status_code == 422

    blank_display_name = client.post(
        "/api/admin/users",
        headers=headers,
        json={
            "username": "blankdisplay",
            "display_name": "   ",
            "password": "BlankDisplay123!",
            "role_codes": ["viewer"],
        },
    )
    assert blank_display_name.status_code == 422

    created = client.post(
        "/api/admin/users",
        headers=headers,
        json={
            "username": "blankupdate",
            "display_name": "Blank Update",
            "password": "BlankUpdate123!",
            "role_codes": ["viewer"],
        },
    )
    assert created.status_code == 201

    blank_update = client.patch(
        f"/api/admin/users/{created.json()['id']}",
        headers=headers,
        json={"display_name": "   ", "is_active": True, "role_codes": ["viewer"]},
    )
    assert blank_update.status_code == 422


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
    assert deactivate.json()["message"] == LAST_ACTIVE_ADMIN_MESSAGE

    remove_role = client.patch(
        f"/api/admin/users/{admin_id}",
        headers=headers,
        json={"display_name": "Admin", "is_active": True, "role_codes": ["viewer"]},
    )
    assert remove_role.status_code == 400
    assert remove_role.json()["message"] == LAST_ACTIVE_ADMIN_MESSAGE


def test_concurrent_admin_updates_keep_at_least_one_active_admin(
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    seed_auth_baseline(db_session, admin_username="admin", admin_password="ChangeMe123!")
    second_admin = admin_service.create_user(
        db_session,
        AdminUserCreate(
            username="secondadmin",
            display_name="Second Admin",
            password="SecondAdmin123!",
            role_codes=["admin"],
        ),
    )
    first_admin_id = db_session.scalar(select(User.id).where(User.username == "admin"))
    assert first_admin_id is not None

    first_count_done = Event()
    both_counted = Event()
    original_active_admin_count = admin_service.active_admin_count

    def delayed_active_admin_count(db: Session, excluded_user_id: int | None = None) -> int:
        result = original_active_admin_count(db, excluded_user_id)
        if excluded_user_id in {first_admin_id, second_admin.id}:
            if first_count_done.is_set():
                both_counted.set()
            else:
                first_count_done.set()
            both_counted.wait(timeout=0.25)
        return result

    monkeypatch.setattr(admin_service, "active_admin_count", delayed_active_admin_count)
    TestingSessionLocal = sessionmaker(bind=db_session.get_bind(), autoflush=False, autocommit=False)

    def deactivate_admin(user_id: int) -> tuple[bool, str | None]:
        session = TestingSessionLocal()
        try:
            admin_service.update_user(
                session,
                user_id,
                AdminUserUpdate(
                    display_name=f"Admin {user_id}",
                    is_active=False,
                    role_codes=["admin"],
                ),
            )
            return True, None
        except Exception as exc:  # noqa: BLE001 - assert the service's API error message.
            return False, getattr(exc, "detail", {}).get("message")
        finally:
            session.close()

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(deactivate_admin, [first_admin_id, second_admin.id]))

    db_session.expire_all()
    remaining_active_admins = original_active_admin_count(db_session)
    successes = [result for result in results if result[0]]
    failures = [result for result in results if not result[0]]

    assert len(successes) <= 1
    assert remaining_active_admins == 1
    assert any(message == LAST_ACTIVE_ADMIN_MESSAGE for _success, message in failures)


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

    update_target = client.post(
        "/api/admin/users",
        headers=headers,
        json={
            "username": "updaterole",
            "display_name": "Update Role",
            "password": "UpdateRole123!",
            "role_codes": ["viewer"],
        },
    )
    assert update_target.status_code == 201
    update_user_id = update_target.json()["id"]

    update_empty_roles = client.patch(
        f"/api/admin/users/{update_user_id}",
        headers=headers,
        json={"display_name": "Update Role", "is_active": True, "role_codes": []},
    )
    assert update_empty_roles.status_code == 400
    assert update_empty_roles.json()["message"] == ROLE_REQUIRED_MESSAGE

    update_blank_roles = client.patch(
        f"/api/admin/users/{update_user_id}",
        headers=headers,
        json={"display_name": "Update Role", "is_active": True, "role_codes": ["   "]},
    )
    assert update_blank_roles.status_code == 400
    assert update_blank_roles.json()["message"] == ROLE_REQUIRED_MESSAGE

    update_bad_role = client.patch(
        f"/api/admin/users/{update_user_id}",
        headers=headers,
        json={"display_name": "Update Role", "is_active": True, "role_codes": ["missing"]},
    )
    assert update_bad_role.status_code == 400
    assert update_bad_role.json()["message"] == ROLE_NOT_FOUND_MESSAGE

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
