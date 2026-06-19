from __future__ import annotations

from decimal import Decimal

import pytest
from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.auth import User
from app.models.configuration import (
    AttributeDefinition,
    AttributeOption,
    Category,
    FamilyMember,
    HomeSpace,
    ItemStatus,
    LocationNode,
    Residence,
)
from app.models.inventory import Item, ItemLoan, ItemQuantityChange, Tag
from app.schemas.inventory import ItemCreate, ItemListQuery, ItemUpdate
from app.services.inventory import archive_item, create_item, get_item_detail, list_items, update_item


@pytest.fixture()
def inventory_seed(db_session: Session) -> dict[str, object]:
    creator = User(id=42, username="creator", password_hash="hash", display_name="Creator")
    editor = User(id=7, username="editor", password_hash="hash", display_name="Editor")
    archiver = User(id=99, username="archiver", password_hash="hash", display_name="Archiver")
    home = HomeSpace(name="Home")
    residence = Residence(name="Main residence", home_space=home)
    closet = LocationNode(residence=residence, name="Bedroom closet", node_type="cabinet", sort_order=10)
    drawer = LocationNode(residence=residence, parent=closet, name="Top drawer", node_type="drawer", sort_order=20)
    member = FamilyMember(home_space=home, name="Alex", relation="owner")
    category = Category(code="documents", name="Documents", sort_order=10)
    expire_date = AttributeDefinition(
        category=category,
        key="expire_date",
        name="Expire date",
        field_type="date",
        is_required=True,
        sort_order=10,
    )
    serial_number = AttributeDefinition(
        category=category,
        key="serial_number",
        name="Serial number",
        field_type="text",
        sort_order=20,
    )
    importance = AttributeDefinition(
        category=category,
        key="importance",
        name="Importance",
        field_type="single_select",
        sort_order=30,
    )
    purchase_price = AttributeDefinition(
        category=category,
        key="purchase_price",
        name="Purchase price",
        field_type="money",
        sort_order=40,
    )
    warranty_date = AttributeDefinition(
        category=category,
        key="warranty_date",
        name="Warranty date",
        field_type="date",
        sort_order=50,
    )
    verified = AttributeDefinition(
        category=category,
        key="verified",
        name="Verified",
        field_type="boolean",
        sort_order=60,
    )
    storage_flags = AttributeDefinition(
        category=category,
        key="storage_flags",
        name="Storage flags",
        field_type="multi_select",
        sort_order=70,
    )
    AttributeOption(definition=importance, label="High", value="high", sort_order=10)
    AttributeOption(definition=importance, label="Low", value="low", sort_order=20)
    AttributeOption(definition=storage_flags, label="Dry", value="dry", sort_order=10)
    AttributeOption(definition=storage_flags, label="Cold", value="cold", sort_order=20)
    in_stock = ItemStatus(code="in_stock", name="In stock", semantic="in_inventory", sort_order=10, is_system=True)
    loaned = ItemStatus(code="loaned", name="Loaned", semantic="away", sort_order=20, is_system=True)
    db_session.add_all([creator, editor, archiver, home, category, in_stock, loaned])
    db_session.commit()

    return {
        "home": home,
        "residence": residence,
        "closet": closet,
        "drawer": drawer,
        "member": member,
        "category": category,
        "expire_date": expire_date,
        "serial_number": serial_number,
        "importance": importance,
        "purchase_price": purchase_price,
        "warranty_date": warranty_date,
        "verified": verified,
        "storage_flags": storage_flags,
        "in_stock": in_stock,
        "loaned": loaned,
    }


def make_create_payload(seed: dict[str, object], **overrides: object) -> ItemCreate:
    category = seed["category"]
    status = seed["in_stock"]
    drawer = seed["drawer"]
    member = seed["member"]
    expire_date = seed["expire_date"]
    serial_number = seed["serial_number"]
    importance = seed["importance"]
    payload = {
        "name": "Passport folder",
        "description": "Family identity documents",
        "category_id": category.id,
        "status_id": status.id,
        "quantity": Decimal("2.00"),
        "unit": "pcs",
        "owner_member_id": member.id,
        "keeper_member_id": member.id,
        "location_node_id": drawer.id,
        "is_container": True,
        "privacy_level": "normal",
        "attribute_values": [
            {"attribute_definition_id": expire_date.id, "value": "2030-12-31"},
            {"attribute_definition_id": serial_number.id, "value": "SN-001"},
            {"attribute_definition_id": importance.id, "value": "high"},
        ],
        "tags": ["Important", " Travel "],
    }
    payload.update(overrides)
    return ItemCreate(**payload)


