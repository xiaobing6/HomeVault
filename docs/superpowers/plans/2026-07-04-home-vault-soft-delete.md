# HomeVault Soft Delete Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add soft delete for residences, location nodes, family members, and items while preserving history and hiding deleted records from normal workflows.

**Architecture:** Extend existing models with explicit `is_deleted`, `deleted_at`, and `deleted_by_id` fields, keeping `is_active` and `is_archived` semantics intact. Backend services own reference guards and default filtering; frontend panels call new delete APIs through the existing Pinia stores and use confirmation prompts before removal.

**Tech Stack:** FastAPI, SQLAlchemy, Alembic, Pydantic, pytest, Vue 3, Pinia, Element Plus, TypeScript contract tests.

---

## File Structure

- Modify `backend/app/models/configuration.py`: add soft-delete fields to `Residence`, `LocationNode`, and `FamilyMember`; update residence active-name unique index to ignore deleted residences.
- Modify `backend/app/models/inventory.py`: add soft-delete fields to `Item`; make active-child checks ignore deleted items.
- Create `backend/alembic/versions/20260704_0011_soft_delete_core_entities.py`: add columns and indexes, rebuild residence active-name partial unique index.
- Modify `backend/app/schemas/configuration.py`: expose `is_deleted` on residence, location, and family member responses.
- Modify `backend/app/schemas/inventory.py`: expose item delete fields and add single/bulk delete request schemas.
- Modify `backend/app/services/configuration.py`: filter deleted config records, add safe delete helpers, and audit delete actions.
- Modify `backend/app/services/inventory.py`: filter deleted items, reject unsafe item deletes, add single/bulk delete services, and audit delete actions.
- Modify `backend/app/api/routes/configuration.py`: add config delete endpoints under `config:manage`.
- Modify `backend/app/api/routes/inventory.py`: add item delete endpoints under `items:archive`.
- Modify `backend/tests/test_configuration_api.py`: add config delete API and audit coverage.
- Modify `backend/tests/test_inventory_services.py`: add item service delete behavior coverage.
- Modify `backend/tests/test_inventory_api.py`: add item delete API, permissions, export/list/detail coverage.
- Modify `frontend/src/api/configuration.ts`: add `is_deleted` fields and delete API helpers.
- Modify `frontend/src/api/inventory.ts`: add item delete fields, request types, and delete API helpers.
- Modify `frontend/src/stores/configuration.ts`: add delete actions and reload bootstrap.
- Modify `frontend/src/stores/inventory.ts`: add single and bulk delete actions.
- Modify `frontend/src/components/config/ResidenceLocationPanel.vue`: add residence/location delete confirmation controls.
- Modify `frontend/src/components/config/FamilyMemberPanel.vue`: add family member delete confirmation control.
- Modify `frontend/src/components/items/ItemToolbar.vue`: add bulk delete menu event.
- Modify `frontend/src/components/items/ItemDetailModal.vue`: add item delete event/control.
- Modify `frontend/src/components/items/ItemActionDialogs.vue`: add single delete dialog branch.
- Modify `frontend/src/components/items/BulkActionDialogs.vue`: add bulk delete dialog branch.
- Modify `frontend/src/pages/ItemsPage.vue`: wire item delete actions and close detail on single delete.
- Modify `frontend/tests/config-management-contract.ts`: verify config delete API/store contracts and `is_deleted` types.
- Modify `frontend/tests/config-management-ui-contract.mjs`: verify config delete controls.
- Modify `frontend/tests/inventory-bulk-export-contract.mjs`: verify inventory delete API/store/toolbar/page controls.

---

### Task 1: Data Model, Migration, and Schema Fields

**Files:**
- Modify: `backend/tests/test_configuration_api.py`
- Modify: `backend/tests/test_inventory_services.py`
- Modify: `backend/app/models/configuration.py`
- Modify: `backend/app/models/inventory.py`
- Create: `backend/alembic/versions/20260704_0011_soft_delete_core_entities.py`
- Modify: `backend/app/schemas/configuration.py`
- Modify: `backend/app/schemas/inventory.py`

- [ ] **Step 1: Write failing schema/model tests**

Append to `backend/tests/test_configuration_api.py`:

```python
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
```

Append to `backend/tests/test_inventory_services.py`:

```python
def test_item_detail_response_includes_soft_delete_fields(
    db_session: Session,
    inventory_seed: dict[str, object],
) -> None:
    item = create_item(db_session, make_create_payload(inventory_seed))

    detail = get_item_detail(db_session, item.id)

    assert detail.is_deleted is False
    assert detail.deleted_at is None
    assert detail.delete_reason == ""
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
cd backend
python -m pytest tests/test_configuration_api.py::test_configuration_payloads_include_soft_delete_flags tests/test_inventory_services.py::test_item_detail_response_includes_soft_delete_fields -q
```

Expected: FAIL because response schemas and models do not expose `is_deleted`, `deleted_at`, or `delete_reason`.

- [ ] **Step 3: Add model fields**

In `backend/app/models/configuration.py`, add to `Residence` after `is_active`:

```python
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    deleted_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
```

Add relationship near `updated_by`:

```python
    deleted_by: Mapped[object | None] = relationship("User", foreign_keys=[deleted_by_id], lazy="selectin")
```

Change the residence partial unique index predicates:

```python
            sqlite_where=text("is_active = 1 AND is_deleted = 0"),
            postgresql_where=text("is_active = true AND is_deleted = false"),
```

Add to `LocationNode` after `is_active`:

```python
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    deleted_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    deleted_by: Mapped[object | None] = relationship("User", foreign_keys=[deleted_by_id], lazy="selectin")
```

Add to `FamilyMember` after `is_active`:

```python
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    deleted_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    deleted_by: Mapped[object | None] = relationship("User", foreign_keys=[deleted_by_id], lazy="selectin")
```

In `backend/app/models/inventory.py`, add to `Item` after `archived_at`:

```python
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    delete_reason: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    deleted_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
```

- [ ] **Step 4: Add Alembic migration**

Create `backend/alembic/versions/20260704_0011_soft_delete_core_entities.py`:

```python
"""add soft delete fields to core entities

Revision ID: 20260704_0011
Revises: 20260704_0010
Create Date: 2026-07-04 15:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "20260704_0011"
down_revision = "20260704_0010"
branch_labels = None
depends_on = None


def _index_exists(table_name: str, index_name: str) -> bool:
    inspector = sa.inspect(op.get_bind())
    return index_name in {index["name"] for index in inspector.get_indexes(table_name)}


def _add_soft_delete_columns(table_name: str, include_reason: bool = False) -> None:
    with op.batch_alter_table(table_name) as batch_op:
        batch_op.add_column(sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.false()))
        if include_reason:
            batch_op.add_column(sa.Column("delete_reason", sa.String(length=255), nullable=False, server_default=""))
        batch_op.add_column(sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(sa.Column("deleted_by_id", sa.Integer(), nullable=True))
        batch_op.create_foreign_key(
            f"fk_{table_name}_deleted_by_id_users",
            "users",
            ["deleted_by_id"],
            ["id"],
            ondelete="SET NULL",
        )
    op.create_index(f"ix_{table_name}_is_deleted", table_name, ["is_deleted"])


def _drop_soft_delete_columns(table_name: str, include_reason: bool = False) -> None:
    if _index_exists(table_name, f"ix_{table_name}_is_deleted"):
        op.drop_index(f"ix_{table_name}_is_deleted", table_name=table_name)
    with op.batch_alter_table(table_name) as batch_op:
        batch_op.drop_constraint(f"fk_{table_name}_deleted_by_id_users", type_="foreignkey")
        batch_op.drop_column("deleted_by_id")
        batch_op.drop_column("deleted_at")
        if include_reason:
            batch_op.drop_column("delete_reason")
        batch_op.drop_column("is_deleted")


def upgrade() -> None:
    if _index_exists("residences", "uq_residences_active_name"):
        op.drop_index("uq_residences_active_name", table_name="residences")

    _add_soft_delete_columns("residences")
    _add_soft_delete_columns("location_nodes")
    _add_soft_delete_columns("family_members")
    _add_soft_delete_columns("items", include_reason=True)

    op.create_index(
        "uq_residences_active_name",
        "residences",
        ["name"],
        unique=True,
        sqlite_where=sa.text("is_active = 1 AND is_deleted = 0"),
        postgresql_where=sa.text("is_active = true AND is_deleted = false"),
    )

    if op.get_context().dialect.name != "sqlite":
        for table_name in ("residences", "location_nodes", "family_members", "items"):
            op.alter_column(table_name, "is_deleted", server_default=None)
        op.alter_column("items", "delete_reason", server_default=None)


def downgrade() -> None:
    if _index_exists("residences", "uq_residences_active_name"):
        op.drop_index("uq_residences_active_name", table_name="residences")

    _drop_soft_delete_columns("items", include_reason=True)
    _drop_soft_delete_columns("family_members")
    _drop_soft_delete_columns("location_nodes")
    _drop_soft_delete_columns("residences")

    op.create_index(
        "uq_residences_active_name",
        "residences",
        ["name"],
        unique=True,
        sqlite_where=sa.text("is_active = 1"),
        postgresql_where=sa.text("is_active = true"),
    )
```

- [ ] **Step 5: Add response schema fields**

In `backend/app/schemas/configuration.py`, add `is_deleted: bool` to `ResidenceResponse`, `LocationNodeResponse`, and `FamilyMemberResponse`.

In `backend/app/schemas/inventory.py`, add to `ItemSummaryResponse`:

```python
    is_deleted: bool
```

Add to `ItemDetailResponse`:

```python
    delete_reason: str
    deleted_at: datetime | None = None
```

Add request schemas after `ArchiveItemRequest`:

```python
class DeleteItemRequest(RequestModel):
    delete_reason: str = Field(default="", max_length=255)
```

Add after `BulkArchiveItemsRequest`:

```python
class BulkDeleteItemsRequest(ItemIdBatchMixin):
    delete_reason: str = Field(default="", max_length=255)
```

- [ ] **Step 6: Include fields in item response builders**

In `backend/app/services/configuration.py`, add to `build_residence_response`:

```python
        is_deleted=residence.is_deleted,
```

In `backend/app/services/inventory.py`, add to `build_item_summary_response`:

```python
        is_deleted=item.is_deleted,
```

Add to `build_item_detail_response`:

```python
        delete_reason=redacted_if_sensitive(item.delete_reason, redact=not show_sensitive_data),
        deleted_at=item.deleted_at,
```

- [ ] **Step 7: Run tests to verify green**

Run:

```bash
cd backend
python -m pytest tests/test_configuration_api.py::test_configuration_payloads_include_soft_delete_flags tests/test_inventory_services.py::test_item_detail_response_includes_soft_delete_fields -q
```

Expected: PASS.

---

### Task 2: Configuration Soft Delete Backend

**Files:**
- Modify: `backend/tests/test_configuration_api.py`
- Modify: `backend/app/services/configuration.py`
- Modify: `backend/app/api/routes/configuration.py`
- Modify: `backend/app/services/inventory_import.py`

- [ ] **Step 1: Write failing configuration delete API tests**

Append to `backend/tests/test_configuration_api.py`:

```python
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
```

Append to `backend/tests/test_configuration_api.py`:

```python
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
    assert "物品" in location_delete.json()["detail"]["message"]
    assert residence_delete.status_code == 400
    assert "物品" in residence_delete.json()["detail"]["message"]
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
cd backend
python -m pytest tests/test_configuration_api.py::test_config_delete_endpoints_hide_records_and_write_audit_logs tests/test_configuration_api.py::test_config_delete_blocks_active_inventory_references -q
```

