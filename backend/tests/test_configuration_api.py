from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.core.security import hash_password
from app.main import app
from app.models.auth import Role, User
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


def test_bootstrap_returns_seeded_core_config(client: TestClient) -> None:
    response = client.get("/api/config/bootstrap", headers=login(client))

    assert response.status_code == 200
    body = response.json()
    assert body["home_space"]["name"] == "我们家"
    assert body["item_statuses"][0]["code"] == "in_stock"
    assert "residences" in body
    assert "categories" in body


def test_admin_creates_residence_location_member_category_and_field(client: TestClient) -> None:
    headers = login(client)

    residence = client.post(
        "/api/config/residences",
        headers=headers,
        json={"name": "现在住处", "description": "主住处", "address": "", "sort_order": 10},
    )
    assert residence.status_code == 201
    residence_id = residence.json()["id"]

    room = client.post(
        "/api/config/location-nodes",
        headers=headers,
        json={"residence_id": residence_id, "name": "客厅", "node_type": "room", "sort_order": 10},
    )
    assert room.status_code == 201

    member = client.post(
        "/api/config/family-members",
        headers=headers,
        json={"name": "妈妈", "relation": "家人", "phone": "", "note": ""},
    )
    assert member.status_code == 201

    category = client.post(
        "/api/config/categories",
        headers=headers,
        json={"code": "documents", "name": "证件", "icon": "document", "sort_order": 10},
    )
    assert category.status_code == 201
    category_id = category.json()["id"]

    field = client.post(
        "/api/config/attribute-definitions",
        headers=headers,
        json={
            "category_id": category_id,
            "key": "expire_date",
            "name": "有效期",
            "field_type": "date",
            "is_filterable": True,
            "sort_order": 10,
        },
    )
    assert field.status_code == 201

    bootstrap = client.get("/api/config/bootstrap", headers=headers).json()
    assert bootstrap["residences"][0]["name"] == "现在住处"
    assert bootstrap["location_tree"][0]["name"] == "客厅"
    assert bootstrap["family_members"][0]["name"] == "妈妈"
    assert bootstrap["categories"][0]["code"] == "documents"


def test_viewer_cannot_create_configuration(client: TestClient, db_session: Session) -> None:
    viewer_role = db_session.query(Role).filter(Role.code == "viewer").one()
    viewer = User(
        username="viewer",
        password_hash=hash_password("Viewer123!"),
        display_name="查看者",
        is_active=True,
    )
    viewer.roles = [viewer_role]
    db_session.add(viewer)
    db_session.commit()

    response = client.post(
        "/api/config/residences",
        headers=login(client, "viewer", "Viewer123!"),
        json={"name": "老家", "description": "", "address": "", "sort_order": 10},
    )

    assert response.status_code == 403
    assert response.json()["message"] == "你没有权限执行此操作"
