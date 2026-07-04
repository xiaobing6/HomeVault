from collections.abc import Iterator
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.core.security import hash_password
from app.main import app
from app.models import AuditLog
from app.models.auth import Role, User
from app.models.configuration import AttributeDefinition, AttributeOption, DictionaryOption, Residence
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


PNG_BYTES = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR"


def test_residence_payloads_include_audit_metadata_image_and_updated_order(
    client: TestClient,
    db_session: Session,
) -> None:
    headers = login(client)

    first = client.post(
        "/api/config/residences",
        headers=headers,
        json={"name": "First home", "description": "", "address": ""},
    )
    second = client.post(
        "/api/config/residences",
        headers=headers,
        json={"name": "Second home", "description": "", "address": ""},
    )
    assert first.status_code == 201
    assert second.status_code == 201
    assert first.json()["is_active"] is True

    first_row = db_session.get(Residence, first.json()["id"])
    second_row = db_session.get(Residence, second.json()["id"])
    assert first_row is not None
    assert second_row is not None
    first_row.updated_at = datetime.now(timezone.utc) - timedelta(days=1)
    second_row.updated_at = datetime.now(timezone.utc)
    db_session.commit()

    upload = client.post(
        f"/api/config/residences/{second.json()['id']}/image",
        headers=headers,
        files={"file": ("front.png", PNG_BYTES, "image/png")},
    )
    assert upload.status_code == 200
    assert upload.json()["image_url"] == f"/api/config/residences/{second.json()['id']}/image/file"
    assert upload.json()["image_original_filename"] == "front.png"
    assert "sort_order" not in upload.json()

    image_file = client.get(upload.json()["image_url"], headers=headers)
    assert image_file.status_code == 200
    assert image_file.content == PNG_BYTES

    replacement = client.post(
        f"/api/config/residences/{second.json()['id']}/image",
        headers=headers,
        files={"file": ("replace.webp", b"RIFFxxxxWEBPpayload", "image/webp")},
    )
    assert replacement.status_code == 200
    assert replacement.json()["image_original_filename"] == "replace.webp"

    residences = client.get("/api/config/residences", headers=headers)
    assert residences.status_code == 200
    body = residences.json()
    assert [residence["name"] for residence in body] == ["Second home", "First home"]
    assert "sort_order" not in body[0]
    for field in ["created_at", "updated_at", "created_by_id", "created_by_name", "updated_by_id", "updated_by_name"]:
        assert body[0][field]


def test_configuration_mutations_write_audit_logs(
    client: TestClient,
    db_session: Session,
) -> None:
    headers = login(client)

    residence = client.post(
        "/api/config/residences",
        headers=headers,
        json={"name": "Audit Home", "description": "", "address": "", "sort_order": 1},
    )
    assert residence.status_code == 201
    residence_id = residence.json()["id"]

    residence_update = client.patch(
        f"/api/config/residences/{residence_id}",
        headers=headers,
        json={
            "name": "Audit Home",
            "description": "Updated",
            "address": "",
            "sort_order": 1,
            "is_active": False,
        },
    )
    assert residence_update.status_code == 200

    location = client.post(
        "/api/config/location-nodes",
        headers=headers,
        json={"residence_id": residence_id, "name": "Shelf", "node_type": "area"},
    )
    assert location.status_code == 201
    location_id = location.json()["id"]

    location_update = client.patch(
        f"/api/config/location-nodes/{location_id}",
        headers=headers,
        json={
            "parent_id": None,
            "name": "Shelf Updated",
            "node_type": "cabinet",
            "icon": "",
            "sort_order": 2,
            "note": "",
            "is_active": False,
        },
    )
    assert location_update.status_code == 200

    audit_logs = db_session.scalars(
        select(AuditLog)
        .where(AuditLog.action.like("config.%"))
        .order_by(AuditLog.id)
    ).all()
    audit_logs_by_action = {log.action: log for log in audit_logs}

    assert set(audit_logs_by_action) == {
        "config.residence.create",
        "config.residence.update",
        "config.location.create",
        "config.location.update",
    }
    assert {log.actor_username for log in audit_logs} == {"admin"}

    residence_create_log = audit_logs_by_action["config.residence.create"]
    assert residence_create_log.resource_type == "residence"
    assert residence_create_log.resource_id == str(residence_id)
    assert residence_create_log.resource_label == "Audit Home"
    assert residence_create_log.metadata_json == {"is_active": True}

    residence_update_log = audit_logs_by_action["config.residence.update"]
    assert residence_update_log.resource_type == "residence"
    assert residence_update_log.resource_id == str(residence_id)
    assert residence_update_log.resource_label == "Audit Home"
    assert residence_update_log.metadata_json == {"is_active": False}

    location_create_log = audit_logs_by_action["config.location.create"]
    assert location_create_log.resource_type == "location_node"
    assert location_create_log.resource_id == str(location_id)
    assert location_create_log.resource_label == "Shelf"
    assert location_create_log.metadata_json == {"residence_id": residence_id}

    location_update_log = audit_logs_by_action["config.location.update"]
    assert location_update_log.resource_type == "location_node"
    assert location_update_log.resource_id == str(location_id)
    assert location_update_log.resource_label == "Shelf Updated"
    assert location_update_log.metadata_json == {
        "residence_id": residence_id,
        "changed_fields": ["name", "node_type", "sort_order", "is_active"],
        "is_active": False,
    }


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


