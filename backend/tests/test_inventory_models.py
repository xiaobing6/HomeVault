from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.base import Base
from app.models.configuration import (
    AttributeDefinition,
    Category,
    FamilyMember,
    HomeSpace,
    ItemStatus,
    LocationNode,
    Residence,
)


def test_inventory_tables_are_registered() -> None:
    table_names = set(Base.metadata.tables)

    assert {
        "items",
        "item_attribute_values",
        "item_images",
        "item_attachments",
        "tags",
        "item_tags",
        "item_movements",
        "item_quantity_changes",
        "item_loans",
    }.issubset(table_names)


def test_inventory_models_persist_item_with_tag_media_history_and_loan(db_session: Session) -> None:
    from app.models.inventory import (
        Item,
        ItemAttachment,
        ItemAttributeValue,
        ItemImage,
        ItemLoan,
        ItemMovement,
        ItemQuantityChange,
        ItemTag,
        Tag,
    )

    home = HomeSpace(name="我们家", description="家庭物品空间")
    residence = Residence(name="现在住处", home_space=home, description="主住处")
    location = LocationNode(residence=residence, name="主卧衣柜", node_type="cabinet", sort_order=10)
    member = FamilyMember(home_space=home, name="妈妈", relation="家人")
    category = Category(code="documents", name="证件", sort_order=10)
    attribute_definition = AttributeDefinition(
        category=category,
        key="serial_number",
        name="编号",
        field_type="text",
        sort_order=10,
    )
    status = ItemStatus(code="in_stock", name="在库", semantic="in_inventory", sort_order=10, is_system=True)
    tag = Tag(name="重要", normalized_name="重要")
    item = Item(
        name="证件收纳盒",
        description="全家证件集中存放",
        category=category,
        status=status,
        quantity=Decimal("1.00"),
        unit="盒",
        owner_member=member,
        keeper_member=member,
        location_node=location,
        is_container=True,
    )
    item.attribute_values.append(ItemAttributeValue(attribute_definition=attribute_definition, value="A-001"))
    item.tag_links.append(ItemTag(tag=tag))
    item.images.append(
        ItemImage(
            original_filename="box.jpg",
            stored_filename="box-1.jpg",
            file_path="/uploads/items/box-1.jpg",
            content_type="image/jpeg",
            byte_size=1200,
            is_primary=True,
            sort_order=10,
        )
    )
    item.attachments.append(
        ItemAttachment(
            original_filename="receipt.pdf",
            stored_filename="receipt-1.pdf",
            file_path="/uploads/items/receipt-1.pdf",
            content_type="application/pdf",
            byte_size=2048,
        )
    )
    item.movements.append(
        ItemMovement(
            new_location_node=location,
            new_status=status,
            movement_type="create",
            reason="初始入库",
            note="从整理箱迁入",
        )
    )
    item.quantity_changes.append(
        ItemQuantityChange(
            quantity_before=Decimal("0.00"),
            quantity_after=Decimal("1.00"),
            quantity_delta=Decimal("1.00"),
            unit="盒",
            reason="初始数量",
        )
    )
    item.loans.append(
        ItemLoan(
            borrower_name="小姨",
            borrower_contact="13800000000",
            expected_return_date=date(2026, 7, 1),
            loan_note="办理证件使用",
        )
    )
    db_session.add(item)
    db_session.commit()

    saved_item = db_session.scalar(select(Item).where(Item.name == "证件收纳盒"))

    assert saved_item is not None
    assert saved_item.category.name == "证件"
    assert saved_item.status.code == "in_stock"
    assert saved_item.owner_member.name == "妈妈"
    assert saved_item.keeper_member.name == "妈妈"
    assert saved_item.location_node.name == "主卧衣柜"
    assert saved_item.container_item is None
    assert saved_item.attribute_values[0].attribute_definition.key == "serial_number"
    assert saved_item.attribute_values[0].value == "A-001"
    assert saved_item.tag_links[0].tag.normalized_name == "重要"
    assert saved_item.images[0].original_filename == "box.jpg"
    assert saved_item.images[0].is_primary is True
    assert saved_item.attachments[0].original_filename == "receipt.pdf"
    assert saved_item.movements[0].new_location_node.name == "主卧衣柜"
    assert saved_item.movements[0].new_status.code == "in_stock"
    assert saved_item.quantity_changes[0].quantity_after == Decimal("1.00")
    assert saved_item.loans[0].borrower_name == "小姨"
    assert saved_item.loans[0].expected_return_date == date(2026, 7, 1)


def test_item_location_and_container_are_mutually_exclusive(db_session: Session) -> None:
    from app.models.inventory import Item

    home = HomeSpace(name="我们家")
    residence = Residence(name="现在住处", home_space=home)
    location = LocationNode(residence=residence, name="玄关柜", node_type="cabinet")
    category = Category(code="documents", name="证件")
    status = ItemStatus(code="in_stock", name="在库", semantic="in_inventory", is_system=True)
    container = Item(
        name="证件箱",
        category=category,
        status=status,
        location_node=location,
        is_container=True,
    )
    db_session.add(container)
    db_session.commit()

    db_session.add(
        Item(
            name="不能同时放两个地方的物品",
            category=category,
            status=status,
            location_node=location,
            container_item=container,
        )
    )

    with pytest.raises(IntegrityError):
        db_session.commit()


def test_item_loans_reject_duplicate_active_loan_for_same_item(db_session: Session) -> None:
    from app.models.inventory import Item, ItemLoan

    home = HomeSpace(name="Home")
    residence = Residence(name="Main residence", home_space=home)
    location = LocationNode(residence=residence, name="Closet", node_type="cabinet")
    category = Category(code="documents", name="Documents")
    status = ItemStatus(code="in_stock", name="In stock", semantic="in_inventory", is_system=True)
    item = Item(
        name="Passport",
        category=category,
        status=status,
        location_node=location,
    )
    item.loans.append(ItemLoan(borrower_name="Taylor"))
    item.loans.append(ItemLoan(borrower_name="Jordan"))
    db_session.add(item)

    with pytest.raises(IntegrityError):
        db_session.commit()


def test_item_images_reject_duplicate_active_primary_for_same_item(db_session: Session) -> None:
    from app.models.inventory import Item, ItemImage

    home = HomeSpace(name="Home")
    residence = Residence(name="Main residence", home_space=home)
    location = LocationNode(residence=residence, name="Closet", node_type="cabinet")
    category = Category(code="documents", name="Documents")
    status = ItemStatus(code="in_stock", name="In stock", semantic="in_inventory", is_system=True)
    item = Item(
        name="Passport",
        category=category,
        status=status,
        location_node=location,
    )
    item.images.append(
        ItemImage(
            original_filename="front.jpg",
            stored_filename="front.jpg",
            file_path="items/1/images/front.jpg",
            content_type="image/jpeg",
            byte_size=10,
            is_primary=True,
        )
    )
    item.images.append(
        ItemImage(
            original_filename="back.jpg",
            stored_filename="back.jpg",
            file_path="items/1/images/back.jpg",
            content_type="image/jpeg",
            byte_size=10,
            is_primary=True,
        )
    )
    db_session.add(item)

    with pytest.raises(IntegrityError):
        db_session.commit()