Expected: FAIL because delete endpoints are missing.

- [ ] **Step 3: Add configuration service helpers**

In `backend/app/services/configuration.py`, import `Item`:

```python
from app.models.inventory import Item
```

Add helper functions near `assert_active_residence_name_available`:

```python
RESOURCE_NOT_FOUND_MESSAGE = "资源不存在"


def not_deleted_filter(model):
    return model.is_deleted.is_(False)


def collect_location_subtree_ids(nodes: list[LocationNode], root_id: int) -> set[int]:
    children_by_parent: dict[int | None, list[LocationNode]] = {}
    for node in nodes:
        children_by_parent.setdefault(node.parent_id, []).append(node)

    collected: set[int] = set()
    stack = [root_id]
    while stack:
        node_id = stack.pop()
        if node_id in collected:
            continue
        collected.add(node_id)
        stack.extend(child.id for child in children_by_parent.get(node_id, []))
    return collected


def active_inventory_effective_location_ids(db: Session) -> set[int]:
    items = db.scalars(
        select(Item).where(
            Item.is_deleted.is_(False),
            Item.is_archived.is_(False),
        )
    ).all()
    items_by_id = {item.id: item for item in items}
    location_ids: set[int] = set()
    for item in items:
        current = item
        visited: set[int] = set()
        while current is not None and current.id not in visited:
            visited.add(current.id)
            if current.location_node_id is not None:
                location_ids.add(current.location_node_id)
                break
            if current.container_item_id is None:
                break
            current = items_by_id.get(current.container_item_id)
    return location_ids


def assert_no_active_items_in_locations(db: Session, location_ids: set[int], message: str) -> None:
    if not location_ids:
        return
    if active_inventory_effective_location_ids(db) & location_ids:
        raise bad_request(message)
```

- [ ] **Step 4: Filter deleted configuration records**

Update these queries in `backend/app/services/configuration.py`:

```python
select(Residence).where(Residence.is_deleted.is_(False))
select(LocationNode).where(LocationNode.is_deleted.is_(False))
select(FamilyMember).where(FamilyMember.is_deleted.is_(False))
```

Apply those filters in:

- `list_residences`
- `list_location_tree`
- `list_family_members`
- `get_config_bootstrap`
- `assert_active_residence_name_available`
- `create_location_node` residence lookup
- `assert_location_parent_valid`

For create/update validation, treat deleted records like missing by raising existing bad request messages.

- [ ] **Step 5: Implement delete services**

Add to `backend/app/services/configuration.py`:

```python
def delete_family_member(
    db: Session,
    member_id: int,
    actor: User | None = None,
) -> FamilyMemberResponse:
    member = db.get(FamilyMember, member_id)
    if member is None or member.is_deleted:
        raise not_found(RESOURCE_NOT_FOUND_MESSAGE)

    member.is_deleted = True
    member.deleted_at = utcnow()
    member.deleted_by_id = actor.id if actor is not None else None
    record_audit_log(
        db,
        action="config.family_member.delete",
        resource_type="family_member",
        actor=actor,
        resource_id=member.id,
        resource_label=member.name,
    )
    db.commit()
    db.refresh(member)
    return FamilyMemberResponse.model_validate(member)


def delete_location_node(
    db: Session,
    node_id: int,
    actor: User | None = None,
) -> LocationNodeResponse:
    node = db.get(LocationNode, node_id)
    if node is None or node.is_deleted:
        raise not_found(RESOURCE_NOT_FOUND_MESSAGE)

    residence_nodes = db.scalars(
        select(LocationNode).where(
            LocationNode.residence_id == node.residence_id,
            LocationNode.is_deleted.is_(False),
        )
    ).all()
    subtree_ids = collect_location_subtree_ids(list(residence_nodes), node.id)
    assert_no_active_items_in_locations(
        db,
        subtree_ids,
        "位置下还有未删除物品，请先移动、归档或删除物品",
    )

    deleted_at = utcnow()
    for current in residence_nodes:
        if current.id in subtree_ids:
            current.is_deleted = True
            current.deleted_at = deleted_at
            current.deleted_by_id = actor.id if actor is not None else None

    record_audit_log(
        db,
        action="config.location.delete",
        resource_type="location_node",
        actor=actor,
        resource_id=node.id,
        resource_label=node.name,
        metadata={"residence_id": node.residence_id, "deleted_count": len(subtree_ids)},
    )
    db.commit()
    db.refresh(node)
    return LocationNodeResponse.model_validate(node)


def delete_residence(
    db: Session,
    residence_id: int,
    actor: User | None = None,
) -> ResidenceResponse:
    residence = db.get(Residence, residence_id)
    if residence is None or residence.is_deleted:
        raise not_found(RESOURCE_NOT_FOUND_MESSAGE)

    nodes = db.scalars(
        select(LocationNode).where(
            LocationNode.residence_id == residence.id,
            LocationNode.is_deleted.is_(False),
        )
    ).all()
    location_ids = {node.id for node in nodes}
    assert_no_active_items_in_locations(
        db,
        location_ids,
        "住宅下还有未删除物品，请先移动、归档或删除物品",
    )

    deleted_at = utcnow()
    residence.is_deleted = True
    residence.deleted_at = deleted_at
    residence.deleted_by_id = actor.id if actor is not None else None
    for node in nodes:
        node.is_deleted = True
        node.deleted_at = deleted_at
        node.deleted_by_id = actor.id if actor is not None else None

    record_audit_log(
        db,
        action="config.residence.delete",
        resource_type="residence",
        actor=actor,
        resource_id=residence.id,
        resource_label=residence.name,
        metadata={"deleted_location_count": len(nodes)},
    )
    commit_or_bad_request(db, ACTIVE_RESIDENCE_NAME_EXISTS_MESSAGE)
    db.refresh(residence)
    return build_residence_response(residence)
```

