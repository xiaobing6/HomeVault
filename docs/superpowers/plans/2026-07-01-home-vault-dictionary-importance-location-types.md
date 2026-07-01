# HomeVault Dictionary Importance And Location Types Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make item importance and location node types dictionary-backed while keeping dictionary management limited to editing existing options.

**Architecture:** Add a small backend dictionary helper for active-option validation and label lookup, then reuse it from configuration, inventory, import, and export services. The backend owns data validity through seed/migration and service validation; the frontend reads bootstrap dictionary groups for selects, labels, filters, and dictionary option editing.

**Tech Stack:** FastAPI, SQLAlchemy, Alembic, Pydantic, pytest, Vue 3, Pinia, Element Plus, TypeScript, Vite.

---

## File Structure

Backend:

- Create `backend/app/services/dictionaries.py`: shared dictionary lookup, active-value validation, and label maps.
- Create `backend/alembic/versions/20260701_0009_item_importance_and_dictionary_options.py`: add `items.importance`, seed core dictionary options, remove system `storage_conditions`.
- Modify `backend/app/models/inventory.py`: add `Item.importance`.
- Modify `backend/app/schemas/configuration.py`: add `DictionaryOptionUpdate`.
- Modify `backend/app/schemas/inventory.py`: add item importance to create/update/list/detail/filter.
- Modify `backend/app/services/configuration.py`: seed dictionary options, remove core storage conditions, update dictionary options, validate location node type, and audit dictionary option edits.
- Modify `backend/app/api/routes/configuration.py`: add `PATCH /api/config/dictionary-options/{option_id}` and pass actors for location updates.
- Modify `backend/app/services/inventory.py`: validate item importance, serialize it, filter it, export it, and audit changes.
- Modify `backend/app/services/inventory_import.py`: add `importance` to import template, preview, normalization, and confirmation payloads.
- Modify `backend/tests/test_configuration_seed.py`: core dictionary seed coverage.
- Modify `backend/tests/test_configuration_api.py`: dictionary option editing and location type validation.
- Modify `backend/tests/test_database_models.py`: item importance model/migration coverage.
- Modify `backend/tests/test_inventory_api.py`: importance API/filter/export/import/audit coverage.

Frontend:

- Modify `frontend/src/api/configuration.ts`: dictionary option update payload and API helper.
- Modify `frontend/src/api/inventory.ts`: add `importance` to item types, filters, create, and update payloads.
- Modify `frontend/src/stores/configuration.ts`: dictionary option update action.
- Create `frontend/src/utils/dictionaries.ts`: dictionary option lookup, active option filtering, and label fallback helpers.
- Modify `frontend/src/components/config/DictionaryPanel.vue`: edit existing dictionary options; no create/delete controls.
- Modify `frontend/src/components/config/ResidenceLocationPanel.vue`: read location type options from `location_node_types`.
- Modify `frontend/src/components/items/ItemFormDrawer.vue`: add item importance select.
- Modify `frontend/src/components/items/ItemDetailModal.vue`: show item importance.
- Modify `frontend/src/components/items/ItemTable.vue`: show item importance.
- Modify `frontend/src/components/items/ItemFilterPanel.vue`: add importance filter.
- Modify `frontend/tests/config-management-contract.ts`: dictionary option update contract.
- Modify `frontend/tests/config-management-ui-contract.mjs`: dictionary edit controls and dictionary-backed location type checks.
- Create `frontend/tests/item-importance-ui-contract.mjs`: source-level item importance UI checks.

## Task 1: Backend Core Dictionary Seed And Option Editing

**Files:**
- Create: `backend/app/services/dictionaries.py`
- Modify: `backend/app/schemas/configuration.py`
- Modify: `backend/app/services/configuration.py`
- Modify: `backend/app/api/routes/configuration.py`
- Modify: `backend/tests/test_configuration_seed.py`
- Modify: `backend/tests/test_configuration_api.py`

- [ ] **Step 1: Write failing seed and dictionary option API tests**

Modify `backend/tests/test_configuration_seed.py` to assert the new core dictionary set and default options:

```python
from sqlalchemy.orm import selectinload


def test_core_configuration_seed_creates_dictionary_options_and_removes_storage_conditions(
    db_session: Session,
) -> None:
    ensure_core_configuration_seed(db_session)

    groups = db_session.scalars(
        select(DictionaryGroup)
        .options(selectinload(DictionaryGroup.options))
        .order_by(DictionaryGroup.code)
    ).all()
    groups_by_code = {group.code: group for group in groups}

    assert "storage_conditions" not in groups_by_code
    assert {"units", "importance", "location_node_types"}.issubset(groups_by_code)
    assert [(option.value, option.label, option.sort_order) for option in groups_by_code["importance"].options] == [
        ("high", "\u9ad8", 10),
        ("medium", "\u4e2d", 20),
        ("low", "\u4f4e", 30),
    ]
    assert [option.value for option in groups_by_code["location_node_types"].options] == [
        "room",
        "area",
        "cabinet",
        "shelf",
        "box",
        "other",
    ]
    assert groups_by_code["units"].options[0].value == "\u4ef6"
```

Update the existing `test_core_configuration_seed_is_idempotent` assertion from:

```python
assert {"units", "importance", "storage_conditions"}.issubset({group.code for group in groups})
```

to:

```python
assert {"units", "importance", "location_node_types"}.issubset({group.code for group in groups})
assert "storage_conditions" not in {group.code for group in groups}
```

Append to `backend/tests/test_configuration_api.py`:

```python
from app.models.configuration import DictionaryGroup


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


def test_dictionary_option_value_and_group_are_not_editable(client: TestClient) -> None:
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
```

- [ ] **Step 2: Run tests and verify RED**

Run from `backend`:

