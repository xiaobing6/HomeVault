from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.schemas.inventory import (
    ItemCreate,
    ItemDetailResponse,
    ItemListResponse,
    ItemListQuery,
    ItemUpdate,
    LoanCreate,
    PlacementPayload,
    QuantityAdjustmentCreate,
)


def test_item_create_requires_name_and_category() -> None:
    with pytest.raises(ValidationError):
        ItemCreate(name="", category_id=1, status_id=1)

    with pytest.raises(ValidationError):
        ItemCreate(name="证件收纳盒", status_id=1)


def test_item_list_query_defaults_hide_archived_items() -> None:
    assert ItemListQuery().include_archived is False
    assert ItemListQuery().page == 1
    assert ItemListQuery().page_size == 20


def test_item_list_query_rejects_invalid_page_bounds() -> None:
    with pytest.raises(ValidationError):
        ItemListQuery(page=0)

    with pytest.raises(ValidationError):
        ItemListQuery(page_size=101)


def test_item_update_excludes_dedicated_lifecycle_fields() -> None:
    forbidden_fields = {"location_node_id", "container_item_id", "status_id", "quantity"}

    assert forbidden_fields.isdisjoint(ItemUpdate.model_fields)


@pytest.mark.parametrize(
    ("model_type", "payload"),
    [
        (ItemCreate, {"name": "   ", "category_id": 1, "status_id": 1}),
        (QuantityAdjustmentCreate, {"delta": Decimal("1"), "reason": "   "}),
        (LoanCreate, {"borrower_name": "   "}),
    ],
)
def test_required_request_strings_reject_whitespace_only(
    model_type: type[ItemCreate] | type[QuantityAdjustmentCreate] | type[LoanCreate],
    payload: dict[str, object],
) -> None:
    with pytest.raises(ValidationError):
        model_type(**payload)


def test_placement_payload_rejects_location_and_container_together() -> None:
    with pytest.raises(ValidationError):
        PlacementPayload(location_node_id=1, container_item_id=2)


def test_quantity_adjustment_requires_exactly_one_quantity_target() -> None:
    with pytest.raises(ValidationError):
        QuantityAdjustmentCreate(reason="inventory count")

    with pytest.raises(ValidationError):
        QuantityAdjustmentCreate(new_quantity=Decimal("2"), delta=Decimal("1"), reason="inventory count")