def test_created_attribute_definition_is_returned_in_category_read_payloads(client: TestClient) -> None:
    headers = login(client)

    category = client.post(
        "/api/config/categories",
        headers=headers,
        json={"code": "documents", "name": "Documents", "icon": "document", "sort_order": 10},
    )
    assert category.status_code == 201
    category_id = category.json()["id"]

    field = client.post(
        "/api/config/attribute-definitions",
        headers=headers,
        json={
            "category_id": category_id,
            "key": "expire_date",
            "name": "Expire date",
            "field_type": "date",
            "is_filterable": True,
            "sort_order": 10,
        },
    )
    assert field.status_code == 201

    bootstrap = client.get("/api/config/bootstrap", headers=headers)
    categories = client.get("/api/config/categories", headers=headers)

    assert bootstrap.status_code == 200
    assert categories.status_code == 200
    for category_payload in (bootstrap.json()["categories"][0], categories.json()[0]):
        assert category_payload["code"] == "documents"
        assert category_payload["attribute_definitions"] == [
            {
                "id": field.json()["id"],
                "category_id": category_id,
                "key": "expire_date",
                "name": "Expire date",
                "field_type": "date",
                "default_value": "",
                "privacy_level": "normal",
                "is_required": False,
                "is_filterable": True,
                "sort_order": 10,
                "is_active": True,
                "options": [],
            }
        ]


def test_attribute_definition_rejects_removed_encrypted_text_field_type(client: TestClient) -> None:
    headers = login(client)
    category = client.post(
        "/api/config/categories",
        headers=headers,
        json={"code": "documents", "name": "Documents"},
    )
    assert category.status_code == 201

    response = client.post(
        "/api/config/attribute-definitions",
        headers=headers,
        json={
            "category_id": category.json()["id"],
            "key": "safe_code",
            "name": "Safe code",
            "field_type": "encrypted_text",
            "privacy_level": "sensitive",
        },
    )

    assert response.status_code == 422


def test_legacy_attribute_privacy_level_is_normalized_in_config_payloads(
    client: TestClient,
    db_session: Session,
) -> None:
    headers = login(client)
    category = client.post(
        "/api/config/categories",
        headers=headers,
        json={"code": "documents", "name": "Documents"},
    )
    assert category.status_code == 201
    field = client.post(
        "/api/config/attribute-definitions",
        headers=headers,
        json={
            "category_id": category.json()["id"],
            "key": "serial_number",
            "name": "Serial number",
            "field_type": "text",
        },
    )
    assert field.status_code == 201
    definition = db_session.get(AttributeDefinition, field.json()["id"])
    assert definition is not None
    definition.privacy_level = "encrypted"
    db_session.commit()

    bootstrap = client.get("/api/config/bootstrap", headers=headers)
    categories = client.get("/api/config/categories", headers=headers)

    assert bootstrap.status_code == 200
    assert categories.status_code == 200
    assert bootstrap.json()["categories"][0]["attribute_definitions"][0]["privacy_level"] == "sensitive"
    assert categories.json()[0]["attribute_definitions"][0]["privacy_level"] == "sensitive"