- [ ] **Step 6: Add routes**

In `backend/app/api/routes/configuration.py`, import delete service aliases:

```python
    delete_family_member as delete_family_member_record,
    delete_location_node as delete_location_node_record,
    delete_residence as delete_residence_record,
```

Add routes:

```python
@router.delete("/residences/{residence_id}", response_model=ResidenceResponse)
def delete_residence(
    residence_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("config:manage")),
) -> ResidenceResponse:
    return delete_residence_record(db, residence_id, actor=user)


@router.delete("/location-nodes/{node_id}", response_model=LocationNodeResponse)
def delete_location_node(
    node_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("config:manage")),
) -> LocationNodeResponse:
    return delete_location_node_record(db, node_id, actor=user)


@router.delete("/family-members/{member_id}", response_model=FamilyMemberResponse)
def delete_family_member(
    member_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("config:manage")),
) -> FamilyMemberResponse:
    return delete_family_member_record(db, member_id, actor=user)
```

- [ ] **Step 7: Filter deleted records in import matching**

In `backend/app/services/inventory_import.py`, add `is_deleted.is_(False)` to residence, location, and family member lookup statements:

```python
FamilyMember.is_deleted.is_(False)
Residence.is_deleted.is_(False)
LocationNode.is_deleted.is_(False)
```

- [ ] **Step 8: Run configuration tests**

Run:

```bash
cd backend
python -m pytest tests/test_configuration_api.py::test_config_delete_endpoints_hide_records_and_write_audit_logs tests/test_configuration_api.py::test_config_delete_blocks_active_inventory_references -q
```

Expected: PASS.

---

### Task 3: Item Soft Delete Backend

**Files:**
- Modify: `backend/tests/test_inventory_services.py`
- Modify: `backend/tests/test_inventory_api.py`
- Modify: `backend/app/services/inventory.py`
- Modify: `backend/app/api/routes/inventory.py`

- [ ] **Step 1: Write failing item service tests**

Append to `backend/tests/test_inventory_services.py`:

```python
def test_delete_item_hides_from_lists_and_detail(
    db_session: Session,
    inventory_seed: dict[str, object],
) -> None:
    from app.schemas.inventory import DeleteItemRequest
    from app.services.inventory import delete_item

    item = create_item(db_session, make_create_payload(inventory_seed, name="Delete me"))

    deleted = delete_item(db_session, item.id, DeleteItemRequest(delete_reason="Duplicate"), actor_id=7)

    assert deleted.is_deleted is True
    assert deleted.delete_reason == "Duplicate"
    assert deleted.deleted_at is not None
    assert list_items(db_session, ItemListQuery(include_archived=True)).total == 0
    with pytest.raises(HTTPException):
        get_item_detail(db_session, item.id)


def test_delete_item_blocks_children_and_active_loan(
    db_session: Session,
    inventory_seed: dict[str, object],
) -> None:
    from app.schemas.inventory import DeleteItemRequest
    from app.services.inventory import delete_item

    container = create_item(
        db_session,
        make_create_payload(inventory_seed, name="Container", is_container=True),
    )
    child_payload = make_create_payload(
        inventory_seed,
        name="Child",
        location_node_id=None,
        container_item_id=container.id,
        is_container=False,
    )
    create_item(db_session, child_payload)

    with pytest.raises(HTTPException) as child_exc:
        delete_item(db_session, container.id, DeleteItemRequest())
    assert "子物品" in str(child_exc.value.detail)

    loaned = create_item(db_session, make_create_payload(inventory_seed, name="Loaned"))
    create_loan(db_session, loaned.id, LoanCreate(borrower_name="Friend"))

    with pytest.raises(HTTPException) as loan_exc:
        delete_item(db_session, loaned.id, DeleteItemRequest())
    assert "借用" in str(loan_exc.value.detail)
```

- [ ] **Step 2: Write failing item API tests**

Append to `backend/tests/test_inventory_api.py`:

```python
def test_admin_can_delete_item_and_bulk_delete_items(client: TestClient, db_session: Session) -> None:
    headers = login(client)
    ids = inventory_ids(db_session)
    first = create_item(client, headers, ids, name="Delete one")
    second = create_item(client, headers, ids, name="Delete two")

    single_delete = client.request(
        "DELETE",
        f"/api/items/{first['id']}",
        headers=headers,
        json={"delete_reason": "Duplicate"},
    )
    bulk_delete = client.post(
        "/api/items/bulk/delete",
        headers=headers,
        json={"item_ids": [second["id"], second["id"]], "delete_reason": "Cleanup"},
    )
    list_response = client.get("/api/items", headers=headers, params={"include_archived": True})
    detail_response = client.get(f"/api/items/{first['id']}", headers=headers)
    export_response = client.post("/api/items/export.csv", headers=headers, json={})

    assert single_delete.status_code == 200
    assert single_delete.json()["is_deleted"] is True
    assert single_delete.json()["delete_reason"] == "Duplicate"
    assert bulk_delete.status_code == 200
    assert bulk_delete.json()["updated_count"] == 1
    assert list_response.json()["total"] == 0
    assert detail_response.status_code == 404
    assert "Delete one" not in export_response.text
    assert "Delete two" not in export_response.text


def test_editor_cannot_delete_items(client: TestClient, db_session: Session) -> None:
    admin_headers = login(client)
    editor_headers = login(client, "editor", "Editor123!")
    ids = inventory_ids(db_session)
    item = create_item(client, admin_headers, ids)

    response = client.request("DELETE", f"/api/items/{item['id']}", headers=editor_headers, json={})

    assert response.status_code == 403
```

- [ ] **Step 3: Run tests to verify they fail**

Run:

```bash
cd backend
python -m pytest tests/test_inventory_services.py::test_delete_item_hides_from_lists_and_detail tests/test_inventory_services.py::test_delete_item_blocks_children_and_active_loan tests/test_inventory_api.py::test_admin_can_delete_item_and_bulk_delete_items tests/test_inventory_api.py::test_editor_cannot_delete_items -q
```

