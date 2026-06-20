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


PNG_BYTES = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR"


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
    user = User(
        username=username,
        password_hash=hash_password(password),
        display_name=username.title(),
        is_active=True,
    )
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
    drawer = LocationNode(residence=residence, name="Drawer", node_type="drawer", sort_order=20)
    member = FamilyMember(home_space=home, name="Alex", relation="Owner")
    category = Category(code="documents", name="Documents", sort_order=10)
    db.add_all([residence, shelf, drawer, member, category])
    db.commit()


def login(client: TestClient, username: str = "admin", password: str = "ChangeMe123!") -> dict[str, str]:
    response = client.post("/api/auth/login", json={"username": username, "password": password})
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def inventory_ids(db: Session) -> dict[str, int]:
    return {
        "category_id": db.scalar(select(Category.id).where(Category.code == "documents")),
        "in_stock_id": db.scalar(select(ItemStatus.id).where(ItemStatus.code == "in_stock")),
        "removed_id": db.scalar(select(ItemStatus.id).where(ItemStatus.code == "removed")),
        "shelf_id": db.scalar(select(LocationNode.id).where(LocationNode.name == "Shelf")),
        "drawer_id": db.scalar(select(LocationNode.id).where(LocationNode.name == "Drawer")),
        "member_id": db.scalar(select(FamilyMember.id).where(FamilyMember.name == "Alex")),
    }


def make_item_payload(ids: dict[str, int], **overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "name": "Passport folder",
        "description": "Family documents",
        "category_id": ids["category_id"],
        "status_id": ids["in_stock_id"],
        "quantity": "2.00",
        "unit": "pcs",
        "owner_member_id": ids["member_id"],
        "keeper_member_id": ids["member_id"],
        "location_node_id": ids["shelf_id"],
        "is_container": True,
        "privacy_level": "normal",
        "attribute_values": [],
        "tags": ["Important", "Travel"],
    }
    payload.update(overrides)
    return payload


def create_item(client: TestClient, headers: dict[str, str], ids: dict[str, int], **overrides: object) -> dict[str, object]:
    response = client.post("/api/items", headers=headers, json=make_item_payload(ids, **overrides))
    assert response.status_code == 201
    return response.json()


def test_admin_can_create_list_detail_update_and_archive_item(client: TestClient, db_session: Session) -> None:
    headers = login(client)
    ids = inventory_ids(db_session)

    created = create_item(client, headers, ids)
    listed = client.get("/api/items", headers=headers, params={"search": "passport"})
    detail = client.get(f"/api/items/{created['id']}", headers=headers)
    updated = client.patch(
        f"/api/items/{created['id']}",
        headers=headers,
        json={"name": "Updated passport folder", "tags": ["Updated"]},
    )
    reused_tag = client.post("/api/tags", headers=headers, json={"name": " Updated "})
    tags = client.get("/api/tags", headers=headers, params={"search": "up"})
    archived = client.post(
        f"/api/items/{created['id']}/archive",
        headers=headers,
        json={"archive_reason": "Scanned"},
    )
    archived_list = client.get("/api/items", headers=headers, params={"include_archived": True})

    assert created["name"] == "Passport folder"
    assert created["created_by_id"] is not None
    assert listed.status_code == 200
    assert listed.json()["total"] == 1
    assert listed.json()["items"][0]["id"] == created["id"]
    assert detail.status_code == 200
    assert detail.json()["tags"][0]["normalized_name"] == "important"
    assert updated.status_code == 200
    assert updated.json()["name"] == "Updated passport folder"
    assert [tag["normalized_name"] for tag in updated.json()["tags"]] == ["updated"]
    assert reused_tag.status_code == 201
    assert reused_tag.json()["normalized_name"] == "updated"
    assert tags.status_code == 200
    assert [tag["normalized_name"] for tag in tags.json()] == ["updated"]
    assert archived.status_code == 200
    assert archived.json()["is_archived"] is True
    assert archived.json()["archive_reason"] == "Scanned"
    assert archived_list.json()["items"][0]["is_archived"] is True