def test_attribute_options_are_returned_with_category_attribute_definitions(
    client: TestClient,
    db_session: Session,
) -> None:
    headers = login(client)
    category = client.post(
        "/api/config/categories",
        headers=headers,
        json={"code": "documents", "name": "Documents"},
    ).json()
    field = client.post(
        "/api/config/attribute-definitions",
        headers=headers,
        json={
            "category_id": category["id"],
            "key": "retention",
            "name": "Retention",
            "field_type": "single_select",
        },
    ).json()
    db_session.add(
        AttributeOption(
            definition_id=field["id"],
            label="Long term",
            value="long_term",
            sort_order=10,
            is_active=True,
        )
    )
    db_session.commit()

    response = client.get("/api/config/categories", headers=headers)

    assert response.status_code == 200
    assert response.json()[0]["attribute_definitions"][0]["options"] == [
        {
            "id": 1,
            "definition_id": field["id"],
            "label": "Long term",
            "value": "long_term",
            "sort_order": 10,
            "is_active": True,
        }
    ]


def test_dictionaries_alias_returns_seeded_groups(client: TestClient) -> None:
    response = client.get("/api/config/dictionaries", headers=login(client))

    assert response.status_code == 200
    assert {"units", "importance", "location_node_types"}.issubset(
        {group["code"] for group in response.json()}
    )


def test_admin_can_use_backend_configuration_write_contract_routes(client: TestClient) -> None:
    headers = login(client)

    home_space = client.put(
        "/api/config/home-space",
        headers=headers,
        json={"name": "Primary home", "description": "Configuration owner"},
    )
    assert home_space.status_code == 200
    assert home_space.json()["name"] == "Primary home"

    residence = client.post(
        "/api/config/residences",
        headers=headers,
        json={"name": "Residence one", "description": "", "address": "", "sort_order": 10},
    )
    assert residence.status_code == 201
    residence_id = residence.json()["id"]
    residence_update = client.patch(
        f"/api/config/residences/{residence_id}",
        headers=headers,
        json={
            "name": "Residence main",
            "description": "Updated",
            "address": "Updated address",
            "sort_order": 20,
            "is_active": True,
        },
    )
    assert residence_update.status_code == 200
    assert residence_update.json()["name"] == "Residence main"

    location = client.post(
        "/api/config/location-nodes",
        headers=headers,
        json={"residence_id": residence_id, "name": "Room one", "node_type": "room"},
    )
    assert location.status_code == 201
    location_id = location.json()["id"]
    location_update = client.patch(
        f"/api/config/location-nodes/{location_id}",
        headers=headers,
        json={
            "parent_id": None,
            "name": "Room main",
            "node_type": "room",
            "icon": "room",
            "sort_order": 30,
            "note": "Updated",
            "is_active": True,
        },
    )
    assert location_update.status_code == 200
    assert location_update.json()["name"] == "Room main"

    member = client.post(
        "/api/config/family-members",
        headers=headers,
        json={"name": "Alex", "relation": "Owner", "phone": "", "note": ""},
    )
    assert member.status_code == 201
    member_id = member.json()["id"]
    member_update = client.patch(
        f"/api/config/family-members/{member_id}",
        headers=headers,
        json={"name": "Alex Chen", "relation": "Owner", "phone": "123", "note": "Updated", "is_active": True},
    )
    assert member_update.status_code == 200
    assert member_update.json()["phone"] == "123"

    category = client.post(
        "/api/config/categories",
        headers=headers,
        json={"code": "documents", "name": "Documents"},
    )
    assert category.status_code == 201
    category_id = category.json()["id"]
    category_update = client.patch(
        f"/api/config/categories/{category_id}",
        headers=headers,
        json={"parent_id": None, "name": "Important documents", "icon": "document", "sort_order": 40, "is_active": True},
    )
    assert category_update.status_code == 200
    assert category_update.json()["name"] == "Important documents"

    field = client.post(
        "/api/config/attribute-definitions",
        headers=headers,
        json={"category_id": category_id, "key": "expire_date", "name": "Expire date", "field_type": "date"},
    )
    assert field.status_code == 201
    field_id = field.json()["id"]
    field_update = client.patch(
        f"/api/config/attribute-definitions/{field_id}",
        headers=headers,
        json={
            "name": "Expiration date",
            "field_type": "date",
            "default_value": "",
            "privacy_level": "normal",
            "is_required": True,
            "is_filterable": True,
            "sort_order": 50,
            "is_active": True,
        },
    )
    assert field_update.status_code == 200
    assert field_update.json()["is_required"] is True

    attribute_option = client.post(
        "/api/config/attribute-options",
        headers=headers,
        json={"definition_id": field_id, "label": "Long term", "value": "long_term", "sort_order": 10},
    )
    assert attribute_option.status_code == 201
    attribute_option_update = client.patch(
        f"/api/config/attribute-options/{attribute_option.json()['id']}",
        headers=headers,
        json={"label": "Permanent", "sort_order": 20, "is_active": True},
    )
    assert attribute_option_update.status_code == 200
    assert attribute_option_update.json()["label"] == "Permanent"

    status_response = client.post(
        "/api/config/item-statuses",
        headers=headers,
        json={"code": "reserved", "name": "Reserved", "semantic": "available", "sort_order": 80},
    )
    assert status_response.status_code == 201
    status_update = client.patch(
        f"/api/config/item-statuses/{status_response.json()['id']}",
        headers=headers,
        json={"name": "Reserved now", "semantic": "available", "sort_order": 90, "is_active": True},
    )
    assert status_update.status_code == 200
    assert status_update.json()["name"] == "Reserved now"