Expected: FAIL because delete schemas, services, and routes are missing.

- [ ] **Step 4: Add imports**

In `backend/app/services/inventory.py`, import request schemas:

```python
    BulkDeleteItemsRequest,
    DeleteItemRequest,
```

In `backend/app/api/routes/inventory.py`, import:

```python
    BulkDeleteItemsRequest,
    DeleteItemRequest,
```

and service functions:

```python
    bulk_delete_items,
    delete_item,
```

- [ ] **Step 5: Exclude deleted items from reads and validations**

In `backend/app/services/inventory.py`, update `require_item`:

```python
    if item is None or item.is_deleted:
        raise not_found("物品不存在")
```

Update `require_items` statement:

```python
select(Item).where(Item.id.in_(item_ids), Item.is_deleted.is_(False))
```

Update `load_items_for_response` statement:

```python
select(Item).where(Item.id.in_(item_ids), Item.is_deleted.is_(False))
```

Update `load_item_for_response`:

```python
        .where(Item.id == item_id, Item.is_deleted.is_(False))
```

Update `has_active_children`:

```python
        .where(
            Item.container_item_id == item_id,
            Item.is_archived.is_(False),
            Item.is_deleted.is_(False),
        )
```

Update `validate_basic_placement` container lookup:

```python
        if container_item is None or container_item.is_archived or container_item.is_deleted:
            raise bad_request("容器不存在")
```

Update `build_item_list_filter_statement` to always start with:

```python
    stmt = select(Item).where(Item.is_deleted.is_(False))
```

- [ ] **Step 6: Implement item delete services**

Add to `backend/app/services/inventory.py` near `archive_item`:

```python
def assert_item_can_be_deleted(db: Session, item: Item) -> None:
    if has_active_children(db, item.id):
        raise bad_request("请先移动、归档或删除子物品")
    if has_active_loan(db, item.id):
        raise bad_request("物品存在未归还借用记录，不能删除")


def delete_item(
    db: Session,
    item_id: int,
    payload: DeleteItemRequest | None = None,
    actor_id: int | None = None,
    include_sensitive: bool = True,
) -> ItemDetailResponse:
    item = require_item(db, item_id)
    assert_item_can_be_deleted(db, item)
    delete_payload = payload or DeleteItemRequest()
    item.is_deleted = True
    item.delete_reason = delete_payload.delete_reason
    item.deleted_at = utcnow()
    item.deleted_by_id = actor_id
    item.updated_by_id = actor_id
    record_audit_log(
        db,
        action="inventory.item.delete",
        resource_type="item",
        actor_user_id=actor_id,
        resource_id=item.id,
        resource_label=item.name,
        metadata={"delete_reason": item.delete_reason},
    )
    commit_or_bad_request(db, "物品保存失败")
    db.refresh(item)
    return build_item_detail_response(item, include_sensitive=include_sensitive)


def bulk_delete_items(
    db: Session,
    payload: BulkDeleteItemsRequest,
    actor_id: int | None = None,
) -> BulkItemOperationResponse:
    items = require_items(db, payload.item_ids)
    for item in items:
        assert_item_can_be_deleted(db, item)

    deleted_at = utcnow()
    for item in items:
        item.is_deleted = True
        item.delete_reason = payload.delete_reason
        item.deleted_at = deleted_at
        item.deleted_by_id = actor_id
        item.updated_by_id = actor_id
        record_audit_log(
            db,
            action="inventory.item.delete",
            resource_type="item",
            actor_user_id=actor_id,
            resource_id=item.id,
            resource_label=item.name,
            metadata={"delete_reason": item.delete_reason, "bulk": True},
        )
    record_audit_log(
        db,
        action="inventory.item.bulk_delete",
        resource_type="item",
        actor_user_id=actor_id,
        metadata={"item_ids": payload.item_ids, "delete_reason": payload.delete_reason},
    )
    commit_or_bad_request(db, "物品保存失败")
    return BulkItemOperationResponse(updated_count=len(payload.item_ids), item_ids=payload.item_ids)
```

- [ ] **Step 7: Add item delete routes**

In `backend/app/api/routes/inventory.py`, add after archive routes:

```python
@router.delete("/items/{item_id}", response_model=ItemDetailResponse)
def delete_inventory_item(
    item_id: int,
    payload: DeleteItemRequest | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission(ARCHIVE_PERMISSION)),
) -> ItemDetailResponse:
    return delete_item(db, item_id, payload, actor_id=user.id, include_sensitive=can_view_sensitive(user))


@router.post("/items/bulk/delete", response_model=BulkItemOperationResponse)
def bulk_delete_inventory_items(
    payload: BulkDeleteItemsRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission(ARCHIVE_PERMISSION)),
) -> BulkItemOperationResponse:
    return bulk_delete_items(db, payload, actor_id=user.id)
```

- [ ] **Step 8: Run item delete tests**

Run:

```bash
cd backend
python -m pytest tests/test_inventory_services.py::test_delete_item_hides_from_lists_and_detail tests/test_inventory_services.py::test_delete_item_blocks_children_and_active_loan tests/test_inventory_api.py::test_admin_can_delete_item_and_bulk_delete_items tests/test_inventory_api.py::test_editor_cannot_delete_items -q
```

Expected: PASS.

---

### Task 4: Frontend API and Store Contracts

**Files:**
- Modify: `frontend/tests/config-management-contract.ts`
- Modify: `frontend/tests/inventory-bulk-export-contract.mjs`
- Modify: `frontend/src/api/configuration.ts`
- Modify: `frontend/src/api/inventory.ts`
- Modify: `frontend/src/stores/configuration.ts`
- Modify: `frontend/src/stores/inventory.ts`

- [ ] **Step 1: Write failing frontend contract tests**