def test_editor_can_create_move_borrow_return_and_adjust_quantity(client: TestClient, db_session: Session) -> None:
    headers = login(client, "editor", "Editor123!")
    ids = inventory_ids(db_session)
    item = create_item(client, headers, ids, is_container=False)
    container = create_item(client, headers, ids, name="Archive box")

    moved = client.post(
        f"/api/items/{item['id']}/move",
        headers=headers,
        json={"container_item_id": container["id"], "reason": "Boxed"},
    )
    adjusted = client.post(
        f"/api/items/{item['id']}/quantity-adjustments",
        headers=headers,
        json={"delta": "3.00", "reason": "Restocked"},
    )
    changes = client.get(f"/api/items/{item['id']}/quantity-adjustments", headers=headers)
    loaned = client.post(
        f"/api/items/{item['id']}/loans",
        headers=headers,
        json={"borrower_name": "Taylor", "borrower_contact": "taylor@example.test", "loan_note": "Weekend"},
    )
    loan_id = loaned.json()["loans"][0]["id"]
    returned = client.post(
        f"/api/items/{item['id']}/loans/{loan_id}/return",
        headers=headers,
        json={"location_node_id": ids["drawer_id"], "target_status_id": ids["in_stock_id"], "return_note": "Back"},
    )
    movements = client.get(f"/api/items/{item['id']}/movements", headers=headers)
    archive = client.post(f"/api/items/{item['id']}/archive", headers=headers, json={})

    assert moved.status_code == 200
    assert moved.json()["container_item_id"] == container["id"]
    assert adjusted.status_code == 200
    assert adjusted.json()["quantity"] == "5.00"
    assert changes.status_code == 200
    assert changes.json()[0]["reason"] == "Restocked"
    assert loaned.status_code == 200
    assert loaned.json()["loans"][0]["borrower_name"] == "Taylor"
    assert returned.status_code == 200
    assert returned.json()["location_node_id"] == ids["drawer_id"]
    assert movements.status_code == 200
    assert {movement["movement_type"] for movement in movements.json()} == {"move", "status"}
    assert archive.status_code == 403


def test_viewer_can_read_but_cannot_write_inventory(client: TestClient, db_session: Session) -> None:
    admin_headers = login(client)
    viewer_headers = login(client, "viewer", "Viewer123!")
    ids = inventory_ids(db_session)
    item = create_item(client, admin_headers, ids)

    listed = client.get("/api/items", headers=viewer_headers)
    detail = client.get(f"/api/items/{item['id']}", headers=viewer_headers)
    create_response = client.post("/api/items", headers=viewer_headers, json=make_item_payload(ids, name="Nope"))
    update_response = client.patch(f"/api/items/{item['id']}", headers=viewer_headers, json={"name": "Nope"})
    move_response = client.post(
        f"/api/items/{item['id']}/move",
        headers=viewer_headers,
        json={"location_node_id": ids["drawer_id"]},
    )
    upload_response = client.post(
        f"/api/items/{item['id']}/images",
        headers=viewer_headers,
        files={"file": ("front.png", PNG_BYTES, "image/png")},
        data={"is_primary": "true"},
    )
    archive_response = client.post(f"/api/items/{item['id']}/archive", headers=viewer_headers, json={})

    assert listed.status_code == 200
    assert listed.json()["total"] == 1
    assert detail.status_code == 200
    assert detail.json()["id"] == item["id"]
    assert create_response.status_code == 403
    assert update_response.status_code == 403
    assert move_response.status_code == 403
    assert upload_response.status_code == 403
    assert archive_response.status_code == 403


def test_inventory_api_rejects_container_cycle(client: TestClient, db_session: Session) -> None:
    headers = login(client)
    ids = inventory_ids(db_session)
    parent = create_item(client, headers, ids, name="Parent box")
    child = create_item(
        client,
        headers,
        ids,
        name="Child box",
        location_node_id=None,
        container_item_id=parent["id"],
    )

    response = client.post(
        f"/api/items/{parent['id']}/move",
        headers=headers,
        json={"container_item_id": child["id"], "reason": "Invalid nesting"},
    )

    assert response.status_code == 400
    assert response.json()["message"]