def test_dictionary_groups_and_options_cannot_be_created(client: TestClient) -> None:
    headers = login(client)
    bootstrap = client.get("/api/config/bootstrap", headers=headers)
    assert bootstrap.status_code == 200
    importance = next(group for group in bootstrap.json()["dictionary_groups"] if group["code"] == "importance")

    dictionary_group = client.post(
        "/api/config/dictionary-groups",
        headers=headers,
        json={"code": "colors", "name": "Colors"},
    )
    assert dictionary_group.status_code in {404, 405}

    dictionary_option = client.post(
        "/api/config/dictionary-options",
        headers=headers,
        json={"group_id": importance["id"], "label": "Red", "value": "red", "sort_order": 10},
    )
    assert dictionary_option.status_code in {404, 405}


def test_admin_updates_existing_dictionary_option_and_writes_audit_log(
    client: TestClient,
    db_session: Session,
) -> None:
    headers = login(client)
    bootstrap = client.get("/api/config/bootstrap", headers=headers)
    assert bootstrap.status_code == 200
    importance = next(group for group in bootstrap.json()["dictionary_groups"] if group["code"] == "importance")
    option = next(item for item in importance["options"] if item["value"] == "high")

    response = client.patch(
        f"/api/config/dictionary-options/{option['id']}",
        headers=headers,
        json={"label": "High value", "sort_order": 5, "is_active": False},
    )

    assert response.status_code == 200
    assert response.json()["value"] == "high"
    assert response.json()["label"] == "High value"
    assert response.json()["sort_order"] == 5
    assert response.json()["is_active"] is False

    log = db_session.scalar(select(AuditLog).where(AuditLog.action == "config.dictionary_option.update"))
    assert log is not None
    assert log.actor_username == "admin"
    assert log.resource_type == "dictionary_option"
    assert log.resource_id == str(option["id"])
    assert log.resource_label == "high"
    assert log.metadata_json == {
        "group_code": "importance",
        "changed_fields": ["label", "sort_order", "is_active"],
        "is_active": False,
    }


