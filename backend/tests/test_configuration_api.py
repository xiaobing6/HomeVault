from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.core.security import hash_password
from app.main import app
from app.models import AuditLog
from app.models.auth import Role, User
from app.models.configuration import AttributeDefinition, AttributeOption
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
    assert {"units", "importance", "storage_conditions"}.issubset(
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

    dictionary_group = client.post(
        "/api/config/dictionary-groups",
        headers=headers,
        json={"code": "colors", "name": "Colors"},
    )
    assert dictionary_group.status_code == 201
    dictionary_option = client.post(
        "/api/config/dictionary-options",
        headers=headers,
        json={"group_id": dictionary_group.json()["id"], "label": "Red", "value": "red", "sort_order": 10},
    )
    assert dictionary_option.status_code == 201
    assert dictionary_option.json()["value"] == "red"


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