def test_create_item_persists_custom_values_tags_initial_quantity_and_location(
    db_session: Session,
    inventory_seed: dict[str, object],
) -> None:
    detail = create_item(db_session, make_create_payload(inventory_seed), actor_id=42)

    item = db_session.get(Item, detail.id)
    quantity_change = db_session.scalar(
        select(ItemQuantityChange).where(ItemQuantityChange.item_id == detail.id)
    )

    assert item is not None
    assert item.name == "Passport folder"
    assert item.location_node_id == inventory_seed["drawer"].id
    assert item.container_item_id is None
    assert item.quantity == Decimal("2.00")
    assert {value.attribute_definition.key: value.value for value in item.attribute_values} == {
        "expire_date": "2030-12-31",
        "serial_number": "SN-001",
        "importance": "high",
    }
    assert [link.tag.normalized_name for link in item.tag_links] == ["important", "travel"]
    assert quantity_change is not None
    assert quantity_change.quantity_before == Decimal("0.00")
    assert quantity_change.quantity_after == Decimal("2.00")
    assert quantity_change.actor_id == 42
    assert detail.location_node_name == "Top drawer"
    assert [tag.normalized_name for tag in detail.tags] == ["important", "travel"]


def test_create_item_normalizes_custom_values_for_persistence(
    db_session: Session,
    inventory_seed: dict[str, object],
) -> None:
    expire_date = inventory_seed["expire_date"]
    purchase_price = inventory_seed["purchase_price"]
    warranty_date = inventory_seed["warranty_date"]
    verified = inventory_seed["verified"]
    storage_flags = inventory_seed["storage_flags"]

    detail = create_item(
        db_session,
        make_create_payload(
            inventory_seed,
            attribute_values=[
                {"attribute_definition_id": expire_date.id, "value": "2030-12-31"},
                {"attribute_definition_id": purchase_price.id, "value": "0012.3400"},
                {"attribute_definition_id": warranty_date.id, "value": " 2028-01-05 "},
                {"attribute_definition_id": verified.id, "value": "YES"},
                {"attribute_definition_id": storage_flags.id, "value": "cold, dry"},
            ],
        ),
    )

    values = {
        value.attribute_key: value.value
        for value in get_item_detail(db_session, detail.id).attribute_values
    }

    assert values["purchase_price"] == "12.34"
    assert values["warranty_date"] == "2028-01-05"
    assert values["verified"] == "true"
    assert values["storage_flags"] == '["cold","dry"]'


def test_create_item_rejects_required_missing_custom_value(
    db_session: Session,
    inventory_seed: dict[str, object],
) -> None:
    serial_number = inventory_seed["serial_number"]
    importance = inventory_seed["importance"]

    with pytest.raises(HTTPException) as exc_info:
        create_item(
            db_session,
            make_create_payload(
                inventory_seed,
                attribute_values=[
                    {"attribute_definition_id": serial_number.id, "value": "SN-001"},
                    {"attribute_definition_id": importance.id, "value": "high"},
                ],
            ),
        )

    assert exc_info.value.status_code == 400
    assert "Expire date" in exc_info.value.detail["message"]


def test_create_item_rejects_invalid_select_value(
    db_session: Session,
    inventory_seed: dict[str, object],
) -> None:
    expire_date = inventory_seed["expire_date"]
    importance = inventory_seed["importance"]

    with pytest.raises(HTTPException) as exc_info:
        create_item(
            db_session,
            make_create_payload(
                inventory_seed,
                attribute_values=[
                    {"attribute_definition_id": expire_date.id, "value": "2030-12-31"},
                    {"attribute_definition_id": importance.id, "value": "urgent"},
                ],
            ),
        )

    assert exc_info.value.status_code == 400
    assert "Importance" in exc_info.value.detail["message"]


def test_list_items_searches_name_tag_and_custom_value(
    db_session: Session,
    inventory_seed: dict[str, object],
) -> None:
    create_item(db_session, make_create_payload(inventory_seed, name="Passport folder", tags=["Travel"]))
    create_item(db_session, make_create_payload(inventory_seed, name="Camera case", tags=["Photo"]))

    by_name = list_items(db_session, ItemListQuery(search="passport"))
    by_tag = list_items(db_session, ItemListQuery(search="photo"))
    by_custom_value = list_items(db_session, ItemListQuery(search="SN-001"))

    assert [item.name for item in by_name.items] == ["Passport folder"]
    assert [item.name for item in by_tag.items] == ["Camera case"]
    assert [item.name for item in by_custom_value.items] == ["Camera case", "Passport folder"]
    assert by_custom_value.total == 2
    assert by_custom_value.page == 1
    assert by_custom_value.page_size == 20