def test_dictionary_option_value_and_group_are_not_editable(
    client: TestClient,
    db_session: Session,
) -> None:
    headers = login(client)
    bootstrap = client.get("/api/config/bootstrap", headers=headers)
    assert bootstrap.status_code == 200
    importance = next(group for group in bootstrap.json()["dictionary_groups"] if group["code"] == "importance")
    option = next(item for item in importance["options"] if item["value"] == "medium")

    response = client.patch(
        f"/api/config/dictionary-options/{option['id']}",
        headers=headers,
        json={"label": "\u4e2d", "value": "changed", "group_id": 999, "sort_order": 20, "is_active": True},
    )

    assert response.status_code == 200
    assert response.json()["value"] == "medium"
    assert response.json()["group_id"] == option["group_id"]
    db_option = db_session.get(DictionaryOption, option["id"])
    assert db_option is not None
    assert db_option.value == "medium"
    assert db_option.group_id == option["group_id"]


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


def test_location_node_type_must_use_enabled_dictionary_option(
    client: TestClient,
    db_session: Session,
) -> None:
    headers = login(client)
    bootstrap = client.get("/api/config/bootstrap", headers=headers)
    location_group = next(
        group for group in bootstrap.json()["dictionary_groups"] if group["code"] == "location_node_types"
    )
    room_option_id = next(option["id"] for option in location_group["options"] if option["value"] == "room")

    response = client.post(
        "/api/config/residences",
        headers=headers,
        json={"name": "Main", "description": "", "address": "", "sort_order": 1},
    )
    assert response.status_code == 201
    residence_id = response.json()["id"]

    unknown = client.post(
        "/api/config/location-nodes",
        headers=headers,
        json={"residence_id": residence_id, "name": "Unknown", "node_type": "drawer"},
    )
    assert unknown.status_code == 400

    disable = client.patch(
        f"/api/config/dictionary-options/{room_option_id}",
        headers=headers,
        json={"label": "\u623f\u95f4", "sort_order": 10, "is_active": False},
    )
    assert disable.status_code == 200

    disabled = client.post(
        "/api/config/location-nodes",
        headers=headers,
        json={"residence_id": residence_id, "name": "Bedroom", "node_type": "room"},
    )
    assert disabled.status_code == 400


def test_location_update_allows_unchanged_disabled_node_type(
    client: TestClient,
    db_session: Session,
) -> None:
    headers = login(client)
    residence = client.post(
        "/api/config/residences",
        headers=headers,
        json={"name": "Main", "description": "", "address": "", "sort_order": 1},
    )
    assert residence.status_code == 201
    location = client.post(
        "/api/config/location-nodes",
        headers=headers,
        json={"residence_id": residence.json()["id"], "name": "Bedroom", "node_type": "room"},
    )
    assert location.status_code == 201

    bootstrap = client.get("/api/config/bootstrap", headers=headers)
    location_group = next(
        group for group in bootstrap.json()["dictionary_groups"] if group["code"] == "location_node_types"
    )
    room_option_id = next(option["id"] for option in location_group["options"] if option["value"] == "room")
    disable = client.patch(
        f"/api/config/dictionary-options/{room_option_id}",
        headers=headers,
        json={"label": "\u623f\u95f4", "sort_order": 10, "is_active": False},
    )
    assert disable.status_code == 200

    unchanged = client.patch(
        f"/api/config/location-nodes/{location.json()['id']}",
        headers=headers,
        json={
            "parent_id": None,
            "name": "Bedroom updated",
            "node_type": "room",
            "icon": "",
            "sort_order": 5,
            "note": "",
            "is_active": True,
        },
    )
    assert unchanged.status_code == 200
    assert unchanged.json()["node_type"] == "room"


def test_configuration_payloads_include_soft_delete_flags(client: TestClient) -> None:
    headers = login(client)

    residence = client.post(
        "/api/config/residences",
        headers=headers,
        json={"name": "Soft Delete Home", "description": "", "address": ""},
    )
    assert residence.status_code == 201
    location = client.post(
        "/api/config/location-nodes",
        headers=headers,
        json={"residence_id": residence.json()["id"], "name": "Soft Delete Shelf", "node_type": "shelf"},
    )
    member = client.post(
        "/api/config/family-members",
        headers=headers,
        json={"name": "Soft Delete Member", "relation": "Owner", "phone": "", "note": ""},
    )

    assert residence.json()["is_deleted"] is False
    assert location.status_code == 201
    assert location.json()["is_deleted"] is False
    assert member.status_code == 201
    assert member.json()["is_deleted"] is False