```powershell
python -m pytest tests/test_configuration_seed.py::test_core_configuration_seed_creates_dictionary_options_and_removes_storage_conditions tests/test_configuration_api.py::test_admin_updates_existing_dictionary_option_and_writes_audit_log tests/test_configuration_api.py::test_dictionary_option_value_and_group_are_not_editable -q
```

Expected: failures because seeded options and the patch endpoint do not exist yet.

- [ ] **Step 3: Create shared dictionary helper**

Create `backend/app/services/dictionaries.py`:

```python
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.errors import bad_request
from app.models.configuration import DictionaryGroup, DictionaryOption


def get_dictionary_group(db: Session, code: str) -> DictionaryGroup:
    group = db.scalar(
        select(DictionaryGroup)
        .where(DictionaryGroup.code == code, DictionaryGroup.is_active.is_(True))
        .options(selectinload(DictionaryGroup.options))
    )
    if group is None:
        raise bad_request("Dictionary group not found")
    return group


def get_active_dictionary_option(
    db: Session,
    group_code: str,
    value: str,
) -> DictionaryOption | None:
    return db.scalar(
        select(DictionaryOption)
        .join(DictionaryGroup)
        .where(
            DictionaryGroup.code == group_code,
            DictionaryGroup.is_active.is_(True),
            DictionaryOption.value == value,
            DictionaryOption.is_active.is_(True),
        )
        .order_by(DictionaryOption.sort_order, DictionaryOption.id)
    )


def require_active_dictionary_value(
    db: Session,
    group_code: str,
    value: str,
    *,
    message: str,
    allow_existing_value: str | None = None,
) -> str:
    normalized = value.strip()
    if allow_existing_value is not None and normalized == allow_existing_value:
        return normalized
    if get_active_dictionary_option(db, group_code, normalized) is None:
        raise bad_request(message)
    return normalized


def dictionary_label_map(db: Session, group_code: str) -> dict[str, str]:
    group = get_dictionary_group(db, group_code)
    return {
        option.value: option.label
        for option in sorted(group.options, key=lambda item: (item.sort_order, item.id))
    }
```

- [ ] **Step 4: Seed core groups and options**

Modify `backend/app/services/configuration.py` constants:

```python
CORE_DICTIONARY_GROUPS = [
    (
        "units",
        "\u5355\u4f4d",
        [
            ("\u4ef6", "\u4ef6", 10),
            ("\u4e2a", "\u4e2a", 20),
            ("\u7bb1", "\u7bb1", 30),
            ("\u5957", "\u5957", 40),
        ],
    ),
    (
        "importance",
        "\u91cd\u8981\u7a0b\u5ea6",
        [
            ("high", "\u9ad8", 10),
            ("medium", "\u4e2d", 20),
            ("low", "\u4f4e", 30),
        ],
    ),
    (
        "location_node_types",
        "\u4f4d\u7f6e\u7c7b\u578b",
        [
            ("room", "\u623f\u95f4", 10),
            ("area", "\u533a\u57df", 20),
            ("cabinet", "\u67dc\u5b50", 30),
            ("shelf", "\u67b6\u5b50", 40),
            ("box", "\u7bb1/\u76d2", 50),
            ("other", "\u5176\u4ed6", 60),
        ],
    ),
]
```

Modify `ensure_core_configuration_seed` so each tuple unpacks `code, name, options`. Inside the group loop, insert missing options without changing existing labels:

```python
    storage_group = db.scalar(
        select(DictionaryGroup).where(
            DictionaryGroup.code == "storage_conditions",
            DictionaryGroup.is_system.is_(True),
        )
    )
    if storage_group is not None:
        db.delete(storage_group)

    for code, name, options in CORE_DICTIONARY_GROUPS:
        group = db.scalar(select(DictionaryGroup).where(DictionaryGroup.code == code))
        if group is None:
            group = DictionaryGroup(code=code, name=name, is_system=True, is_active=True)
            db.add(group)
            db.flush()
        else:
            group.name = name
            group.is_system = True
            group.is_active = True

        existing_options = {
            option.value: option
            for option in db.scalars(select(DictionaryOption).where(DictionaryOption.group_id == group.id)).all()
        }
        for value, label, sort_order in options:
            if value not in existing_options:
                db.add(
                    DictionaryOption(
                        group_id=group.id,
                        label=label,
                        value=value,
                        sort_order=sort_order,
                        is_active=True,
                    )
                )
```

Update dictionary group queries that unpack `CORE_DICTIONARY_GROUPS`:

```python
[code for code, _name, _options in CORE_DICTIONARY_GROUPS]
```

- [ ] **Step 5: Add dictionary option update schema, service, and route**

Modify `backend/app/schemas/configuration.py` after `DictionaryOptionCreate`:

```python
class DictionaryOptionUpdate(BaseModel):
    label: str = Field(min_length=1, max_length=120)
    sort_order: int = 0
    is_active: bool = True
```

Modify imports in `backend/app/services/configuration.py` to include `DictionaryOptionUpdate`.

Add this service to `backend/app/services/configuration.py` after `create_dictionary_option`:

```python
def update_dictionary_option(
    db: Session,
    option_id: int,
    payload: DictionaryOptionUpdate,
    actor: User | None = None,
) -> DictionaryOptionResponse:
    option = db.get(DictionaryOption, option_id)
    if option is None:
        raise bad_request("Dictionary option not found")

    group = option.group
    changed_fields: list[str] = []
    if option.label != payload.label:
        changed_fields.append("label")
    if option.sort_order != payload.sort_order:
        changed_fields.append("sort_order")
    if option.is_active != payload.is_active:
        changed_fields.append("is_active")

    option.label = payload.label
    option.sort_order = payload.sort_order
    option.is_active = payload.is_active
    record_audit_log(
        db,
        action="config.dictionary_option.update",
        resource_type="dictionary_option",
        actor=actor,
        resource_id=option.id,
        resource_label=option.value,
        metadata={
            "group_code": group.code if group is not None else None,
            "changed_fields": changed_fields,
            "is_active": option.is_active,
        },
    )
    db.commit()
    db.refresh(option)
    return DictionaryOptionResponse.model_validate(option)
```

