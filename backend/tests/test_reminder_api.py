from __future__ import annotations

from collections.abc import Iterator
from datetime import timedelta
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.core.config import get_settings
from app.core.security import hash_password
from app.main import app
from app.models.auth import Role, User
from app.models.configuration import Category, FamilyMember, HomeSpace, ItemStatus, LocationNode, Residence
from app.services.reminders import server_today
from app.services.seed import seed_auth_baseline


@pytest.fixture()
def client(db_session: Session, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    upload_dir = tmp_path / "uploads"
    upload_dir.mkdir()
    monkeypatch.setattr(get_settings(), "upload_dir", str(upload_dir), raising=False)
    seed_auth_baseline(db_session, admin_username="admin", admin_password="ChangeMe123!")
    seed_inventory_config(db_session)
    seed_user(db_session, "editor", "Editor123!", "editor")
    seed_user(db_session, "viewer", "Viewer123!", "viewer")

    def override_get_db() -> Iterator[Session]:
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()


def seed_user(db: Session, username: str, password: str, role_code: str) -> User:
    role = db.scalar(select(Role).where(Role.code == role_code))
    assert role is not None
    user = User(username=username, password_hash=hash_password(password), display_name=username.title(), is_active=True)
    user.roles = [role]
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def seed_inventory_config(db: Session) -> None:
    home = db.scalar(select(HomeSpace).order_by(HomeSpace.id))
    assert home is not None
    residence = Residence(name="Main residence", home_space=home, sort_order=10)
    shelf = LocationNode(residence=residence, name="Shelf", node_type="shelf", sort_order=10)
    member = FamilyMember(home_space=home, name="Alex", relation="Owner")
    category = Category(code="documents", name="Documents", sort_order=10)
    db.add_all([residence, shelf, member, category])
    db.commit()


def login(client: TestClient, username: str = "admin", password: str = "ChangeMe123!") -> dict[str, str]:
    response = client.post("/api/auth/login", json={"username": username, "password": password})
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def inventory_ids(db: Session) -> dict[str, int]:
    return {
        "category_id": db.scalar(select(Category.id).where(Category.code == "documents")),
        "in_stock_id": db.scalar(select(ItemStatus.id).where(ItemStatus.code == "in_stock")),
        "shelf_id": db.scalar(select(LocationNode.id).where(LocationNode.name == "Shelf")),
        "member_id": db.scalar(select(FamilyMember.id).where(FamilyMember.name == "Alex")),
    }


def make_item_payload(ids: dict[str, int], **overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "name": "Passport folder",
        "description": "Family documents",
        "category_id": ids["category_id"],
        "status_id": ids["in_stock_id"],
        "quantity": "1.00",
        "unit": "pcs",
        "owner_member_id": ids["member_id"],
        "keeper_member_id": ids["member_id"],
        "location_node_id": ids["shelf_id"],
        "is_container": False,
        "privacy_level": "normal",
        "attribute_values": [],
        "tags": ["Important"],
    }
    payload.update(overrides)
    return payload


def create_item(client: TestClient, headers: dict[str, str], ids: dict[str, int], **overrides: object) -> dict[str, object]:
    response = client.post("/api/items", headers=headers, json=make_item_payload(ids, **overrides))
    assert response.status_code == 201
    return response.json()


def test_editor_can_create_filter_complete_reopen_dismiss_and_archive_reminder(
    client: TestClient,
    db_session: Session,
) -> None:
    headers = login(client, "editor", "Editor123!")
    ids = inventory_ids(db_session)
    item = create_item(client, headers, ids)
    due_date = server_today() + timedelta(days=3)

    created = client.post(
        "/api/reminders",
        headers=headers,
        json={"title": "Check passport", "item_id": item["id"], "due_date": due_date.isoformat(), "priority": "high"},
    )
    reminder_id = created.json()["id"]
    listed = client.get("/api/reminders", headers=headers, params={"upcoming_days": 90})
    detail = client.get(f"/api/reminders/{reminder_id}", headers=headers)
    completed = client.post(f"/api/reminders/{reminder_id}/complete", headers=headers)
    reopened = client.post(f"/api/reminders/{reminder_id}/reopen", headers=headers)
    dismissed = client.post(f"/api/reminders/{reminder_id}/dismiss", headers=headers)
    archived = client.delete(f"/api/reminders/{reminder_id}", headers=headers)

    assert created.status_code == 201
    assert created.json()["item"]["id"] == item["id"]
    assert listed.status_code == 200
    assert listed.json()["total"] == 1
    assert detail.status_code == 200
    assert completed.json()["status"] == "done"
    assert reopened.json()["status"] == "pending"
    assert dismissed.json()["status"] == "dismissed"
    assert archived.status_code == 200
    assert archived.json()["archived_at"] is not None


def test_viewer_can_read_but_cannot_write_reminders(client: TestClient, db_session: Session) -> None:
    admin_headers = login(client)
    viewer_headers = login(client, "viewer", "Viewer123!")
    ids = inventory_ids(db_session)
    item = create_item(client, admin_headers, ids)
    created = client.post("/api/reminders", headers=admin_headers, json={"title": "Read me", "item_id": item["id"]})
    reminder_id = created.json()["id"]

    listed = client.get("/api/reminders", headers=viewer_headers)
    detail = client.get(f"/api/reminders/{reminder_id}", headers=viewer_headers)
    create_response = client.post("/api/reminders", headers=viewer_headers, json={"title": "Nope"})
    complete_response = client.post(f"/api/reminders/{reminder_id}/complete", headers=viewer_headers)

    assert listed.status_code == 200
    assert detail.status_code == 200
    assert create_response.status_code == 403
    assert complete_response.status_code == 403
