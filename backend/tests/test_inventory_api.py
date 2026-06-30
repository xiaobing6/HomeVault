from __future__ import annotations

import csv
from io import StringIO
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
from app.models.configuration import AttributeDefinition, Category, FamilyMember, HomeSpace, ItemStatus, LocationNode, Residence
from app.models.inventory import Item
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
        "removed_id": db.scalar(select(ItemStatus.id).where(ItemStatus.semantic == "removed").order_by(ItemStatus.id)),
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


def csv_upload(content: str) -> dict[str, tuple[str, bytes, str]]:
    return {"file": ("items.csv", content.encode("utf-8"), "text/csv")}


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


def test_editor_can_bulk_move_and_change_status_items(client: TestClient, db_session: Session) -> None:
    headers = login(client, "editor", "Editor123!")
    ids = inventory_ids(db_session)
    first = create_item(client, headers, ids, name="First folder", is_container=False)
    second = create_item(client, headers, ids, name="Second folder", is_container=False)

    moved = client.post(
        "/api/items/bulk/move",
        headers=headers,
        json={
            "item_ids": [first["id"], second["id"]],
            "location_node_id": ids["drawer_id"],
            "reason": "Shelf cleanup",
        },
    )
    changed = client.post(
        "/api/items/bulk/status",
        headers=headers,
        json={
            "item_ids": [first["id"], second["id"]],
            "status_id": ids["removed_id"],
            "reason": "Removed from home",
        },
    )
    first_detail = client.get(f"/api/items/{first['id']}", headers=headers)
    second_movements = client.get(f"/api/items/{second['id']}/movements", headers=headers)

    assert moved.status_code == 200
    assert moved.json() == {"updated_count": 2, "item_ids": [first["id"], second["id"]]}
    assert changed.status_code == 200
    assert changed.json()["updated_count"] == 2
    assert first_detail.status_code == 200
    assert first_detail.json()["status_id"] == ids["removed_id"]
    assert first_detail.json()["location_node_id"] is None
    assert second_movements.status_code == 200
    assert [movement["movement_type"] for movement in second_movements.json()] == ["move", "status"]


def test_admin_can_bulk_archive_items(client: TestClient, db_session: Session) -> None:
    headers = login(client)
    ids = inventory_ids(db_session)
    first = create_item(client, headers, ids, name="Archive first")
    second = create_item(client, headers, ids, name="Archive second")

    archived = client.post(
        "/api/items/bulk/archive",
        headers=headers,
        json={"item_ids": [first["id"], second["id"], first["id"]], "archive_reason": "Batch cleanup"},
    )
    active_list = client.get("/api/items", headers=headers)
    archived_list = client.get("/api/items", headers=headers, params={"include_archived": True})
    first_detail = client.get(f"/api/items/{first['id']}", headers=headers)
    second_detail = client.get(f"/api/items/{second['id']}", headers=headers)

    assert archived.status_code == 200
    assert archived.json() == {"updated_count": 2, "item_ids": [first["id"], second["id"]]}
    assert active_list.status_code == 200
    assert active_list.json()["total"] == 0
    assert archived_list.status_code == 200
    assert {item["id"] for item in archived_list.json()["items"]} == {first["id"], second["id"]}
    assert first_detail.json()["archive_reason"] == "Batch cleanup"
    assert second_detail.json()["archive_reason"] == "Batch cleanup"


def test_viewer_cannot_use_bulk_mutation_apis(client: TestClient, db_session: Session) -> None:
    admin_headers = login(client)
    viewer_headers = login(client, "viewer", "Viewer123!")
    ids = inventory_ids(db_session)
    item = create_item(client, admin_headers, ids)

    move_response = client.post(
        "/api/items/bulk/move",
        headers=viewer_headers,
        json={"item_ids": [item["id"]], "location_node_id": ids["drawer_id"]},
    )
    status_response = client.post(
        "/api/items/bulk/status",
        headers=viewer_headers,
        json={"item_ids": [item["id"]], "status_id": ids["removed_id"]},
    )
    archive_response = client.post(
        "/api/items/bulk/archive",
        headers=viewer_headers,
        json={"item_ids": [item["id"]], "archive_reason": "Nope"},
    )

    assert move_response.status_code == 403
    assert status_response.status_code == 403
    assert archive_response.status_code == 403


