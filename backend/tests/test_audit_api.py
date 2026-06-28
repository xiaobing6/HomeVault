from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.main import app
from app.services.audit import record_audit_log
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


@pytest.mark.parametrize("role_code", ["viewer", "editor"])
def test_users_without_logs_view_are_forbidden(
    client: TestClient,
    db_session: Session,
    role_code: str,
) -> None:
    admin_headers = login(client)
    record = record_audit_log(
        db_session,
        action="admin.user.create",
        resource_type="user",
        resource_id=7,
        resource_label="manager",
        actor_username="admin",
    )
    db_session.commit()
    created = client.post(
        "/api/admin/users",
        headers=admin_headers,
        json={
            "username": role_code,
            "display_name": role_code.title(),
            "password": f"{role_code.title()}123!",
            "role_codes": [role_code],
        },
    )
    assert created.status_code == 201
    restricted_headers = login(client, role_code, f"{role_code.title()}123!")

    listed = client.get("/api/audit/logs", headers=restricted_headers)
    detail = client.get(f"/api/audit/logs/{record.id}", headers=restricted_headers)
    assert listed.status_code == 403
    assert detail.status_code == 403


def test_missing_audit_log_detail_returns_not_found(client: TestClient) -> None:
    headers = login(client)

    response = client.get("/api/audit/logs/9999", headers=headers)

    assert response.status_code == 404
    assert response.json()["message"] == "日志不存在"