def test_inventory_api_uploads_image_and_attachment(client: TestClient, db_session: Session) -> None:
    headers = login(client)
    viewer_headers = login(client, "viewer", "Viewer123!")
    ids = inventory_ids(db_session)
    item = create_item(client, headers, ids)
    other_item = create_item(client, headers, ids, name="Other folder")

    image = client.post(
        f"/api/items/{item['id']}/images",
        headers=headers,
        files={"file": ("front.png", PNG_BYTES, "image/png")},
        data={"is_primary": "true"},
    )
    assert image.status_code == 201
    image_id = image.json()["id"]

    image_update = client.patch(
        f"/api/items/{item['id']}/images/{image_id}",
        headers=headers,
        json={"is_primary": True, "sort_order": 5},
    )
    attachment = client.post(
        f"/api/items/{item['id']}/attachments",
        headers=headers,
        files={"file": ("manual.pdf", b"%PDF-1.7\n", "application/pdf")},
    )
    assert attachment.status_code == 201
    attachment_id = attachment.json()["id"]
    image_file_url = f"/api/items/{item['id']}/images/{image_id}/file"
    attachment_download_url = f"/api/items/{item['id']}/attachments/{attachment_id}/download"

    detail = client.get(f"/api/items/{item['id']}", headers=headers)
    anonymous_image = client.get(image_file_url)
    anonymous_attachment = client.get(attachment_download_url)
    viewer_image = client.get(image_file_url, headers=viewer_headers)
    viewer_attachment = client.get(attachment_download_url, headers=viewer_headers)
    wrong_item_image = client.get(
        f"/api/items/{other_item['id']}/images/{image_id}/file",
        headers=viewer_headers,
    )
    missing_attachment_path = Path(get_settings().upload_dir) / attachment.json()["file_path"]
    missing_attachment_path.unlink()
    missing_attachment = client.get(attachment_download_url, headers=viewer_headers)
    image_delete = client.delete(f"/api/items/{item['id']}/images/{image_id}", headers=headers)
    attachment_delete = client.delete(
        f"/api/items/{item['id']}/attachments/{attachment_id}",
        headers=headers,
    )

    assert image.json()["url"] == image_file_url
    assert image.json()["is_primary"] is True
    assert image_update.status_code == 200
    assert image_update.json()["sort_order"] == 5
    assert attachment.json()["download_url"] == attachment_download_url
    assert detail.json()["primary_image_url"] == image_file_url
    assert detail.json()["images"][0]["url"] == image_file_url
    assert detail.json()["attachments"][0]["download_url"] == attachment_download_url
    assert anonymous_image.status_code == 401
    assert anonymous_attachment.status_code == 401
    assert viewer_image.status_code == 200
    assert viewer_image.content == PNG_BYTES
    assert viewer_attachment.status_code == 200
    assert viewer_attachment.content == b"%PDF-1.7\n"
    assert wrong_item_image.status_code == 404
    assert missing_attachment.status_code == 404
    assert image_delete.status_code == 200
    assert image_delete.json()["images"] == []
    assert attachment_delete.status_code == 200
    assert attachment_delete.json()["attachments"] == []


def test_inventory_api_ignores_false_primary_image_update(client: TestClient, db_session: Session) -> None:
    headers = login(client)
    ids = inventory_ids(db_session)
    item = create_item(client, headers, ids)
    image = client.post(
        f"/api/items/{item['id']}/images",
        headers=headers,
        files={"file": ("front.png", PNG_BYTES, "image/png")},
        data={"is_primary": "true"},
    )
    assert image.status_code == 201
    image_id = image.json()["id"]

    image_update = client.patch(
        f"/api/items/{item['id']}/images/{image_id}",
        headers=headers,
        json={"is_primary": False},
    )
    detail = client.get(f"/api/items/{item['id']}", headers=headers)

    assert image_update.status_code == 200
    assert image_update.json()["is_primary"] is True
    assert detail.status_code == 200
    assert detail.json()["images"][0]["is_primary"] is True
    assert detail.json()["primary_image_url"] == detail.json()["images"][0]["url"]


def test_inventory_api_filters_items_by_reminders(client: TestClient, db_session: Session) -> None:
    headers = login(client)
    ids = inventory_ids(db_session)
    item = create_item(client, headers, ids)
    overdue_date = server_today() - timedelta(days=1)
    reminder = client.post(
        "/api/reminders",
        headers=headers,
        json={"title": "Late", "item_id": item["id"], "due_date": overdue_date.isoformat()},
    )
    overdue = client.get("/api/items", headers=headers, params={"has_overdue_reminder": True})
    upcoming = client.get(
        "/api/items",
        headers=headers,
        params={"has_upcoming_reminder": True, "reminder_upcoming_days": 7},
    )
    pending = client.get("/api/items", headers=headers, params={"has_pending_reminder": True})

    assert reminder.status_code == 201
    assert overdue.status_code == 200
    assert overdue.json()["total"] == 1
    assert overdue.json()["items"][0]["id"] == item["id"]
    assert upcoming.status_code == 200
    assert upcoming.json()["total"] == 0
    assert pending.status_code == 200
    assert pending.json()["total"] == 1