def test_config_delete_endpoints_hide_records_and_write_audit_logs(
    client: TestClient,
    db_session: Session,
) -> None:
    headers = login(client)
    residence = client.post(
        "/api/config/residences",
        headers=headers,
        json={"name": "Delete Home", "description": "", "address": ""},
    )
    assert residence.status_code == 201
    residence_id = residence.json()["id"]
    parent = client.post(
        "/api/config/location-nodes",
        headers=headers,
        json={"residence_id": residence_id, "name": "Parent Shelf", "node_type": "shelf"},
    )
    child = client.post(
        "/api/config/location-nodes",
        headers=headers,
        json={"residence_id": residence_id, "parent_id": parent.json()["id"], "name": "Child Box", "node_type": "box"},
    )
    member = client.post(
        "/api/config/family-members",
        headers=headers,
        json={"name": "Deleted Member", "relation": "Owner", "phone": "", "note": ""},
    )
    assert parent.status_code == 201
    assert child.status_code == 201
    assert member.status_code == 201

    member_delete = client.delete(f"/api/config/family-members/{member.json()['id']}", headers=headers)
    location_delete = client.delete(f"/api/config/location-nodes/{parent.json()['id']}", headers=headers)
    residence_delete = client.delete(f"/api/config/residences/{residence_id}", headers=headers)
    bootstrap = client.get("/api/config/bootstrap", headers=headers)

    assert member_delete.status_code == 200
    assert member_delete.json()["is_deleted"] is True
    assert location_delete.status_code == 200
    assert location_delete.json()["is_deleted"] is True
    assert residence_delete.status_code == 200
    assert residence_delete.json()["is_deleted"] is True
    assert bootstrap.status_code == 200
    assert all(item["id"] != residence_id for item in bootstrap.json()["residences"])
    assert all(item["id"] != member.json()["id"] for item in bootstrap.json()["family_members"])
    assert all(item["id"] != parent.json()["id"] for item in bootstrap.json()["location_tree"])

    audit_actions = {
        log.action
        for log in db_session.scalars(select(AuditLog).where(AuditLog.action.like("config.%.delete"))).all()
    }
    assert audit_actions == {
        "config.family_member.delete",
        "config.location.delete",
        "config.residence.delete",
    }


def test_config_delete_blocks_active_inventory_references(client: TestClient) -> None:
    headers = login(client)
    residence = client.post(
        "/api/config/residences",
        headers=headers,
        json={"name": "Blocked Home", "description": "", "address": ""},
    )
    assert residence.status_code == 201
    location = client.post(
        "/api/config/location-nodes",
        headers=headers,
        json={"residence_id": residence.json()["id"], "name": "Blocked Shelf", "node_type": "shelf"},
    )
    assert location.status_code == 201
    member = client.post(
        "/api/config/family-members",
        headers=headers,
        json={"name": "Blocked Member", "relation": "Owner", "phone": "", "note": ""},
    )
    assert member.status_code == 201
    category = client.post(
        "/api/config/categories",
        headers=headers,
        json={"code": "blocked_documents", "name": "Blocked Documents", "icon": "document", "sort_order": 10},
    )
    assert category.status_code == 201
    bootstrap = client.get("/api/config/bootstrap", headers=headers).json()
    status_id = next(status["id"] for status in bootstrap["item_statuses"] if status["code"] == "in_stock")

    item = client.post(
        "/api/items",
        headers=headers,
        json={
            "name": "Referenced Item",
            "category_id": category.json()["id"],
            "status_id": status_id,
            "quantity": "1",
            "unit": "pcs",
            "owner_member_id": member.json()["id"],
            "keeper_member_id": member.json()["id"],
            "location_node_id": location.json()["id"],
            "is_container": False,
            "privacy_level": "normal",
            "attribute_values": [],
            "tags": [],
        },
    )
    assert item.status_code == 201

    location_delete = client.delete(f"/api/config/location-nodes/{location.json()['id']}", headers=headers)
    residence_delete = client.delete(f"/api/config/residences/{residence.json()['id']}", headers=headers)

    assert location_delete.status_code == 400
    assert "物品" in location_delete.json()["message"]
    assert residence_delete.status_code == 400
    assert "物品" in residence_delete.json()["message"]