In `frontend/tests/config-management-contract.ts`, add imports:

```ts
  deleteFamilyMemberApi,
  deleteLocationNodeApi,
  deleteResidenceApi,
  type Residence,
```

Add type assertions inside `assertConfigurationApiContract`:

```ts
  expectType<Residence>(await deleteResidenceApi(1))
  expectType<LocationNode>(await deleteLocationNodeApi(1))
  expectType<FamilyMember>(await deleteFamilyMemberApi(1))
```

Add store assertions inside `assertConfigurationStoreContract`:

```ts
  await configuration.deleteResidence(1)
  await configuration.deleteLocationNode(1)
  await configuration.deleteFamilyMember(1)
```

Add field assertions after payload constants:

```ts
declare const deletedResidence: Residence
declare const deletedLocation: LocationNode
declare const deletedMember: FamilyMember
expectType<boolean>(deletedResidence.is_deleted)
expectType<boolean>(deletedLocation.is_deleted)
expectType<boolean>(deletedMember.is_deleted)
```

In `frontend/tests/inventory-bulk-export-contract.mjs`, add expectations:

```js
assert.match(api, /is_deleted:\s*boolean/)
assert.match(api, /delete_reason:\s*string/)
assert.match(api, /deleteItemApi/)
assert.match(api, /bulkDeleteItemsApi/)
assert.match(store, /deleteItem/)
assert.match(store, /bulkDeleteItems/)
```

- [ ] **Step 2: Run frontend contract tests to verify they fail**

Run:

```bash
cd frontend
npx vue-tsc -p tsconfig.contract.json
node tests/inventory-bulk-export-contract.mjs
```

Expected: FAIL because delete API/store helpers and fields are missing.

- [ ] **Step 3: Update configuration API types/helpers**

In `frontend/src/api/configuration.ts`, add `is_deleted: boolean` to `Residence`, `LocationNode`, and `FamilyMember`.

Add helpers:

```ts
export async function deleteResidenceApi(residenceId: number): Promise<Residence> {
  const response = await apiClient.delete<Residence>(`/config/residences/${residenceId}`)
  return response.data
}

export async function deleteLocationNodeApi(nodeId: number): Promise<LocationNode> {
  const response = await apiClient.delete<LocationNode>(`/config/location-nodes/${nodeId}`)
  return response.data
}

export async function deleteFamilyMemberApi(memberId: number): Promise<FamilyMember> {
  const response = await apiClient.delete<FamilyMember>(`/config/family-members/${memberId}`)
  return response.data
}
```

- [ ] **Step 4: Update inventory API types/helpers**

In `frontend/src/api/inventory.ts`, add to `ItemSummary`:

```ts
  is_deleted: boolean
```

Add to `ItemDetail`:

```ts
  delete_reason: string
  deleted_at: string | null
```

Add request interfaces:

```ts
export interface DeleteItemRequest {
  delete_reason?: string
}

export interface BulkDeleteItemsRequest {
  item_ids: number[]
  delete_reason?: string
}
```

Add helpers:

```ts
export async function deleteItemApi(
  itemId: number,
  payload: DeleteItemRequest = {}
): Promise<ItemDetail> {
  const response = await apiClient.delete<ItemDetail>(`/items/${itemId}`, { data: payload })
  return response.data
}

export async function bulkDeleteItemsApi(
  payload: BulkDeleteItemsRequest
): Promise<BulkItemOperationResponse> {
  const response = await apiClient.post<BulkItemOperationResponse>('/items/bulk/delete', payload)
  return response.data
}
```

- [ ] **Step 5: Update stores**

In `frontend/src/stores/configuration.ts`, import delete helpers and add actions:

```ts
    async deleteResidence(residenceId: number) {
      const residence = await deleteResidenceApi(residenceId)
      await this.load()
      return residence
    },
    async deleteLocationNode(nodeId: number) {
      const location = await deleteLocationNodeApi(nodeId)
      await this.load()
      return location
    },
    async deleteFamilyMember(memberId: number) {
      const member = await deleteFamilyMemberApi(memberId)
      await this.load()
      return member
    },
```

In `frontend/src/stores/inventory.ts`, import delete helpers/types and add actions:

```ts
    async deleteItem(itemId: number, payload: DeleteItemRequest = {}) {
      return await this.saveAndRefresh(() => deleteItemApi(itemId, payload))
    },
    async bulkDeleteItems(payload: BulkDeleteItemsRequest) {
      return await this.saveAndRefresh(() => bulkDeleteItemsApi(payload))
    },
```

- [ ] **Step 6: Run frontend contract tests**

Run:

```bash
cd frontend
npx vue-tsc -p tsconfig.contract.json
node tests/inventory-bulk-export-contract.mjs
```

Expected: PASS.

---

### Task 5: Frontend Configuration Delete UI

**Files:**
- Modify: `frontend/tests/config-management-ui-contract.mjs`
- Modify: `frontend/src/components/config/ResidenceLocationPanel.vue`
- Modify: `frontend/src/components/config/FamilyMemberPanel.vue`

- [ ] **Step 1: Write failing UI contract checks**

In `frontend/tests/config-management-ui-contract.mjs`, add assertions:

```js
assert.match(residenceLocationPanel, /Delete/, 'Residence/location panel should import a delete icon')
assert.match(residenceLocationPanel, /ElMessageBox/, 'Residence/location deletes should confirm before running')
assert.match(residenceLocationPanel, /deleteResidence/, 'Residence/location panel should call configuration.deleteResidence')
assert.match(residenceLocationPanel, /deleteLocationNode/, 'Residence/location panel should call configuration.deleteLocationNode')
assert.match(residenceLocationPanel, /confirmDeleteResidence/, 'Residence detail should expose a residence delete confirmation')
assert.match(residenceLocationPanel, /confirmDeleteLocation/, 'Location detail should expose a location delete confirmation')
assert.match(familyMemberPanel, /ElMessageBox/, 'Family member delete should confirm before running')
assert.match(familyMemberPanel, /deleteFamilyMember/, 'Family member panel should call configuration.deleteFamilyMember')
assert.match(familyMemberPanel, /confirmDeleteMember/, 'Family member table should expose delete confirmation')
```

