from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.main import app
from app.models import AuditLog
from app.models.auth import Role
from app.services.seed import seed_auth_baseline

ROLE_REQUIRED_MESSAGE = "\u89d2\u8272\u81f3\u5c11\u9700\u8981\u4e00\u4e2a\u6743\u9650"
PERMISSION_NOT_FOUND_MESSAGE = "\u6743\u9650\u4e0d\u5b58\u5728"
SYSTEM_ROLE_READONLY_MESSAGE = "\u7cfb\u7edf\u89d2\u8272\u4e0d\u80fd\u7f16\u8f91"
INACTIVE_ROLE_ASSIGNMENT_MESSAGE = "\u89d2\u8272\u672a\u542f\u7528"
DUPLICATE_ROLE_CODE_MESSAGE = "\u89d2\u8272\u7f16\u7801\u5df2\u5b58\u5728"


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


def permission_codes(role: dict) -> list[str]:
    return [permission["code"] for permission in role["permissions"]]


def test_admin_can_create_update_and_reactivate_custom_role(
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
    created_body = created.json()
    role_id = created_body["id"]
    assert created_body["code"] == "caretaker"
    assert created_body["name"] == "Caretaker"
    assert created_body["description"] == "Maintains daily inventory"
    assert created_body["is_system"] is False
    assert created_body["is_active"] is True
    assert permission_codes(created_body) == ["items:create", "items:view"]

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
    updated_body = updated.json()
    assert updated_body["name"] == "Caretaker Plus"
    assert updated_body["description"] == "Can edit inventory"
    assert updated_body["is_system"] is False
    assert updated_body["is_active"] is False
    assert permission_codes(updated_body) == ["items:edit", "items:view"]

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

    db_session.expire_all()
    saved_role = db_session.get(Role, role_id)
    assert saved_role is not None
    assert saved_role.is_system is False
    assert saved_role.is_active is True


def test_admin_role_mutations_validate_input(client: TestClient) -> None:
    headers = login(client)

    duplicate = client.post(
        "/api/admin/roles",
        headers=headers,
        json={
            "code": "admin",
            "name": "Duplicate Admin",
            "description": "Duplicate system role code",
            "permission_codes": ["items:view"],
            "is_active": True,
        },
    )
    assert duplicate.status_code == 400
    assert duplicate.json()["message"] == DUPLICATE_ROLE_CODE_MESSAGE

    blank_code = client.post(
        "/api/admin/roles",
        headers=headers,
        json={
            "code": "   ",
            "name": "Blank Code",
            "description": "Invalid blank code",
            "permission_codes": ["items:view"],
            "is_active": True,
        },
    )
    assert blank_code.status_code == 422

    blank_name = client.post(
        "/api/admin/roles",
        headers=headers,
        json={
            "code": "blankname",
            "name": "   ",
            "description": "Invalid blank name",
            "permission_codes": ["items:view"],
            "is_active": True,
        },
    )
    assert blank_name.status_code == 422

    unknown_permission = client.post(
        "/api/admin/roles",
        headers=headers,
        json={
            "code": "unknownperm",
            "name": "Unknown Permission",
            "description": "References a missing permission",
            "permission_codes": ["items:view", "items:missing"],
            "is_active": True,
        },
    )
    assert unknown_permission.status_code == 400
    assert unknown_permission.json()["message"] == PERMISSION_NOT_FOUND_MESSAGE

    empty_permissions = client.post(
        "/api/admin/roles",
        headers=headers,
        json={
            "code": "emptypermissions",
            "name": "Empty Permissions",
            "description": "No permissions",
            "permission_codes": [],
            "is_active": True,
        },
    )
    assert empty_permissions.status_code == 400
    assert empty_permissions.json()["message"] == ROLE_REQUIRED_MESSAGE

    roles = client.get("/api/admin/roles", headers=headers)
    assert roles.status_code == 200
    admin_role_id = next(role["id"] for role in roles.json() if role["code"] == "admin")

    system_update = client.patch(
        f"/api/admin/roles/{admin_role_id}",
        headers=headers,
        json={
            "name": "Admin Edited",
            "description": "Should not update",
            "permission_codes": ["items:view"],
            "is_active": True,
        },
    )
    assert system_update.status_code == 400
    assert system_update.json()["message"] == SYSTEM_ROLE_READONLY_MESSAGE


def test_role_mutations_write_audit_logs(
    client: TestClient,
    db_session: Session,
) -> None:
    headers = login(client)

    created = client.post(
        "/api/admin/roles",
        headers=headers,
        json={
            "code": "auditkeeper",
            "name": "Audit Keeper",
            "description": "Tracks daily inventory",
            "permission_codes": ["items:view", "items:create"],
            "is_active": True,
        },
    )
    assert created.status_code == 201
    role_id = created.json()["id"]

    updated = client.patch(
        f"/api/admin/roles/{role_id}",
        headers=headers,
        json={
            "name": "Audit Keeper Plus",
            "description": "Can edit daily inventory",
            "permission_codes": ["items:view", "items:edit"],
            "is_active": False,
        },
    )
    assert updated.status_code == 200

    audit_logs = db_session.scalars(
        select(AuditLog)
        .where(AuditLog.resource_type == "role", AuditLog.resource_label == "auditkeeper")
        .order_by(AuditLog.id)
    ).all()

    assert [log.action for log in audit_logs] == [
        "admin.role.create",
        "admin.role.update",
        "admin.role.deactivate",
    ]
    assert {log.actor_username for log in audit_logs} == {"admin"}
    assert audit_logs[0].resource_id == str(role_id)
    assert audit_logs[0].metadata_json == {
        "permission_codes": ["items:create", "items:view"],
        "is_active": True,
    }
    assert audit_logs[1].metadata_json == {
        "changed_fields": ["name", "description", "permission_codes"],
        "permission_codes": ["items:edit", "items:view"],
        "is_active": False,
    }
    assert audit_logs[2].metadata_json == {"is_active": False}


def test_inactive_custom_role_cannot_be_assigned_until_reactivated(client: TestClient) -> None:
    headers = login(client)

    created = client.post(
        "/api/admin/roles",
        headers=headers,
        json={
            "code": "inactivekeeper",
            "name": "Inactive Keeper",
            "description": "Disabled role",
            "permission_codes": ["items:view"],
            "is_active": False,
        },
    )
    assert created.status_code == 201
    role_id = created.json()["id"]

    inactive_user = client.post(
        "/api/admin/users",
        headers=headers,
        json={
            "username": "inactiveuser",
            "display_name": "Inactive User",
            "password": "Inactive123!",
            "role_codes": ["inactivekeeper"],
        },
    )
    assert inactive_user.status_code == 400
    assert inactive_user.json()["message"] == INACTIVE_ROLE_ASSIGNMENT_MESSAGE

    reactivated = client.patch(
        f"/api/admin/roles/{role_id}",
        headers=headers,
        json={
            "name": "Inactive Keeper",
            "description": "Disabled role",
            "permission_codes": ["items:view"],
            "is_active": True,
        },
    )
    assert reactivated.status_code == 200

    active_user = client.post(
        "/api/admin/users",
        headers=headers,
        json={
            "username": "inactiveuser",
            "display_name": "Inactive User",
            "password": "Inactive123!",
            "role_codes": ["inactivekeeper"],
        },
    )
    assert active_user.status_code == 201
    assert active_user.json()["roles"] == ["inactivekeeper"]