def test_list_items_returns_pagination_metadata_and_slices_results(
    db_session: Session,
    inventory_seed: dict[str, object],
) -> None:
    create_item(db_session, make_create_payload(inventory_seed, name="Alpha"))
    create_item(db_session, make_create_payload(inventory_seed, name="Bravo"))
    create_item(db_session, make_create_payload(inventory_seed, name="Charlie"))

    page = list_items(db_session, ItemListQuery(sort="name_asc", page=2, page_size=1))

    assert [item.name for item in page.items] == ["Bravo"]
    assert page.total == 3
    assert page.page == 2
    assert page.page_size == 1


def test_list_items_filters_by_container_placement(
    db_session: Session,
    inventory_seed: dict[str, object],
) -> None:
    container = create_item(db_session, make_create_payload(inventory_seed, name="Document box"))
    create_item(
        db_session,
        make_create_payload(
            inventory_seed,
            name="Birth certificate",
            location_node_id=None,
            container_item_id=container.id,
            is_container=False,
        ),
    )
    create_item(db_session, make_create_payload(inventory_seed, name="Loose passport"))

    placed_in_container = list_items(db_session, ItemListQuery(container_item_id=container.id))

    assert [item.name for item in placed_in_container.items] == ["Birth certificate"]
    assert placed_in_container.total == 1


def test_list_items_on_loan_false_excludes_active_loan_even_when_status_is_in_stock(
    db_session: Session,
    inventory_seed: dict[str, object],
) -> None:
    created = create_item(db_session, make_create_payload(inventory_seed, name="Borrowed passport"))
    db_session.add(ItemLoan(item_id=created.id, borrower_name="Taylor"))
    db_session.commit()

    on_loan = list_items(db_session, ItemListQuery(is_on_loan=True))
    not_on_loan = list_items(db_session, ItemListQuery(is_on_loan=False))

    assert [item.name for item in on_loan.items] == ["Borrowed passport"]
    assert [item.name for item in not_on_loan.items] == []


def test_create_item_rolls_back_and_returns_bad_request_when_flush_raises_integrity_error(
    db_session: Session,
    inventory_seed: dict[str, object],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original_flush = db_session.flush

    def fail_once(*args: object, **kwargs: object) -> object:
        monkeypatch.setattr(db_session, "flush", original_flush)
        raise IntegrityError("insert items", {}, Exception("forced flush failure"))

    monkeypatch.setattr(db_session, "flush", fail_once)

    with pytest.raises(HTTPException) as exc_info:
        create_item(db_session, make_create_payload(inventory_seed, name="Broken item"))

    assert exc_info.value.status_code == 400
    assert db_session.scalar(select(Item).where(Item.name == "Broken item")) is None


def test_item_detail_includes_tags_custom_values_and_paths(
    db_session: Session,
    inventory_seed: dict[str, object],
) -> None:
    created = create_item(db_session, make_create_payload(inventory_seed))

    detail = get_item_detail(db_session, created.id)

    assert detail.category_name == "Documents"
    assert detail.status_name == "In stock"
    assert detail.location_node_name == "Top drawer"
    assert detail.residence_name == "Main residence"
    assert [tag.name for tag in detail.tags] == ["Important", "Travel"]
    assert {value.attribute_key: value.value for value in detail.attribute_values} == {
        "expire_date": "2030-12-31",
        "serial_number": "SN-001",
        "importance": "high",
    }
    assert detail.images == []
    assert detail.attachments == []


def test_update_item_does_not_change_quantity_silently(
    db_session: Session,
    inventory_seed: dict[str, object],
) -> None:
    created = create_item(db_session, make_create_payload(inventory_seed))
    serial_number = inventory_seed["serial_number"]

    updated = update_item(
        db_session,
        created.id,
        ItemUpdate(
            name="Updated passport folder",
            attribute_values=[{"attribute_definition_id": serial_number.id, "value": "SN-002"}],
            tags=["Updated"],
        ),
        actor_id=7,
    )
    item = db_session.get(Item, created.id)
    quantity_changes = db_session.scalars(
        select(ItemQuantityChange).where(ItemQuantityChange.item_id == created.id)
    ).all()

    assert updated.name == "Updated passport folder"
    assert item is not None
    assert item.quantity == Decimal("2.00")
    assert item.status_id == inventory_seed["in_stock"].id
    assert item.location_node_id == inventory_seed["drawer"].id
    assert item.container_item_id is None
    assert len(quantity_changes) == 1


def test_archive_item_hides_from_default_list(
    db_session: Session,
    inventory_seed: dict[str, object],
) -> None:
    created = create_item(db_session, make_create_payload(inventory_seed))

    archived = archive_item(db_session, created.id, actor_id=99)

    assert archived.is_archived is True
    assert list_items(db_session, ItemListQuery()).items == []
    assert [item.id for item in list_items(db_session, ItemListQuery(include_archived=True)).items] == [created.id]
    assert db_session.scalar(select(Tag).where(Tag.normalized_name == "important")) is not None