- [ ] **Step 2: Run UI contract to verify it fails**

Run:

```bash
cd frontend
node tests/config-management-ui-contract.mjs
```

Expected: FAIL because delete controls are missing.

- [ ] **Step 3: Add residence/location delete handlers**

In `ResidenceLocationPanel.vue`, update imports:

```ts
import { ElMessage, ElMessageBox, type FormInstance, type UploadUserFile } from 'element-plus'
import { ArrowLeft, Calendar, Delete, Edit, House, Location, Memo, Picture, Plus, PriceTag, User } from '@element-plus/icons-vue'
```

Add state:

```ts
const deletingResource = ref(false)
```

Add handlers:

```ts
async function confirmDeleteResidence(residence: Residence) {
  try {
    await ElMessageBox.confirm(
      `确定删除住宅「${residence.name}」吗？删除后普通列表将不再显示。`,
      '删除住宅',
      { type: 'warning', confirmButtonText: '删除', cancelButtonText: '取消' }
    )
  } catch {
    return
  }

  deletingResource.value = true
  try {
    await configuration.deleteResidence(residence.id)
    selectedResidence.value = null
    ElMessage.success('已删除住宅')
  } catch (error) {
    ElMessage.error(getChineseErrorMessage(error))
  } finally {
    deletingResource.value = false
  }
}

async function confirmDeleteLocation(location: LocationNode) {
  try {
    await ElMessageBox.confirm(
      `确定删除位置「${location.name}」吗？子位置会一起删除。`,
      '删除位置',
      { type: 'warning', confirmButtonText: '删除', cancelButtonText: '取消' }
    )
  } catch {
    return
  }

  deletingResource.value = true
  try {
    await configuration.deleteLocationNode(location.id)
    selectedLocation.value = null
    ElMessage.success('已删除位置')
  } catch (error) {
    ElMessage.error(getChineseErrorMessage(error))
  } finally {
    deletingResource.value = false
  }
}
```

Add danger buttons in residence and location detail covers next to edit:

```vue
<el-button
  class="detail-delete"
  type="danger"
  :icon="Delete"
  round
  :loading="deletingResource"
  @click.stop="confirmDeleteResidence(selectedResidenceDetail)"
>
  删除
</el-button>
```

```vue
<el-button
  class="detail-delete"
  type="danger"
  :icon="Delete"
  round
  :loading="deletingResource"
  @click.stop="confirmDeleteLocation(selectedLocationDetail)"
>
  删除
</el-button>
```

Add CSS:

```css
.detail-delete {
  position: absolute;
  top: 16px;
  right: 104px;
  border: none;
}
```

- [ ] **Step 4: Add family member delete handler/control**

In `FamilyMemberPanel.vue`, update imports:

```ts
import { ElMessage, ElMessageBox, type FormInstance } from 'element-plus'
import { Delete, Edit, Plus } from '@element-plus/icons-vue'
```

Add state:

```ts
const deletingMemberId = ref<number | null>(null)
```

Add handler:

```ts
async function confirmDeleteMember(member: FamilyMember) {
  try {
    await ElMessageBox.confirm(
      `确定删除家庭成员「${member.name}」吗？历史记录仍会保留姓名。`,
      '删除家庭成员',
      { type: 'warning', confirmButtonText: '删除', cancelButtonText: '取消' }
    )
  } catch {
    return
  }

  deletingMemberId.value = member.id
  try {
    await configuration.deleteFamilyMember(member.id)
    ElMessage.success('已删除成员')
  } catch (error) {
    ElMessage.error(getChineseErrorMessage(error))
  } finally {
    deletingMemberId.value = null
  }
}
```

Widen the action column to `150` and add:

```vue
<el-button
  text
  type="danger"
  :icon="Delete"
  :loading="deletingMemberId === row.id"
  @click="confirmDeleteMember(row)"
>
  删除
</el-button>
```

- [ ] **Step 5: Run UI contract**

Run:

```bash
cd frontend
node tests/config-management-ui-contract.mjs
```

Expected: PASS.

---

### Task 6: Frontend Item Delete UI

**Files:**
- Modify: `frontend/tests/inventory-bulk-export-contract.mjs`
- Modify: `frontend/src/components/items/ItemToolbar.vue`
- Modify: `frontend/src/components/items/ItemDetailModal.vue`
- Modify: `frontend/src/components/items/ItemActionDialogs.vue`
- Modify: `frontend/src/components/items/BulkActionDialogs.vue`
- Modify: `frontend/src/pages/ItemsPage.vue`

- [ ] **Step 1: Write failing item UI contract checks**

In `frontend/tests/inventory-bulk-export-contract.mjs`, add:

```js
assert.match(toolbar, /bulk-delete/)
assert.match(page, /openActionDialog\('delete'\)/)
assert.match(page, /openBulkAction\('delete'\)/)
assert.match(page, /handleDeleteSuccess/)

const detail = source('src/components/items/ItemDetailModal.vue')
assert.match(detail, /delete:/)
assert.match(detail, /emit\('delete'\)/)

const actionDialogs = source('src/components/items/ItemActionDialogs.vue')
assert.match(actionDialogs, /action === 'delete'/)
assert.match(actionDialogs, /deleteItem/)

const bulkDialogs = source('src/components/items/BulkActionDialogs.vue')
assert.match(bulkDialogs, /action === 'delete'/)
assert.match(bulkDialogs, /bulkDeleteItems/)
```

- [ ] **Step 2: Run contract to verify it fails**

Run:

```bash
cd frontend
node tests/inventory-bulk-export-contract.mjs
```