def test_inventory_csv_export_supports_filters_selection_and_privacy(client: TestClient, db_session: Session) -> None:
    admin_headers = login(client)
    editor_headers = login(client, "editor", "Editor123!")
    ids = inventory_ids(db_session)
    db_session.add(
        AttributeDefinition(
            category_id=ids["category_id"],
            key="passport_number",
            name="Passport number",
            field_type="text",
            privacy_level="sensitive",
            is_active=True,
        )
    )
    db_session.commit()
    sensitive_definition = db_session.scalar(
        select(AttributeDefinition).where(AttributeDefinition.key == "passport_number")
    )
    assert sensitive_definition is not None
    normal = create_item(client, admin_headers, ids, name="Book archive", description="Public notes")
    sensitive = create_item(
        client,
        admin_headers,
        ids,
        name="Passport folder",
        description="Safe combination 12-34-56",
        privacy_level="sensitive",
        attribute_values=[{"attribute_definition_id": sensitive_definition.id, "value": "P1234567"}],
    )

    filtered = client.post(
        "/api/items/export.csv",
        headers=admin_headers,
        json={"filters": {"search": "Book"}},
    )
    selected = client.post(
        "/api/items/export.csv",
        headers=editor_headers,
        json={"item_ids": [normal["id"], sensitive["id"]]},
    )

    assert filtered.status_code == 200
    assert filtered.headers["content-type"].startswith("text/csv")
    filtered_rows = list(csv.DictReader(StringIO(filtered.text)))
    assert [row["name"] for row in filtered_rows] == ["Book archive"]

    assert selected.status_code == 200
    rows = {row["name"]: row for row in csv.DictReader(StringIO(selected.text))}
    assert rows["Book archive"]["description"] == "Public notes"
    assert rows["Passport folder"]["description"] == "******"
    assert rows["Passport folder"]["custom_fields"] == "Passport number=******"


def test_inventory_import_template_includes_static_and_custom_columns(
    client: TestClient,
    db_session: Session,
) -> None:
    headers = login(client)
    ids = inventory_ids(db_session)
    db_session.add(
        AttributeDefinition(
            category_id=ids["category_id"],
            key="serial_number",
            name="Serial number",
            field_type="text",
            is_active=True,
        )
    )
    db_session.commit()

    response = client.get("/api/items/import/template.csv", headers=headers)

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")
    header = response.text.splitlines()[0].split(",")
    assert header[:14] == [
        "name",
        "description",
        "category",
        "status",
        "quantity",
        "unit",
        "owner",
        "keeper",
        "residence",
        "location",
        "container",
        "is_container",
        "privacy_level",
        "tags",
    ]
    assert "field:serial_number" in header


def test_inventory_import_preview_validates_rows_without_creating_items(
    client: TestClient,
    db_session: Session,
) -> None:
    headers = login(client)
    content = "\n".join(
        [
            "name,description,category,status,quantity,unit,owner,keeper,residence,location,container,is_container,privacy_level,tags",
            'Imported folder,From CSV,documents,in_stock,3,pcs,Alex,Alex,Main residence,Shelf,,true,sensitive,"Travel, Paper"',
        ]
    )

    response = client.post("/api/items/import/preview", headers=headers, files=csv_upload(content))
    item_count = db_session.scalar(select(Item.id).where(Item.name == "Imported folder").limit(1))

    assert response.status_code == 200
    body = response.json()
    assert body["token"]
    assert body["total_count"] == 1
    assert body["valid_count"] == 1
    assert body["invalid_count"] == 0
    assert body["rows"][0]["row_number"] == 2
    assert body["rows"][0]["is_valid"] is True
    assert body["rows"][0]["normalized"]["name"] == "Imported folder"
    assert body["rows"][0]["normalized"]["privacy_level"] == "sensitive"
    assert body["rows"][0]["warnings"] == []
    assert item_count is None


def test_inventory_import_preview_reports_row_errors(client: TestClient) -> None:
    headers = login(client)
    content = "\n".join(
        [
            "name,description,category,status,quantity,unit,owner,keeper,residence,location,container,is_container,privacy_level,tags",
            ",Missing name,documents,in_stock,abc,pcs,Alex,Alex,Main residence,Shelf,,false,normal,",
            "Bad category,,unknown,in_stock,1,pcs,Alex,Alex,Main residence,Shelf,,false,normal,",
        ]
    )

    response = client.post("/api/items/import/preview", headers=headers, files=csv_upload(content))

    assert response.status_code == 200
    body = response.json()
    assert body["token"] is None
    assert body["total_count"] == 2
    assert body["valid_count"] == 0
    assert body["invalid_count"] == 2
    assert body["rows"][0]["is_valid"] is False
    assert {error["field"] for error in body["rows"][0]["errors"]} == {"name", "quantity"}
    assert body["rows"][1]["errors"][0]["field"] == "category"