Modify `backend/app/api/routes/configuration.py` imports and add:

```python
@router.patch("/dictionary-options/{option_id}", response_model=DictionaryOptionResponse)
def update_dictionary_option(
    option_id: int,
    payload: DictionaryOptionUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("config:manage")),
) -> DictionaryOptionResponse:
    return update_dictionary_option_record(db, option_id, payload, actor=user)
```

- [ ] **Step 6: Run focused tests and verify GREEN**

Run from `backend`:

```powershell
python -m pytest tests/test_configuration_seed.py::test_core_configuration_seed_is_idempotent tests/test_configuration_seed.py::test_core_configuration_seed_creates_dictionary_options_and_removes_storage_conditions tests/test_configuration_api.py::test_admin_updates_existing_dictionary_option_and_writes_audit_log tests/test_configuration_api.py::test_dictionary_option_value_and_group_are_not_editable -q
```

Expected: 4 passed.

- [ ] **Step 7: Commit Task 1**

```powershell
git add backend/app/services/dictionaries.py backend/app/schemas/configuration.py backend/app/services/configuration.py backend/app/api/routes/configuration.py backend/tests/test_configuration_seed.py backend/tests/test_configuration_api.py
git commit -m "feat: manage existing dictionary options"
```

## Task 2: Backend Location Node Type Validation

**Files:**
- Modify: `backend/app/services/configuration.py`
- Modify: `backend/app/api/routes/configuration.py`
- Modify: `backend/tests/test_configuration_api.py`

- [ ] **Step 1: Write failing location type validation tests**

Append to `backend/tests/test_configuration_api.py`:

```python
def test_location_node_type_must_use_enabled_dictionary_option(
    client: TestClient,
    db_session: Session,
) -> None:
    headers = login(client)
    bootstrap = client.get("/api/config/bootstrap", headers=headers)
    location_group = next(group for group in bootstrap.json()["dictionary_groups"] if group["code"] == "location_node_types")
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
    location_group = next(group for group in bootstrap.json()["dictionary_groups"] if group["code"] == "location_node_types")
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
```

- [ ] **Step 2: Run tests and verify RED**

Run from `backend`:

```powershell
python -m pytest tests/test_configuration_api.py::test_location_node_type_must_use_enabled_dictionary_option tests/test_configuration_api.py::test_location_update_allows_unchanged_disabled_node_type -q
```

Expected: FAIL because location node type accepts arbitrary strings.

- [ ] **Step 3: Validate create and update through dictionary helper**

Modify `backend/app/services/configuration.py` imports:

```python
from app.services.dictionaries import require_active_dictionary_value
```

Add constants near `ACTIVE_RESIDENCE_NAME_EXISTS_MESSAGE`:

```python
LOCATION_NODE_TYPE_GROUP = "location_node_types"
LOCATION_NODE_TYPE_INVALID_MESSAGE = "\u4f4d\u7f6e\u7c7b\u578b\u4e0d\u5408\u6cd5"
```

In `create_location_node`, validate before constructing `LocationNode`:

```python
    node_type = require_active_dictionary_value(
        db,
        LOCATION_NODE_TYPE_GROUP,
        payload.node_type,
        message=LOCATION_NODE_TYPE_INVALID_MESSAGE,
    )
```

Use `node_type=node_type` in the model constructor.

Change `update_location_node` signature:

```python
def update_location_node(
    db: Session,
    node_id: int,
    payload: LocationNodeUpdate,
    actor: User | None = None,
) -> LocationNodeResponse:
```

Validate before assignment:

```python
    node_type = require_active_dictionary_value(
        db,
        LOCATION_NODE_TYPE_GROUP,
        payload.node_type,
        message=LOCATION_NODE_TYPE_INVALID_MESSAGE,
        allow_existing_value=node.node_type,
    )
```

Assign `node.node_type = node_type`.

Modify `backend/app/api/routes/configuration.py` route:

```python
return update_location_node_record(db, node_id, payload, actor=user)
```

- [ ] **Step 4: Run focused tests and verify GREEN**

Run from `backend`:

```powershell
python -m pytest tests/test_configuration_api.py::test_location_node_type_must_use_enabled_dictionary_option tests/test_configuration_api.py::test_location_update_allows_unchanged_disabled_node_type -q
```

Expected: 2 passed.

- [ ] **Step 5: Commit Task 2**

```powershell
git add backend/app/services/configuration.py backend/app/api/routes/configuration.py backend/tests/test_configuration_api.py
git commit -m "feat: validate location types with dictionaries"
```

## Task 3: Backend Item Importance Model, API, Filtering, And Audit

**Files:**
- Create: `backend/alembic/versions/20260701_0009_item_importance_and_dictionary_options.py`
- Modify: `backend/app/models/inventory.py`
- Modify: `backend/app/schemas/inventory.py`
- Modify: `backend/app/services/inventory.py`
- Modify: `backend/tests/test_database_models.py`
- Modify: `backend/tests/test_inventory_api.py`

- [ ] **Step 1: Write failing item importance tests**

Append to `backend/tests/test_inventory_api.py`:

```python
def test_item_importance_create_update_filter_and_audit(
    client: TestClient,
    db_session: Session,
) -> None:
    headers = login(client)
    payload = valid_item_payload(db_session)
    payload["importance"] = "high"

    created = client.post("/api/items", headers=headers, json=payload)
    assert created.status_code == 201
    assert created.json()["importance"] == "high"
    item_id = created.json()["id"]

    listed = client.get("/api/items", headers=headers, params={"importance": "high"})
    assert listed.status_code == 200
    assert [item["id"] for item in listed.json()["items"]] == [item_id]

    updated = client.patch(
        f"/api/items/{item_id}",
        headers=headers,
        json={"importance": "low"},
    )
    assert updated.status_code == 200
    assert updated.json()["importance"] == "low"

    audit_log = db_session.scalar(select(AuditLog).where(AuditLog.action == "item.importance.update"))
    assert audit_log is not None
    assert audit_log.actor_user_id is not None
    assert audit_log.resource_type == "item"
    assert audit_log.resource_id == str(item_id)
    assert audit_log.metadata_json == {"previous_importance": "high", "new_importance": "low"}


def test_item_importance_rejects_unknown_and_disabled_values(
    client: TestClient,
    db_session: Session,
) -> None:
    headers = login(client)
    payload = valid_item_payload(db_session)
    payload["importance"] = "urgent"

    unknown = client.post("/api/items", headers=headers, json=payload)
    assert unknown.status_code == 400

    bootstrap = client.get("/api/config/bootstrap", headers=headers)
    importance = next(group for group in bootstrap.json()["dictionary_groups"] if group["code"] == "importance")
    high = next(option for option in importance["options"] if option["value"] == "high")
    disabled = client.patch(
        f"/api/config/dictionary-options/{high['id']}",
        headers=headers,
        json={"label": "\u9ad8", "sort_order": 10, "is_active": False},
    )
    assert disabled.status_code == 200

    payload["importance"] = "high"
    disabled_create = client.post("/api/items", headers=headers, json=payload)
    assert disabled_create.status_code == 400
```

Append to `backend/tests/test_database_models.py`:

```python
def test_item_importance_defaults_to_medium(db_session: Session) -> None:
    item = make_item(db_session, name="Importance default")

    assert item.importance == "medium"
```

- [ ] **Step 2: Run tests and verify RED**

Run from `backend`:

```powershell
python -m pytest tests/test_database_models.py::test_item_importance_defaults_to_medium tests/test_inventory_api.py::test_item_importance_create_update_filter_and_audit tests/test_inventory_api.py::test_item_importance_rejects_unknown_and_disabled_values -q
```

Expected: failures because `importance` is not on the model, schema, or API.

- [ ] **Step 3: Add database model and migration**

Modify `backend/app/models/inventory.py` inside `class Item` after `unit`:

```python
    importance: Mapped[str] = mapped_column(String(40), default="medium", nullable=False, index=True)
```

Create `backend/alembic/versions/20260701_0009_item_importance_and_dictionary_options.py`:

```python
"""add item importance and core dictionary options

Revision ID: 20260701_0009
Revises: 20260701_0008
Create Date: 2026-07-01 20:30:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "20260701_0009"
down_revision = "20260701_0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "items",
        sa.Column("importance", sa.String(length=40), nullable=False, server_default="medium"),
    )
    op.create_index("ix_items_importance", "items", ["importance"])
    op.alter_column("items", "importance", server_default=None)

    op.execute("DELETE FROM dictionary_groups WHERE code = 'storage_conditions' AND is_system = 1")
    seed_group("units", "\u5355\u4f4d", [("\u4ef6", "\u4ef6", 10), ("\u4e2a", "\u4e2a", 20), ("\u7bb1", "\u7bb1", 30), ("\u5957", "\u5957", 40)])
    seed_group("importance", "\u91cd\u8981\u7a0b\u5ea6", [("high", "\u9ad8", 10), ("medium", "\u4e2d", 20), ("low", "\u4f4e", 30)])
    seed_group("location_node_types", "\u4f4d\u7f6e\u7c7b\u578b", [("room", "\u623f\u95f4", 10), ("area", "\u533a\u57df", 20), ("cabinet", "\u67dc\u5b50", 30), ("shelf", "\u67b6\u5b50", 40), ("box", "\u7bb1/\u76d2", 50), ("other", "\u5176\u4ed6", 60)])


def downgrade() -> None:
    op.drop_index("ix_items_importance", table_name="items")
    op.drop_column("items", "importance")


def seed_group(code: str, name: str, options: list[tuple[str, str, int]]) -> None:
    op.execute(
        sa.text(
            """
            INSERT INTO dictionary_groups (code, name, is_system, is_active)
            SELECT :code, :name, 1, 1
            WHERE NOT EXISTS (SELECT 1 FROM dictionary_groups WHERE code = :code)
            """
        ).bindparams(code=code, name=name)
    )
    for value, label, sort_order in options:
        op.execute(
            sa.text(
                """
                INSERT INTO dictionary_options (group_id, label, value, sort_order, is_active)
                SELECT dictionary_groups.id, :label, :value, :sort_order, 1
                FROM dictionary_groups
                WHERE dictionary_groups.code = :code
                  AND NOT EXISTS (
                    SELECT 1 FROM dictionary_options
                    WHERE dictionary_options.group_id = dictionary_groups.id
                      AND dictionary_options.value = :value
                  )
                """
            ).bindparams(code=code, label=label, value=value, sort_order=sort_order)
        )
```

If SQLite rejects `is_system = 1` on the local migration runner, change the delete predicate to `is_system IS TRUE` after checking the existing migration style.

- [ ] **Step 4: Add schemas and service validation**

Modify `backend/app/schemas/inventory.py`:

```python
class ItemCreate(PlacementPayload):
    ...
    unit: str = "\u4ef6"
    importance: str = Field(default="medium", max_length=40)
```

```python
class ItemUpdate(RequestModel):
    ...
    unit: str | None = None
    importance: str | None = Field(default=None, max_length=40)
```

```python
class ItemListQuery(RequestModel):
    ...
    status_id: int | None = None
    importance: str | None = None
```

```python
class ItemSummaryResponse(ResponseModel):
    ...
    unit: str
    importance: str
```

Modify `backend/app/services/inventory.py` imports:

```python
from app.services.audit import record_audit_log
from app.services.dictionaries import require_active_dictionary_value
```

Add constants near `REDACTED_VALUE`:

```python
IMPORTANCE_GROUP = "importance"
IMPORTANCE_INVALID_MESSAGE = "\u91cd\u8981\u7a0b\u5ea6\u4e0d\u5408\u6cd5"
```