def test_item_detail_response_serializes_nested_inventory_payload() -> None:
    now = datetime(2026, 6, 19, 12, 0, tzinfo=timezone.utc)

    response = ItemDetailResponse(
        id=1,
        name="证件收纳盒",
        description="全家证件集中存放",
        category_id=2,
        category_name="证件",
        status_id=3,
        status_name="在库",
        status_semantic="in_inventory",
        quantity=Decimal("2.50"),
        unit="件",
        owner_member_id=4,
        owner_member_name="妈妈",
        keeper_member_id=5,
        keeper_member_name="爸爸",
        location_node_id=6,
        location_node_name="主卧衣柜",
        residence_id=7,
        residence_name="现在住处",
        container_item_id=None,
        container_item_name=None,
        is_container=True,
        privacy_level="normal",
        is_archived=False,
        archive_reason="",
        archived_at=None,
        created_by_id=8,
        updated_by_id=9,
        created_at=now,
        updated_at=now,
        primary_image_url="/api/items/1/images/13/file",
        tags=[
            {
                "id": 10,
                "name": "重要",
                "normalized_name": "重要",
                "created_at": now,
            },
        ],
        attribute_values=[
            {
                "id": 11,
                "attribute_definition_id": 12,
                "attribute_key": "serial_number",
                "attribute_name": "编号",
                "field_type": "text",
                "value": "A-001",
            },
        ],
        images=[
            {
                "id": 13,
                "item_id": 1,
                "original_filename": "box.jpg",
                "stored_filename": "box-1.jpg",
                "file_path": "items/1/images/box-1.jpg",
                "content_type": "image/jpeg",
                "byte_size": 1200,
                "is_primary": True,
                "sort_order": 10,
                "is_archived": False,
                "uploaded_by_id": 8,
                "created_at": now,
                "url": "/api/items/1/images/13/file",
            },
        ],
        attachments=[
            {
                "id": 14,
                "item_id": 1,
                "original_filename": "receipt.pdf",
                "stored_filename": "receipt-1.pdf",
                "file_path": "items/1/attachments/receipt-1.pdf",
                "content_type": "application/pdf",
                "byte_size": 2048,
                "is_archived": False,
                "uploaded_by_id": 8,
                "created_at": now,
                "download_url": "/api/items/1/attachments/14/download",
            },
        ],
        movements=[
            {
                "id": 15,
                "item_id": 1,
                "previous_location_node_id": None,
                "previous_location_node_name": None,
                "new_location_node_id": 6,
                "new_location_node_name": "主卧衣柜",
                "previous_container_item_id": None,
                "previous_container_item_name": None,
                "new_container_item_id": None,
                "new_container_item_name": None,
                "previous_status_id": None,
                "previous_status_name": None,
                "new_status_id": 3,
                "new_status_name": "在库",
                "movement_type": "create",
                "reason": "初始入库",
                "note": "从整理箱迁入",
                "actor_id": 8,
                "created_at": now,
            },
        ],
        quantity_changes=[
            {
                "id": 16,
                "item_id": 1,
                "quantity_before": Decimal("0.00"),
                "quantity_after": Decimal("2.50"),
                "quantity_delta": Decimal("2.50"),
                "unit": "件",
                "reason": "初始数量",
                "note": "",
                "actor_id": 8,
                "created_at": now,
            },
        ],
        loans=[
            {
                "id": 17,
                "item_id": 1,
                "borrower_name": "小姨",
                "borrower_contact": "13800000000",
                "expected_return_date": date(2026, 7, 1),
                "loan_note": "办理证件使用",
                "loaned_at": now,
                "returned_at": None,
                "return_note": "",
                "return_location_node_id": None,
                "return_location_node_name": None,
                "return_container_item_id": None,
                "return_container_item_name": None,
                "loan_actor_id": 8,
                "return_actor_id": None,
                "created_at": now,
                "updated_at": now,
            },
        ],
    )

    serialized = response.model_dump(mode="json")

    assert serialized["quantity"] == "2.50"
    assert serialized["images"][0]["url"] == "/api/items/1/images/13/file"
    assert serialized["attachments"][0]["download_url"] == "/api/items/1/attachments/14/download"
    assert serialized["tags"][0]["name"] == "重要"
    assert serialized["attribute_values"][0]["attribute_key"] == "serial_number"
    assert serialized["movements"][0]["new_location_node_name"] == "主卧衣柜"
    assert serialized["quantity_changes"][0]["quantity_after"] == "2.50"
    assert serialized["loans"][0]["expected_return_date"] == "2026-07-01"


def test_item_list_response_serializes_paged_payload() -> None:
    now = datetime(2026, 6, 19, 12, 0, tzinfo=timezone.utc)

    response = ItemListResponse(
        items=[
            {
                "id": 1,
                "name": "Passport folder",
                "description": "",
                "category_id": 2,
                "category_name": "Documents",
                "status_id": 3,
                "status_name": "In stock",
                "status_semantic": "in_inventory",
                "quantity": Decimal("1.00"),
                "unit": "pcs",
                "location_node_id": None,
                "location_node_name": None,
                "residence_id": None,
                "residence_name": None,
                "container_item_id": None,
                "container_item_name": None,
                "is_container": False,
                "privacy_level": "normal",
                "is_archived": False,
                "tags": [],
                "created_at": now,
                "updated_at": now,
            },
        ],
        total=3,
        page=2,
        page_size=1,
    )

    serialized = response.model_dump(mode="json")

    assert serialized["total"] == 3
    assert serialized["page"] == 2
    assert serialized["page_size"] == 1
    assert serialized["items"][0]["quantity"] == "1.00"