def test_inventory_import_confirm_creates_previewed_items(client: TestClient, db_session: Session) -> None:
    headers = login(client)
    content = "\n".join(
        [
            "name,description,category,status,quantity,unit,owner,keeper,residence,location,container,is_container,privacy_level,tags",
            'Imported folder,From CSV,documents,in_stock,3,pcs,Alex,Alex,Main residence,Shelf,,true,normal,"Travel, Paper"',
            "Imported envelope,Second row,documents,in_stock,1,pcs,Alex,Alex,Main residence,Drawer,,false,normal,Paper",
        ]
    )
    preview = client.post("/api/items/import/preview", headers=headers, files=csv_upload(content))
    token = preview.json()["token"]

    response = client.post("/api/items/import/confirm", headers=headers, json={"token": token})
    imported_items = db_session.scalars(select(Item).where(Item.name.like("Imported%")).order_by(Item.name)).all()

    assert response.status_code == 200
    assert response.json()["imported_count"] == 2
    assert len(response.json()["item_ids"]) == 2
    assert [item.name for item in imported_items] == ["Imported envelope", "Imported folder"]
    assert imported_items[1].quantity == 3
    assert imported_items[1].is_container is True
    assert imported_items[1].tag_links[0].tag.normalized_name == "paper"


def test_inventory_import_confirm_rejects_invalid_token(client: TestClient) -> None:
    headers = login(client)
    response = client.post("/api/items/import/confirm", headers=headers, json={"token": "missing-token"})
    assert response.status_code == 400
    assert response.json()["message"]


def test_inventory_import_requires_create_permission(client: TestClient) -> None:
    viewer_headers = login(client, "viewer", "Viewer123!")
    content = "\n".join(
        [
            "name,description,category,status,quantity,unit,owner,keeper,residence,location,container,is_container,privacy_level,tags",
            "Imported folder,From CSV,documents,in_stock,1,pcs,Alex,Alex,Main residence,Shelf,,false,normal,",
        ]
    )
    template = client.get("/api/items/import/template.csv", headers=viewer_headers)
    preview = client.post("/api/items/import/preview", headers=viewer_headers, files=csv_upload(content))
    confirm = client.post("/api/items/import/confirm", headers=viewer_headers, json={"token": "any"})
    assert template.status_code == 403
    assert preview.status_code == 403
    assert confirm.status_code == 403


def test_inventory_import_preview_rejects_ambiguous_members(
    client: TestClient,
    db_session: Session,
) -> None:
    headers = login(client)
    home = db_session.scalar(select(HomeSpace).order_by(HomeSpace.id))
    assert home is not None
    db_session.add(FamilyMember(home_space=home, name="Alex", relation="Backup owner"))
    db_session.commit()
    content = "\n".join(
        [
            "name,description,category,status,quantity,unit,owner,keeper,residence,location,container,is_container,privacy_level,tags",
            "Imported folder,From CSV,documents,in_stock,1,pcs,Alex,Alex,Main residence,Shelf,,false,normal,",
        ]
    )

    response = client.post("/api/items/import/preview", headers=headers, files=csv_upload(content))

    assert response.status_code == 200
    body = response.json()
    assert body["token"] is None
    assert body["invalid_count"] == 1
    errors = {error["field"]: error["message"] for error in body["rows"][0]["errors"]}
    assert errors["owner"] == "家庭成员名称不唯一，请进一步区分"
    assert errors["keeper"] == "家庭成员名称不唯一，请进一步区分"


def test_inventory_import_preview_rejects_ambiguous_locations_without_residence(
    client: TestClient,
    db_session: Session,
) -> None:
    headers = login(client)
    home = db_session.scalar(select(HomeSpace).order_by(HomeSpace.id))
    assert home is not None
    other_residence = Residence(name="Cabin", home_space=home, sort_order=20)
    db_session.add(LocationNode(residence=other_residence, name="Shelf", node_type="shelf", sort_order=10))
    db_session.commit()
    content = "\n".join(
        [
            "name,description,category,status,quantity,unit,owner,keeper,residence,location,container,is_container,privacy_level,tags",
            "Ambiguous shelf,From CSV,documents,in_stock,1,pcs,Alex,Alex,,Shelf,,false,normal,",
            "Scoped shelf,From CSV,documents,in_stock,1,pcs,Alex,Alex,Main residence,Shelf,,false,normal,",
        ]
    )

    response = client.post("/api/items/import/preview", headers=headers, files=csv_upload(content))

    assert response.status_code == 200
    body = response.json()
    assert body["token"] is None
    assert body["valid_count"] == 1
    assert body["invalid_count"] == 1
    assert body["rows"][0]["errors"][0] == {
        "field": "location",
        "message": "位置名称不唯一，请填写住所或完整路径",
    }
    assert body["rows"][1]["is_valid"] is True
    assert body["rows"][1]["normalized"]["name"] == "Scoped shelf"