Expected: FAIL because item delete UI is missing.

- [ ] **Step 3: Add bulk delete toolbar event**

In `ItemToolbar.vue`, add `Trash` import:

```ts
import { Download, Grid, List, Operation, Plus, Search, Trash, Upload } from '@element-plus/icons-vue'
```

Add emit:

```ts
  'bulk-delete': []
```

Add dropdown item after archive:

```vue
<el-dropdown-item v-if="canArchive" divided :icon="Trash" @click="emit('bulk-delete')">
  批量删除
</el-dropdown-item>
```

- [ ] **Step 4: Add delete detail event/control**

In `ItemDetailModal.vue`, import `Delete`:

```ts
  Delete,
```

Add emit:

```ts
  delete: []
```

Add danger button after archive:

```vue
<el-button
  v-if="canArchive && !item.is_archived && !item.is_deleted"
  type="danger"
  :icon="Delete"
  @click="emit('delete')"
>
  删除
</el-button>
```

- [ ] **Step 5: Add single delete dialog branch**

In `ItemActionDialogs.vue`, change type:

```ts
type ActionType = 'move' | 'status' | 'borrow' | 'return' | 'quantity' | 'archive' | 'delete'
```

Add form:

```ts
const deleteForm = reactive({
  delete_reason: ''
})
```

Update title:

```ts
  if (props.action === 'delete') return '删除物品'
```

Reset form:

```ts
  deleteForm.delete_reason = ''
```

Add submit branch before archive fallback:

```ts
    } else if (props.action === 'delete') {
      detail = await inventory.deleteItem(props.item.id, {
        delete_reason: deleteForm.delete_reason.trim()
      })
      ElMessage.success('已删除')
```

Add template branch:

```vue
<template v-else-if="action === 'delete'">
  <el-alert
    title="删除后，物品将从普通列表、导出和详情入口隐藏。"
    type="warning"
    :closable="false"
  />
  <el-form-item label="删除原因">
    <el-input
      v-model="deleteForm.delete_reason"
      type="textarea"
      :rows="4"
      maxlength="255"
      show-word-limit
    />
  </el-form-item>
</template>
```

- [ ] **Step 6: Add bulk delete dialog branch**

In `BulkActionDialogs.vue`, change type:

```ts
type BulkActionType = 'move' | 'status' | 'archive' | 'delete'
```

Add form:

```ts
const deleteForm = reactive({
  delete_reason: ''
})
```

Update title:

```ts
  if (props.action === 'delete') return '批量删除'
```

Reset form:

```ts
  deleteForm.delete_reason = ''
```

Add submit branch:

```ts
    } else if (props.action === 'delete') {
      response = await inventory.bulkDeleteItems({
        item_ids: props.selectedItemIds,
        delete_reason: deleteForm.delete_reason.trim()
      })
      ElMessage.success(`已删除 ${response.updated_count} 个物品`)
```

Add template branch:

```vue
<template v-else-if="action === 'delete'">
  <el-alert
    title="删除后，所选物品将从普通列表、导出和详情入口隐藏。"
    type="warning"
    :closable="false"
  />
  <el-form-item label="删除原因">
    <el-input v-model="deleteForm.delete_reason" maxlength="255" show-word-limit />
  </el-form-item>
</template>
```

- [ ] **Step 7: Wire item page**

In `ItemsPage.vue`, change types:

```ts
type ItemActionType = 'move' | 'status' | 'borrow' | 'return' | 'quantity' | 'archive' | 'delete'
type BulkActionType = 'move' | 'status' | 'archive' | 'delete'
```

Update permission guard:

```ts
  if ((action === 'archive' || action === 'delete') && !canArchive.value) return
```

Add handler:

```ts
async function handleDeleteSuccess(_detail: ItemDetail) {
  detailOpen.value = false
  inventory.closeDetail()
  await inventory.loadItems()
}

async function handleDialogSuccess(detail: ItemDetail) {
  if (currentAction.value === 'delete') {
    await handleDeleteSuccess(detail)
    return
  }
  await handleActionSuccess(detail)
}
```

Update `ItemToolbar`:

```vue
@bulk-delete="openBulkAction('delete')"
```

Update `ItemDetailModal`:

```vue
@delete="openActionDialog('delete')"
```

Update `ItemActionDialogs` success binding:

```vue
@success="handleDialogSuccess"
```

- [ ] **Step 8: Run item UI contract**

Run:

```bash
cd frontend
node tests/inventory-bulk-export-contract.mjs
```

Expected: PASS.

---

### Task 7: Full Verification and Cleanup

**Files:**
- All files modified in previous tasks.

- [ ] **Step 1: Run targeted backend tests**

Run:

```bash
cd backend
python -m pytest tests/test_configuration_api.py tests/test_inventory_services.py tests/test_inventory_api.py -q
```

Expected: PASS.

- [ ] **Step 2: Run backend suite**

Run:

```bash
cd backend
python -m pytest -q
```

Expected: PASS.

- [ ] **Step 3: Run frontend contract checks**

Run:

```bash
cd frontend
npx vue-tsc -p tsconfig.contract.json
node tests/config-management-ui-contract.mjs
node tests/inventory-bulk-export-contract.mjs
```

Expected: PASS.

- [ ] **Step 4: Run frontend build**

Run:

```bash
cd frontend
npm run build
```

Expected: PASS.

- [ ] **Step 5: Inspect git diff**

Run:

```bash
git diff --stat
git diff -- backend/app/models/configuration.py backend/app/models/inventory.py backend/app/services/configuration.py backend/app/services/inventory.py frontend/src/components/config/ResidenceLocationPanel.vue frontend/src/pages/ItemsPage.vue
```

Expected: Diff only contains soft-delete related changes.

- [ ] **Step 6: Final status**

Run:

```bash
git status --short
```

Expected: only intended soft-delete files are modified or added.