In `create_item_record`, validate before constructing `Item`:

```python
    importance = require_active_dictionary_value(
        db,
        IMPORTANCE_GROUP,
        payload.importance,
        message=IMPORTANCE_INVALID_MESSAGE,
    )
```

Set `importance=importance` on the `Item`.

In `update_item`, add:

```python
    previous_importance = item.importance
    if "importance" in fields and payload.importance is not None:
        item.importance = require_active_dictionary_value(
            db,
            IMPORTANCE_GROUP,
            payload.importance,
            message=IMPORTANCE_INVALID_MESSAGE,
            allow_existing_value=item.importance,
        )
        if item.importance != previous_importance:
            record_audit_log(
                db,
                action="item.importance.update",
                resource_type="item",
                actor_user_id=actor_id,
                resource_id=item.id,
                resource_label=item.name,
                metadata={
                    "previous_importance": previous_importance,
                    "new_importance": item.importance,
                },
            )
```

In `list_items`, after status filtering, add:

```python
    if query.importance is not None:
        stmt = stmt.where(Item.importance == query.importance)
```

In the item response builder, add `importance=item.importance`.

- [ ] **Step 5: Run focused tests and verify GREEN**

Run from `backend`:

```powershell
python -m pytest tests/test_database_models.py::test_item_importance_defaults_to_medium tests/test_inventory_api.py::test_item_importance_create_update_filter_and_audit tests/test_inventory_api.py::test_item_importance_rejects_unknown_and_disabled_values -q
```

Expected: 3 passed.

- [ ] **Step 6: Commit Task 3**

```powershell
git add backend/alembic/versions/20260701_0009_item_importance_and_dictionary_options.py backend/app/models/inventory.py backend/app/schemas/inventory.py backend/app/services/inventory.py backend/tests/test_database_models.py backend/tests/test_inventory_api.py
git commit -m "feat: add dictionary backed item importance"
```

## Task 4: Backend Importance Export And Import

**Files:**
- Modify: `backend/app/services/inventory.py`
- Modify: `backend/app/services/inventory_import.py`
- Modify: `backend/tests/test_inventory_api.py`

- [ ] **Step 1: Write failing export and import tests**

Modify `backend/tests/test_inventory_api.py` export test that asserts the CSV header. Add `"importance"` after `"unit"` in the expected header list.

Append:

```python
def test_inventory_export_outputs_importance_label(
    client: TestClient,
    db_session: Session,
) -> None:
    headers = login(client)
    payload = valid_item_payload(db_session)
    payload["importance"] = "high"
    created = client.post("/api/items", headers=headers, json=payload)
    assert created.status_code == 201

    response = client.post("/api/items/export.csv", headers=headers, json={"item_ids": [created.json()["id"]]})

    assert response.status_code == 200
    assert "importance" in response.text.splitlines()[0].split(",")
    assert "high" not in response.text.splitlines()[1]
    assert "\u9ad8" in response.text.splitlines()[1]


def test_inventory_import_accepts_importance_value_and_label(
    client: TestClient,
) -> None:
    headers = login(client)
    csv_content = "\n".join(
        [
            "name,description,category,status,quantity,unit,importance,owner,keeper,residence,location,container,is_container,privacy_level,tags",
            "High item,From CSV,documents,in_stock,1,pcs,high,Alex,Alex,Main residence,Shelf,,false,normal,",
            "Low item,From CSV,documents,in_stock,1,pcs,\u4f4e,Alex,Alex,Main residence,Shelf,,false,normal,",
        ]
    )

    response = client.post(
        "/api/items/import/preview",
        headers=headers,
        files={"file": ("items.csv", csv_content.encode("utf-8"), "text/csv")},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["invalid_count"] == 0
    assert body["rows"][0]["normalized"]["importance"] == "high"
    assert body["rows"][1]["normalized"]["importance"] == "low"
```

- [ ] **Step 2: Run tests and verify RED**

Run from `backend`:

```powershell
python -m pytest tests/test_inventory_api.py::test_inventory_export_outputs_importance_label tests/test_inventory_api.py::test_inventory_import_accepts_importance_value_and_label -q
```

Expected: failures because import/export do not include importance.

- [ ] **Step 3: Export importance labels**

Modify `backend/app/services/inventory.py` imports:

```python
from app.services.dictionaries import dictionary_label_map, require_active_dictionary_value
```

Add `"importance"` after `"unit"` in `CSV_EXPORT_COLUMNS`.

In `export_items_csv`, load labels once before the row loop:

```python
    importance_labels = dictionary_label_map(db, IMPORTANCE_GROUP)
```

Add the row field:

```python
                "importance": importance_labels.get(detail.importance, detail.importance),
```

- [ ] **Step 4: Import importance values and labels**

Modify `backend/app/services/inventory_import.py` imports:

```python
from app.models.configuration import AttributeDefinition, Category, DictionaryGroup, DictionaryOption, FamilyMember, ItemStatus, LocationNode, Residence
```

Add `"importance"` after `"unit"` in `STATIC_IMPORT_COLUMNS`.

In `build_row_preview`, parse importance after privacy:

```python
    importance = parse_importance(db, original.get("importance", ""), errors)
```

In the normalized payload, add:

```python
            "importance": importance,
```

Add this parser after `parse_privacy_level`:

```python
def parse_importance(db: Session, raw_value: str, errors: list[ImportFieldMessage]) -> str:
    value = raw_value.strip()
    if value == "":
        return "medium"
    option = db.scalar(
        select(DictionaryOption)
        .join(DictionaryGroup)
        .where(
            DictionaryGroup.code == "importance",
            DictionaryGroup.is_active.is_(True),
            DictionaryOption.is_active.is_(True),
            or_(DictionaryOption.value == value, DictionaryOption.label == value),
        )
        .order_by(DictionaryOption.sort_order, DictionaryOption.id)
    )
    if option is None:
        errors.append(field_error("importance", "\u91cd\u8981\u7a0b\u5ea6\u4e0d\u6b63\u786e"))
        return "medium"
    return option.value
```