def test_inventory_import_preview_rejects_ambiguous_containers(
    client: TestClient,
    db_session: Session,
) -> None:
    headers = login(client)
    ids = inventory_ids(db_session)
    create_item(client, headers, ids, name="Shared box", is_container=True, location_node_id=ids["shelf_id"])
    create_item(client, headers, ids, name="Shared box", is_container=True, location_node_id=ids["drawer_id"])
    content = "\n".join(
        [
            "name,description,category,status,quantity,unit,owner,keeper,residence,location,container,is_container,privacy_level,tags",
            "Imported folder,From CSV,documents,in_stock,1,pcs,Alex,Alex,,,Shared box,false,normal,",
        ]
    )

    response = client.post("/api/items/import/preview", headers=headers, files=csv_upload(content))

    assert response.status_code == 200
    body = response.json()
    assert body["token"] is None
    assert body["invalid_count"] == 1
    assert body["rows"][0]["errors"][0] == {
        "field": "container",
        "message": "容器名称不唯一，请进一步区分",
    }


def test_non_admin_inventory_reads_redact_sensitive_content(client: TestClient, db_session: Session) -> None:
    admin_headers = login(client)
    editor_headers = login(client, "editor", "Editor123!")
    ids = inventory_ids(db_session)
    db_session.add(
        AttributeDefinition(
            category_id=ids["category_id"],
            key="passport_number",
            name="Passport number",
            field_type="text",
            privacy_level="sensitive",
            is_active=True,
        )
    )
    db_session.commit()
    sensitive_definition = db_session.scalar(
        select(AttributeDefinition).where(AttributeDefinition.key == "passport_number")
    )
    assert sensitive_definition is not None

    item = create_item(
        client,
        admin_headers,
        ids,
        description="Safe combination 12-34-56",
        privacy_level="sensitive",
        attribute_values=[
            {"attribute_definition_id": sensitive_definition.id, "value": "P1234567"},
        ],
    )
    image = client.post(
        f"/api/items/{item['id']}/images",
        headers=admin_headers,
        files={"file": ("passport.png", PNG_BYTES, "image/png")},
        data={"is_primary": "true"},
    )
    attachment = client.post(
        f"/api/items/{item['id']}/attachments",
        headers=admin_headers,
        files={"file": ("contract.pdf", b"%PDF-1.7\n", "application/pdf")},
    )
    assert image.status_code == 201
    assert attachment.status_code == 201

    admin_detail = client.get(f"/api/items/{item['id']}", headers=admin_headers)
    editor_list = client.get("/api/items", headers=editor_headers)
    editor_detail = client.get(f"/api/items/{item['id']}", headers=editor_headers)
    editor_image = client.get(
        f"/api/items/{item['id']}/images/{image.json()['id']}/file",
        headers=editor_headers,
    )
    editor_attachment = client.get(
        f"/api/items/{item['id']}/attachments/{attachment.json()['id']}/download",
        headers=editor_headers,
    )

    assert admin_detail.status_code == 200
    assert admin_detail.json()["description"] == "Safe combination 12-34-56"
    assert admin_detail.json()["attribute_values"][0]["value"] == "P1234567"
    assert admin_detail.json()["images"][0]["url"]
    assert admin_detail.json()["attachments"][0]["download_url"]
    assert editor_list.status_code == 200
    assert editor_list.json()["items"][0]["description"] == "******"
    assert editor_list.json()["items"][0]["primary_image_url"] is None
    assert editor_detail.status_code == 200
    assert editor_detail.json()["description"] == "******"
    assert editor_detail.json()["attribute_values"][0]["value"] == "******"
    assert editor_detail.json()["images"] == []
    assert editor_detail.json()["attachments"] == []
    assert editor_image.status_code == 404
    assert editor_attachment.status_code == 404


def test_legacy_private_privacy_level_is_treated_as_sensitive(client: TestClient, db_session: Session) -> None:
    admin_headers = login(client)
    editor_headers = login(client, "editor", "Editor123!")
    ids = inventory_ids(db_session)
    item = create_item(
        client,
        admin_headers,
        ids,
        description="Legacy private description",
    )
    db_item = db_session.get(Item, item["id"])
    assert db_item is not None
    db_item.privacy_level = "private"
    db_session.commit()

    admin_detail = client.get(f"/api/items/{item['id']}", headers=admin_headers)
    editor_detail = client.get(f"/api/items/{item['id']}", headers=editor_headers)

    assert admin_detail.status_code == 200
    assert admin_detail.json()["privacy_level"] == "sensitive"
    assert admin_detail.json()["description"] == "Legacy private description"
    assert editor_detail.status_code == 200
    assert editor_detail.json()["privacy_level"] == "sensitive"
    assert editor_detail.json()["description"] == "******"


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
