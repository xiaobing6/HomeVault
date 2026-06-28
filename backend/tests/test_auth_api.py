from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.db.base import Base
from app.main import app
from app.models import AuditLog
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


def test_login_success_and_failure_write_audit_logs(
    client: TestClient,
    db_session: Session,
) -> None:
    success = client.post(
        "/api/auth/login",
        json={"username": "admin", "password": "ChangeMe123!"},
    )
    failure = client.post(
        "/api/auth/login",
        json={"username": "admin", "password": "wrong"},
    )

    assert success.status_code == 200
    assert failure.status_code == 401

    audit_logs = db_session.scalars(select(AuditLog).order_by(AuditLog.id)).all()
    last_two = audit_logs[-2:]
    assert [log.action for log in last_two] == ["auth.login", "auth.login"]
    assert [log.result for log in last_two] == ["success", "failure"]
    assert last_two[1].metadata_json == {"attempted_username": "admin"}
    assert "password" not in last_two[1].metadata_json


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


def test_logout_writes_audit_log(client: TestClient, db_session: Session) -> None:
    login = client.post(
        "/api/auth/login",
        json={"username": "admin", "password": "ChangeMe123!"},
    )
    token = login.json()["access_token"]

    logout = client.post("/api/auth/logout", headers={"Authorization": f"Bearer {token}"})

    assert logout.status_code == 204

    audit_log = db_session.scalars(select(AuditLog).order_by(AuditLog.id)).all()[-1]
    assert audit_log.action == "auth.logout"
    assert audit_log.resource_type == "auth_session"
    assert audit_log.result == "success"
    assert audit_log.resource_id


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