- [ ] **Step 5: Run focused tests and verify GREEN**

Run from `backend`:

```powershell
python -m pytest tests/test_inventory_api.py::test_inventory_export_outputs_importance_label tests/test_inventory_api.py::test_inventory_import_accepts_importance_value_and_label -q
```

Expected: 2 passed.

- [ ] **Step 6: Commit Task 4**

```powershell
git add backend/app/services/inventory.py backend/app/services/inventory_import.py backend/tests/test_inventory_api.py
git commit -m "feat: include importance in inventory import export"
```

## Task 5: Frontend Dictionary Option Editing And Location Types

**Files:**
- Modify: `frontend/src/api/configuration.ts`
- Modify: `frontend/src/stores/configuration.ts`
- Create: `frontend/src/utils/dictionaries.ts`
- Modify: `frontend/src/components/config/DictionaryPanel.vue`
- Modify: `frontend/src/components/config/ResidenceLocationPanel.vue`
- Modify: `frontend/tests/config-management-contract.ts`
- Modify: `frontend/tests/config-management-ui-contract.mjs`

- [ ] **Step 1: Write failing frontend contracts**

Modify `frontend/tests/config-management-contract.ts` to import and use the dictionary update type/action:

```ts
import type { DictionaryOptionUpdate } from '../src/api/configuration'

const dictionaryPayload: DictionaryOptionUpdate = {
  label: 'High value',
  sort_order: 5,
  is_active: false
}

void configuration.updateDictionaryOption(1, dictionaryPayload)
```

Modify `frontend/tests/config-management-ui-contract.mjs`. Replace the read-only assertion:

```js
assert.doesNotMatch(
  dictionaryPanel,
  /updateDictionary(Group|Option)|dictionary(Group|Option)EditOpen|openDictionary(Group|Option)Edit|dictionaryEditOpen|openDictionaryEdit/,
  'Dictionary groups and dictionary options should remain read-only in this slice'
)
```

with:

```js
assert.match(
  dictionaryPanel,
  /configuration\.updateDictionaryOption\(\s*editingDictionaryOption\.value\.id/,
  'Dictionary panel should update existing dictionary options'
)
assert.match(
  dictionaryPanel,
  /<el-switch[\s\S]*v-model="dictionaryOptionEditForm\.is_active"/,
  'Dictionary option edit dialog should expose active state'
)
assert.doesNotMatch(
  dictionaryPanel,
  /configuration\.createDictionaryOption|configuration\.createDictionaryGroup|deleteDictionaryOption|deleteDictionaryGroup/,
  'Dictionary panel should not expose dictionary create or delete controls'
)
assert.match(
  residenceLocationPanel,
  /locationNodeTypeOptions/,
  'Location panel should compute location type options from dictionaries'
)
assert.doesNotMatch(
  residenceLocationPanel,
  /const\s+locationTypes\s*=\s*\[/,
  'Location type options should not be hard-coded in the location panel'
)
```

- [ ] **Step 2: Run tests and verify RED**

Run from `frontend`:

```powershell
.\node_modules\.bin\vue-tsc.cmd --noEmit -p tsconfig.contract.json
node .\tests\config-management-ui-contract.mjs
```

Expected: type check or UI contract fails because dictionary option update and location dictionary options are missing.

- [ ] **Step 3: Add API/store support and dictionary utilities**

Modify `frontend/src/api/configuration.ts`:

```ts
export interface DictionaryOptionUpdate {
  label: string
  sort_order: number
  is_active: boolean
}

export async function updateDictionaryOptionApi(
  optionId: number,
  payload: DictionaryOptionUpdate
): Promise<DictionaryOption> {
  const response = await apiClient.patch<DictionaryOption>(`/config/dictionary-options/${optionId}`, payload)
  return response.data
}
```

Modify `frontend/src/stores/configuration.ts` imports and actions:

```ts
  updateDictionaryOptionApi,
  type DictionaryOptionUpdate,
```

```ts
    async updateDictionaryOption(optionId: number, payload: DictionaryOptionUpdate) {
      await updateDictionaryOptionApi(optionId, payload)
      await this.load()
    },
```

Create `frontend/src/utils/dictionaries.ts`:

```ts
import type { ConfigBootstrap, DictionaryOption } from '../api/configuration'

export function dictionaryOptions(
  data: ConfigBootstrap | null | undefined,
  groupCode: string,
  includeInactive = false
): DictionaryOption[] {
  const group = data?.dictionary_groups.find((item) => item.code === groupCode)
  return (group?.options ?? [])
    .filter((option) => includeInactive || option.is_active)
    .slice()
    .sort((first, second) => first.sort_order - second.sort_order || first.id - second.id)
}

export function dictionaryLabel(
  data: ConfigBootstrap | null | undefined,
  groupCode: string,
  value: string | null | undefined
): string {
  if (!value) return '-'
  return dictionaryOptions(data, groupCode, true).find((option) => option.value === value)?.label ?? value
}
```

- [ ] **Step 4: Add dictionary option edit UI**

Modify `frontend/src/components/config/DictionaryPanel.vue`:

```ts
import type { DictionaryOption, ItemStatus } from '../../api/configuration'
```

Add state:

```ts
const dictionaryOptionEditFormRef = ref<FormInstance>()
const dictionaryOptionEditOpen = ref(false)
const dictionaryOptionEditSaving = ref(false)
const editingDictionaryOption = ref<DictionaryOption | null>(null)

const dictionaryOptionEditForm = reactive({
  label: '',
  sort_order: 0,
  is_active: true
})
```

Add functions:

```ts
function openDictionaryOptionEdit(option: DictionaryOption) {
  editingDictionaryOption.value = option
  Object.assign(dictionaryOptionEditForm, {
    label: option.label,
    sort_order: option.sort_order,
    is_active: option.is_active
  })
  dictionaryOptionEditOpen.value = true
}

function clearDictionaryOptionEdit() {
  editingDictionaryOption.value = null
  Object.assign(dictionaryOptionEditForm, { label: '', sort_order: 0, is_active: true })
}

async function updateDictionaryOption() {
  dictionaryOptionEditForm.label = dictionaryOptionEditForm.label.trim()
  const valid = await validateForm(dictionaryOptionEditFormRef.value)
  if (!valid || !editingDictionaryOption.value) return

  dictionaryOptionEditSaving.value = true
  try {
    await configuration.updateDictionaryOption(editingDictionaryOption.value.id, {
      label: dictionaryOptionEditForm.label,
      sort_order: Number(dictionaryOptionEditForm.sort_order) || 0,
      is_active: dictionaryOptionEditForm.is_active
    })
    dictionaryOptionEditOpen.value = false
    ElMessage.success('Saved')
  } catch (error) {
    ElMessage.error(getChineseErrorMessage(error))
  } finally {
    dictionaryOptionEditSaving.value = false
  }
}
```

In the nested dictionary options table, add columns for `sort_order` and an edit action. Do not add buttons that call create or delete dictionary APIs.

Add a dialog using `dictionaryOptionEditOpen`, `dictionaryOptionEditForm`, an `el-input` for label, an `el-input-number` for sort order, and an `el-switch` for active state.

- [ ] **Step 5: Replace hard-coded location types**

Modify `frontend/src/components/config/ResidenceLocationPanel.vue`:

```ts
import { dictionaryLabel, dictionaryOptions } from '../../utils/dictionaries'
```

Replace the hard-coded `locationTypes` array with:

```ts
const locationNodeTypeOptions = computed(() =>
  dictionaryOptions(data.value, 'location_node_types')
)

function locationNodeTypeLabel(value: string) {
  return dictionaryLabel(data.value, 'location_node_types', value)
}
```

When resetting new forms, use:

```ts
node_type: locationNodeTypeOptions.value[0]?.value ?? 'room'
```

In create/edit selects:

```vue
<el-option
  v-for="type in locationNodeTypeOptions"
  :key="type.value"
  :label="type.label"
  :value="type.value"
/>
```

Where node labels currently append `node.node_type`, display `locationNodeTypeLabel(node.node_type)`.

- [ ] **Step 6: Run focused frontend tests and verify GREEN**

Run from `frontend`:

```powershell
.\node_modules\.bin\vue-tsc.cmd --noEmit -p tsconfig.contract.json
node .\tests\config-management-ui-contract.mjs
```

Expected: both pass.

- [ ] **Step 7: Commit Task 5**

```powershell
git add frontend/src/api/configuration.ts frontend/src/stores/configuration.ts frontend/src/utils/dictionaries.ts frontend/src/components/config/DictionaryPanel.vue frontend/src/components/config/ResidenceLocationPanel.vue frontend/tests/config-management-contract.ts frontend/tests/config-management-ui-contract.mjs
git commit -m "feat: edit dictionary options in configuration"
```

## Task 6: Frontend Item Importance Workflows

**Files:**
- Modify: `frontend/src/api/inventory.ts`
- Modify: `frontend/src/components/items/ItemFormDrawer.vue`
- Modify: `frontend/src/components/items/ItemDetailModal.vue`
- Modify: `frontend/src/components/items/ItemTable.vue`
- Modify: `frontend/src/components/items/ItemFilterPanel.vue`
- Create: `frontend/tests/item-importance-ui-contract.mjs`

- [ ] **Step 1: Write failing item importance UI contract**

Create `frontend/tests/item-importance-ui-contract.mjs`:

```js
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

const testDir = dirname(fileURLToPath(import.meta.url))
const root = resolve(testDir, '..')

function readSource(relativePath) {
  return readFileSync(resolve(root, relativePath), 'utf8')
}

const inventoryApi = readSource('src/api/inventory.ts')
const itemFormDrawer = readSource('src/components/items/ItemFormDrawer.vue')
const itemDetailModal = readSource('src/components/items/ItemDetailModal.vue')
const itemTable = readSource('src/components/items/ItemTable.vue')
const itemFilterPanel = readSource('src/components/items/ItemFilterPanel.vue')

assert.match(inventoryApi, /importance:\s*string/, 'Inventory item summary should expose importance')
assert.match(inventoryApi, /importance\?:\s*string/, 'Inventory create/update/filter payloads should accept importance')
assert.match(itemFormDrawer, /importanceOptions/, 'Item form should compute importance dictionary options')
assert.match(itemFormDrawer, /v-model="form\.importance"/, 'Item form should bind importance select')
assert.match(itemDetailModal, /importanceLabel/, 'Item detail should render an importance label')
assert.match(itemTable, /row\.importance/, 'Item table should render item importance')
assert.match(itemFilterPanel, /importanceValue/, 'Item filter panel should expose importance filtering')
assert.match(itemFilterPanel, /importanceOptions/, 'Item filter panel should use dictionary options for importance')
```

- [ ] **Step 2: Run tests and verify RED**

Run from `frontend`:

```powershell
node .\tests\item-importance-ui-contract.mjs
.\node_modules\.bin\vue-tsc.cmd --noEmit -p tsconfig.contract.json
```

Expected: source contract fails because item importance UI is missing.

- [ ] **Step 3: Update inventory API types**

Modify `frontend/src/api/inventory.ts`:

```ts
export interface ItemSummary {
  ...
  unit: string
  importance: string
```

```ts
export interface ItemFilters {
  ...
  status_id?: number | null
  importance?: string | null
```

```ts
export interface ItemCreateRequest {
  ...
  unit?: string
  importance?: string
```

```ts
export interface ItemUpdateRequest {
  ...
  unit?: string
  importance?: string
```

- [ ] **Step 4: Add item form importance field**

Modify `frontend/src/components/items/ItemFormDrawer.vue` imports:

```ts
import { dictionaryOptions } from '../../utils/dictionaries'
```

Add `importance` to `ItemFormModel`:

```ts
  importance: string
```

Add computed options:

```ts
const importanceOptions = computed(() => dictionaryOptions(data.value, 'importance'))
```

In `createEmptyForm`, set:

```ts
    importance: 'medium',
```

In edit assignment:

```ts
      importance: item.importance || 'medium',
```

In create reset assignment:

```ts
      importance: importanceOptions.value.find((option) => option.value === 'medium')?.value
        ?? importanceOptions.value[0]?.value
        ?? 'medium',
```

In create/update payloads, include:

```ts
    importance: form.importance,
```

Add an `el-form-item` near unit/privacy:

```vue
<el-form-item label="Importance">
  <el-select v-model="form.importance" class="full-width">
    <el-option
      v-for="option in importanceOptions"
      :key="option.value"
      :label="option.label"
      :value="option.value"
    />
  </el-select>
</el-form-item>
```

- [ ] **Step 5: Add detail, table, and filter display**

Modify `frontend/src/components/items/ItemDetailModal.vue`:

```ts
import { dictionaryLabel } from '../../utils/dictionaries'
import { useConfigurationStore } from '../../stores/configuration'

const configuration = useConfigurationStore()
const { data } = storeToRefs(configuration)

const importanceLabel = computed(() => dictionaryLabel(data.value, 'importance', props.item?.importance))
```

Add a descriptions item:

```vue
<el-descriptions-item label="Importance">{{ importanceLabel }}</el-descriptions-item>
```

Modify `frontend/src/components/items/ItemTable.vue`:

```ts
import { storeToRefs } from 'pinia'
import { useConfigurationStore } from '../../stores/configuration'
import { dictionaryLabel } from '../../utils/dictionaries'

const configuration = useConfigurationStore()
const { data } = storeToRefs(configuration)

function importanceLabel(value: string) {
  return dictionaryLabel(data.value, 'importance', value)
}
```

Add a compact table column:

```vue
<el-table-column label="Importance" width="96">
  <template #default="{ row }">{{ importanceLabel(row.importance) }}</template>
</el-table-column>
```

Modify `frontend/src/components/items/ItemFilterPanel.vue`:

```ts
import { dictionaryOptions } from '../../utils/dictionaries'

const importanceOptions = computed(() => dictionaryOptions(data.value, 'importance'))

const importanceValue = computed({
  get: () => inventory.filters.importance ?? '',
  set: (value: string) => {
    void applyFilters({ importance: value || null })
  }
})
```

Add a filter section:

```vue
<section class="filter-section">
  <div class="section-title">
    <el-icon><Location /></el-icon>
    <span>Importance</span>
  </div>
  <el-select v-model="importanceValue" clearable class="full-width">
    <el-option
      v-for="option in importanceOptions"
      :key="option.value"
      :label="option.label"
      :value="option.value"
    />
  </el-select>
</section>
```

- [ ] **Step 6: Run focused frontend tests and verify GREEN**

Run from `frontend`:

```powershell
node .\tests\item-importance-ui-contract.mjs
.\node_modules\.bin\vue-tsc.cmd --noEmit -p tsconfig.contract.json
```

Expected: both pass.

- [ ] **Step 7: Commit Task 6**

```powershell
git add frontend/src/api/inventory.ts frontend/src/components/items/ItemFormDrawer.vue frontend/src/components/items/ItemDetailModal.vue frontend/src/components/items/ItemTable.vue frontend/src/components/items/ItemFilterPanel.vue frontend/tests/item-importance-ui-contract.mjs
git commit -m "feat: surface item importance in inventory UI"
```

## Task 7: Final Verification And Closeout

**Files:**
- Modify if needed: `docs/superpowers/phase-4-closeout.md`

- [ ] **Step 1: Run backend focused test suite**

Run from `backend`:

```powershell
python -m pytest tests/test_configuration_seed.py tests/test_configuration_api.py tests/test_database_models.py tests/test_inventory_api.py -q
```

Expected: all selected tests pass with only existing TestClient warnings.

- [ ] **Step 2: Run frontend contracts and type checks**

Run from `frontend`:

```powershell
.\node_modules\.bin\vue-tsc.cmd --noEmit -p tsconfig.contract.json
node .\tests\config-management-ui-contract.mjs
node .\tests\item-importance-ui-contract.mjs
node .\tests\inventory-import-contract.mjs
node .\tests\inventory-bulk-export-contract.mjs
```

Expected: all commands pass.

- [ ] **Step 3: Run production build**

Run from `frontend`:

```powershell
npm.cmd run build
```

Expected: build passes. Existing Vite/Rollup warnings about large chunks or pure annotations are acceptable if unchanged.

- [ ] **Step 4: Check worktree and whitespace**

Run from repository root:

```powershell
git diff --check
git status --short --branch
```

Expected: `git diff --check` exits 0. `git status` shows only intended files before the final commit.

- [ ] **Step 5: Commit final fixes or docs if any**

If Task 7 changed closeout docs or test contracts, commit those changes:

```powershell
git add docs/superpowers/phase-4-closeout.md frontend/tests/item-importance-ui-contract.mjs
git commit -m "docs: update dictionary importance closeout"
```

Skip this commit when Task 7 makes no file changes.

- [ ] **Step 6: Report verification evidence**

Record the exact commands and results in the final implementation summary:

```text
Backend: python -m pytest tests/test_configuration_seed.py tests/test_configuration_api.py tests/test_database_models.py tests/test_inventory_api.py -q
Frontend: vue-tsc contract, config-management-ui-contract, item-importance-ui-contract, inventory import/export contracts
Build: npm.cmd run build
Git: git diff --check, git status --short --branch
```
