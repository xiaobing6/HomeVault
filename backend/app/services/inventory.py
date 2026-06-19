from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation
import json

from fastapi import HTTPException, status
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.core.errors import bad_request
from app.models.configuration import (
    AttributeDefinition,
    AttributeOption,
    Category,
    FamilyMember,
    ItemStatus,
    LocationNode,
)
from app.models.inventory import (
    Item,
    ItemAttributeValue,
    ItemLoan,
    ItemMovement,
    ItemQuantityChange,
    ItemTag,
    Tag,
)
from app.schemas.inventory import (
    ArchiveItemRequest,
    ItemAttachmentResponse,
    ItemAttributeValueInput,
    ItemAttributeValueResponse,
    ItemCreate,
    ItemDetailResponse,
    ItemListResponse,
    ItemImageResponse,
    ItemListQuery,
    ItemLoanResponse,
    ItemMovementResponse,
    ItemQuantityChangeResponse,
    ItemSummaryResponse,
    ItemUpdate,
    TagResponse,
)

try:
    from app.core.errors import not_found
except ImportError:

    def not_found(message: str) -> HTTPException:
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={"message": message})


MAX_CONTAINER_DEPTH = 5
EXIT_STATUS_SEMANTICS = {"removed", "missing", "consumed"}
INITIAL_QUANTITY_REASON = "\u521d\u59cb\u6570\u91cf"


@dataclass(frozen=True)
class PlacementTarget:
    location_node: LocationNode | None
    container_item: Item | None


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def normalize_tag(name: str) -> str:
    return " ".join(name.strip().lower().split())


def require_item(db: Session, item_id: int) -> Item:
    item = db.get(Item, item_id)
    if item is None:
        raise not_found("\u7269\u54c1\u4e0d\u5b58\u5728")
    return item


def commit_or_bad_request(db: Session, message: str) -> None:
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise bad_request(message) from exc


def require_active_category(db: Session, category_id: int) -> Category:
    category = db.get(Category, category_id)
    if category is None or not category.is_active:
        raise bad_request("\u5206\u7c7b\u4e0d\u5b58\u5728")
    return category


def require_active_status(db: Session, status_id: int) -> ItemStatus:
    item_status = db.get(ItemStatus, status_id)
    if item_status is None or not item_status.is_active:
        raise bad_request("\u72b6\u6001\u4e0d\u5b58\u5728")
    return item_status


def assert_member_exists(db: Session, member_id: int | None) -> None:
    if member_id is None:
        return
    member = db.get(FamilyMember, member_id)
    if member is None or not member.is_active:
        raise bad_request("\u5bb6\u5ead\u6210\u5458\u4e0d\u5b58\u5728")


def validate_basic_placement(
    db: Session,
    status: ItemStatus,
    location_node_id: int | None,
    container_item_id: int | None,
    current_item_id: int | None = None,
) -> PlacementTarget:
    if location_node_id is not None and container_item_id is not None:
        raise bad_request("\u8bf7\u9009\u62e9\u4f4d\u7f6e\u6216\u5bb9\u5668\uff0c\u4e0d\u80fd\u540c\u65f6\u9009\u62e9\u4e24\u8005")
    if status.semantic not in EXIT_STATUS_SEMANTICS and location_node_id is None and container_item_id is None:
        raise bad_request("\u8bf7\u9009\u62e9\u4f4d\u7f6e\u6216\u5bb9\u5668")

    location_node: LocationNode | None = None
    container_item: Item | None = None
    if location_node_id is not None:
        location_node = db.get(LocationNode, location_node_id)
        if location_node is None or not location_node.is_active:
            raise bad_request("\u4f4d\u7f6e\u4e0d\u5b58\u5728")

    if container_item_id is not None:
        if current_item_id is not None and container_item_id == current_item_id:
            raise bad_request("\u4e0d\u80fd\u5c06\u7269\u54c1\u653e\u5165\u81ea\u5df1")
        container_item = db.get(Item, container_item_id)
        if container_item is None or container_item.is_archived:
            raise bad_request("\u5bb9\u5668\u4e0d\u5b58\u5728")
        if not container_item.is_container:
            raise bad_request("\u76ee\u6807\u7269\u54c1\u4e0d\u662f\u5bb9\u5668")
        assert_container_depth(db, container_item, current_item_id=current_item_id)

    return PlacementTarget(location_node=location_node, container_item=container_item)


def assert_container_depth(db: Session, container_item: Item, current_item_id: int | None = None) -> None:
    depth = 1
    visited: set[int] = set()
    next_item: Item | None = container_item
    while next_item is not None:
        if next_item.id in visited:
            raise bad_request("\u5bb9\u5668\u5c42\u7ea7\u4e0d\u5408\u6cd5")
        if current_item_id is not None and next_item.id == current_item_id:
            raise bad_request("\u4e0d\u80fd\u5c06\u7269\u54c1\u653e\u5165\u81ea\u5df1")
        visited.add(next_item.id)
        if depth >= MAX_CONTAINER_DEPTH:
            raise bad_request("\u5bb9\u5668\u5c42\u7ea7\u8fc7\u6df1")
        if next_item.container_item_id is None:
            return
        next_item = db.get(Item, next_item.container_item_id)
        depth += 1


def validate_attribute_values(
    db: Session,
    category_id: int,
    values: list[ItemAttributeValueInput],
) -> dict[int, str]:
    definitions = db.scalars(
        select(AttributeDefinition)
        .where(AttributeDefinition.category_id == category_id)
        .options(selectinload(AttributeDefinition.options))
    ).all()
    active_definitions = [definition for definition in definitions if definition.is_active]
    active_definition_by_id = {definition.id: definition for definition in active_definitions}
    value_by_definition_id: dict[int, str] = {}

    for value in values:
        definition = active_definition_by_id.get(value.attribute_definition_id)
        if definition is None:
            raise bad_request("\u81ea\u5b9a\u4e49\u5b57\u6bb5\u4e0d\u5b58\u5728")
        value_by_definition_id[value.attribute_definition_id] = str(value.value or "")

    for definition in active_definitions:
        raw_value = value_by_definition_id.get(definition.id, "").strip()
        if definition.is_required and raw_value == "":
            raise bad_request(f"{definition.name}\u4e0d\u80fd\u4e3a\u7a7a")
        if raw_value == "":
            continue
        value_by_definition_id[definition.id] = normalize_attribute_value(definition, raw_value)

    return {
        definition_id: raw_value.strip()
        for definition_id, raw_value in value_by_definition_id.items()
    }


def assert_attribute_value_matches_definition(
    definition: AttributeDefinition,
    raw_value: str,
) -> None:
    field_type = definition.field_type
    if field_type in {"number", "money"}:
        assert_decimal_value(definition, raw_value)
        return
    if field_type == "date":
        assert_date_value(definition, raw_value)
        return
    if field_type == "datetime":
        assert_datetime_value(definition, raw_value)
        return
    if field_type == "boolean":
        assert_boolean_value(definition, raw_value)
        return
    if field_type == "single_select":
        assert_single_select_value(definition, raw_value)
        return
    if field_type == "multi_select":
        assert_multi_select_value(definition, raw_value)


def normalize_attribute_value(definition: AttributeDefinition, raw_value: str) -> str:
    field_type = definition.field_type
    if field_type in {"number", "money"}:
        return normalize_decimal_value(definition, raw_value)
    if field_type == "date":
        return normalize_date_value(definition, raw_value)
    if field_type == "datetime":
        return normalize_datetime_value(definition, raw_value)
    if field_type == "boolean":
        return normalize_boolean_value(definition, raw_value)
    if field_type == "single_select":
        assert_single_select_value(definition, raw_value)
        return raw_value
    if field_type == "multi_select":
        selected_values = parse_multi_select_value(definition, raw_value)
        allowed_values = active_option_values(definition)
        if not selected_values or any(value not in allowed_values for value in selected_values):
            raise bad_request(f"{definition.name}\u9009\u9879\u4e0d\u5408\u6cd5")
        return json.dumps(selected_values, ensure_ascii=False, separators=(",", ":"))
    assert_attribute_value_matches_definition(definition, raw_value)
    return raw_value.strip()


def normalize_decimal_value(definition: AttributeDefinition, raw_value: str) -> str:
    try:
        value = Decimal(raw_value)
    except (InvalidOperation, ValueError) as exc:
        raise bad_request(f"{definition.name}\u683c\u5f0f\u4e0d\u6b63\u786e") from exc
    if not value.is_finite():
        raise bad_request(f"{definition.name}\u683c\u5f0f\u4e0d\u6b63\u786e")
    normalized = format(value.normalize(), "f")
    if "." in normalized:
        normalized = normalized.rstrip("0").rstrip(".")
    return normalized or "0"


def normalize_date_value(definition: AttributeDefinition, raw_value: str) -> str:
    try:
        return date.fromisoformat(raw_value).isoformat()
    except ValueError as exc:
        raise bad_request(f"{definition.name}\u683c\u5f0f\u4e0d\u6b63\u786e") from exc


def normalize_datetime_value(definition: AttributeDefinition, raw_value: str) -> str:
    try:
        return datetime.fromisoformat(raw_value.replace("Z", "+00:00")).isoformat()
    except ValueError as exc:
        raise bad_request(f"{definition.name}\u683c\u5f0f\u4e0d\u6b63\u786e") from exc


def normalize_boolean_value(definition: AttributeDefinition, raw_value: str) -> str:
    normalized = raw_value.strip().lower()
    if normalized in {"true", "1", "yes"}:
        return "true"
    if normalized in {"false", "0", "no"}:
        return "false"
    raise bad_request(f"{definition.name}\u683c\u5f0f\u4e0d\u6b63\u786e")


def assert_decimal_value(definition: AttributeDefinition, raw_value: str) -> None:
    try:
        value = Decimal(raw_value)
    except (InvalidOperation, ValueError) as exc:
        raise bad_request(f"{definition.name}\u683c\u5f0f\u4e0d\u6b63\u786e") from exc
    if not value.is_finite():
        raise bad_request(f"{definition.name}\u683c\u5f0f\u4e0d\u6b63\u786e")


def assert_date_value(definition: AttributeDefinition, raw_value: str) -> None:
    try:
        date.fromisoformat(raw_value)
    except ValueError as exc:
        raise bad_request(f"{definition.name}\u683c\u5f0f\u4e0d\u6b63\u786e") from exc


def assert_datetime_value(definition: AttributeDefinition, raw_value: str) -> None:
    try:
        datetime.fromisoformat(raw_value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise bad_request(f"{definition.name}\u683c\u5f0f\u4e0d\u6b63\u786e") from exc


def assert_boolean_value(definition: AttributeDefinition, raw_value: str) -> None:
    if raw_value.strip().lower() not in {"true", "false", "1", "0", "yes", "no"}:
        raise bad_request(f"{definition.name}\u683c\u5f0f\u4e0d\u6b63\u786e")


def active_option_values(definition: AttributeDefinition) -> set[str]:
    return {option.value for option in definition.options if option.is_active}


def assert_single_select_value(definition: AttributeDefinition, raw_value: str) -> None:
    if raw_value not in active_option_values(definition):
        raise bad_request(f"{definition.name}\u9009\u9879\u4e0d\u5408\u6cd5")


def assert_multi_select_value(definition: AttributeDefinition, raw_value: str) -> None:
    selected_values = parse_multi_select_value(definition, raw_value)
    allowed_values = active_option_values(definition)
    if not selected_values or any(value not in allowed_values for value in selected_values):
        raise bad_request(f"{definition.name}\u9009\u9879\u4e0d\u5408\u6cd5")


def parse_multi_select_value(definition: AttributeDefinition, raw_value: str) -> list[str]:
    stripped_value = raw_value.strip()
    if stripped_value.startswith("["):
        try:
            parsed = json.loads(stripped_value)
        except json.JSONDecodeError as exc:
            raise bad_request(f"{definition.name}\u683c\u5f0f\u4e0d\u6b63\u786e") from exc
        if not isinstance(parsed, list) or any(not isinstance(item, str) for item in parsed):
            raise bad_request(f"{definition.name}\u683c\u5f0f\u4e0d\u6b63\u786e")
        return [item.strip() for item in parsed if item.strip()]
    return [item.strip() for item in stripped_value.split(",") if item.strip()]


def create_item(db: Session, payload: ItemCreate, actor_id: int | None = None) -> ItemDetailResponse:
    name = payload.name.strip()
    if name == "":
        raise bad_request("\u7269\u54c1\u540d\u79f0\u4e0d\u80fd\u4e3a\u7a7a")

    category = require_active_category(db, payload.category_id)
    item_status = require_active_status(db, payload.status_id)
    placement = validate_basic_placement(
        db,
        item_status,
        payload.location_node_id,
        payload.container_item_id,
    )
    assert_member_exists(db, payload.owner_member_id)
    assert_member_exists(db, payload.keeper_member_id)
    attribute_values = validate_attribute_values(db, category.id, payload.attribute_values)

    item = Item(
        name=name,
        description=payload.description,
        category_id=category.id,
        status_id=item_status.id,
        quantity=payload.quantity,
        unit=payload.unit,
        owner_member_id=payload.owner_member_id,
        keeper_member_id=payload.keeper_member_id,
        location_node_id=placement.location_node.id if placement.location_node is not None else None,
        container_item_id=placement.container_item.id if placement.container_item is not None else None,
        is_container=payload.is_container,
        privacy_level=payload.privacy_level,
        created_by_id=actor_id,
        updated_by_id=actor_id,
    )
    db.add(item)
    db.flush()
    replace_attribute_values(db, item, attribute_values)
    replace_tags(db, item, payload.tags)
    db.add(
        ItemQuantityChange(
            item_id=item.id,
            quantity_before=Decimal("0.00"),
            quantity_after=payload.quantity,
            quantity_delta=payload.quantity,
            unit=payload.unit,
            reason=INITIAL_QUANTITY_REASON,
            note="",
            actor_id=actor_id,
        )
    )
    item_id = item.id
    commit_or_bad_request(db, "\u7269\u54c1\u4fdd\u5b58\u5931\u8d25")
    return get_item_detail(db, item_id)


def update_item(
    db: Session,
    item_id: int,
    payload: ItemUpdate,
    actor_id: int | None = None,
) -> ItemDetailResponse:
    item = require_item(db, item_id)
    fields = payload.model_fields_set
    category_supplied = "category_id" in fields and payload.category_id is not None
    attributes_supplied = "attribute_values" in fields and payload.attribute_values is not None
    target_category_id = payload.category_id if category_supplied else item.category_id

    if category_supplied:
        require_active_category(db, target_category_id)
    if "owner_member_id" in fields:
        assert_member_exists(db, payload.owner_member_id)
    if "keeper_member_id" in fields:
        assert_member_exists(db, payload.keeper_member_id)
    if category_supplied or attributes_supplied:
        if category_supplied:
            incoming_values = payload.attribute_values if attributes_supplied else []
        else:
            incoming_values = merge_attribute_values_for_update(item, payload.attribute_values or [])
        attribute_values = validate_attribute_values(db, target_category_id, incoming_values)
    else:
        attribute_values = None

    if "name" in fields and payload.name is not None:
        name = payload.name.strip()
        if name == "":
            raise bad_request("\u7269\u54c1\u540d\u79f0\u4e0d\u80fd\u4e3a\u7a7a")
        item.name = name
    if "description" in fields:
        item.description = payload.description or ""
    if category_supplied:
        item.category_id = target_category_id
    if "unit" in fields and payload.unit is not None:
        unit = payload.unit.strip()
        if unit == "":
            raise bad_request("\u5355\u4f4d\u4e0d\u80fd\u4e3a\u7a7a")
        item.unit = unit
    if "owner_member_id" in fields:
        item.owner_member_id = payload.owner_member_id
    if "keeper_member_id" in fields:
        item.keeper_member_id = payload.keeper_member_id
    if "is_container" in fields and payload.is_container is not None:
        item.is_container = payload.is_container
    if "privacy_level" in fields and payload.privacy_level is not None:
        item.privacy_level = payload.privacy_level
    if attribute_values is not None:
        replace_attribute_values(db, item, attribute_values)
    if "tags" in fields and payload.tags is not None:
        replace_tags(db, item, payload.tags)
    item.updated_by_id = actor_id

    commit_or_bad_request(db, "\u7269\u54c1\u4fdd\u5b58\u5931\u8d25")
    return get_item_detail(db, item_id)


def archive_item(
    db: Session,
    item_id: int,
    payload: ArchiveItemRequest | None = None,
    actor_id: int | None = None,
) -> ItemDetailResponse:
    item = require_item(db, item_id)
    archive_payload = payload or ArchiveItemRequest()
    item.is_archived = True
    item.archive_reason = archive_payload.archive_reason
    item.archived_at = utcnow()
    item.updated_by_id = actor_id
    commit_or_bad_request(db, "\u7269\u54c1\u4fdd\u5b58\u5931\u8d25")
    return get_item_detail(db, item_id)


def list_items(db: Session, query: ItemListQuery) -> ItemListResponse:
    stmt = select(Item)
    if not query.include_archived:
        stmt = stmt.where(Item.is_archived.is_(False))
    if query.category_id is not None:
        stmt = stmt.where(Item.category_id == query.category_id)
    if query.status_id is not None:
        stmt = stmt.where(Item.status_id == query.status_id)
    if query.location_node_id is not None:
        stmt = stmt.where(Item.location_node_id == query.location_node_id)
    if query.container_item_id is not None:
        stmt = stmt.where(Item.container_item_id == query.container_item_id)
    if query.residence_id is not None:
        stmt = stmt.where(Item.location_node.has(LocationNode.residence_id == query.residence_id))
    if query.owner_member_id is not None:
        stmt = stmt.where(Item.owner_member_id == query.owner_member_id)
    if query.keeper_member_id is not None:
        stmt = stmt.where(Item.keeper_member_id == query.keeper_member_id)
    if query.container_only is not None:
        stmt = stmt.where(Item.is_container.is_(query.container_only))
    if query.tag:
        normalized_tag = normalize_tag(query.tag)
        stmt = stmt.where(Item.tag_links.any(ItemTag.tag.has(Tag.normalized_name == normalized_tag)))
    if query.search:
        search_term = f"%{query.search.strip()}%"
        if search_term != "%%":
            stmt = stmt.where(
                or_(
                    Item.name.ilike(search_term),
                    Item.description.ilike(search_term),
                    Item.tag_links.any(
                        ItemTag.tag.has(
                            or_(
                                Tag.name.ilike(search_term),
                                Tag.normalized_name.ilike(search_term),
                            )
                        )
                    ),
                    Item.attribute_values.any(ItemAttributeValue.value.ilike(search_term)),
                )
            )
    if query.is_on_loan is True:
        stmt = stmt.where(
            or_(
                Item.status.has(ItemStatus.code == "loaned"),
                Item.loans.any(ItemLoan.returned_at.is_(None)),
            )
        )
    elif query.is_on_loan is False:
        stmt = stmt.where(~Item.status.has(ItemStatus.code == "loaned"))

    total = db.scalar(select(func.count()).select_from(stmt.order_by(None).subquery())) or 0
    stmt = (
        apply_list_sort(stmt, query.sort)
        .options(*item_response_options())
        .limit(query.page_size)
        .offset((query.page - 1) * query.page_size)
    )
    items = db.scalars(stmt).unique().all()
    return ItemListResponse(
        items=[build_item_summary_response(item) for item in items],
        total=total,
        page=query.page,
        page_size=query.page_size,
    )


def get_item_detail(db: Session, item_id: int) -> ItemDetailResponse:
    item = load_item_for_response(db, item_id)
    if item is None:
        raise not_found("\u7269\u54c1\u4e0d\u5b58\u5728")
    return build_item_detail_response(item)


def replace_attribute_values(db: Session, item: Item, values: dict[int, str]) -> None:
    item.attribute_values.clear()
    db.flush()
    for definition_id, value in sorted(values.items()):
        if value == "":
            continue
        db.add(
            ItemAttributeValue(
                item_id=item.id,
                attribute_definition_id=definition_id,
                value=value,
            )
        )


def merge_attribute_values_for_update(
    item: Item,
    incoming_values: list[ItemAttributeValueInput],
) -> list[ItemAttributeValueInput]:
    value_by_definition_id = {
        value.attribute_definition_id: value.value
        for value in item.attribute_values
    }
    for incoming_value in incoming_values:
        value_by_definition_id[incoming_value.attribute_definition_id] = incoming_value.value
    return [
        ItemAttributeValueInput(attribute_definition_id=definition_id, value=value)
        for definition_id, value in value_by_definition_id.items()
    ]


def replace_tags(db: Session, item: Item, tag_names: list[str]) -> None:
    normalized_names: list[str] = []
    seen_names: set[str] = set()
    display_name_by_normalized_name: dict[str, str] = {}
    for tag_name in tag_names:
        normalized_name = normalize_tag(tag_name)
        if normalized_name == "":
            continue
        if len(normalized_name) > 120:
            raise bad_request("\u6807\u7b7e\u8fc7\u957f")
        if normalized_name not in seen_names:
            normalized_names.append(normalized_name)
            seen_names.add(normalized_name)
            display_name_by_normalized_name[normalized_name] = " ".join(tag_name.strip().split())

    existing_tags = {
        tag.normalized_name: tag
        for tag in db.scalars(
            select(Tag).where(Tag.normalized_name.in_(normalized_names))
            if normalized_names
            else select(Tag).where(Tag.id == -1)
        ).all()
    }
    tags: list[Tag] = []
    for normalized_name in normalized_names:
        tag = existing_tags.get(normalized_name)
        if tag is None:
            tag = Tag(
                name=display_name_by_normalized_name[normalized_name],
                normalized_name=normalized_name,
            )
            db.add(tag)
        tags.append(tag)

    item.tag_links.clear()
    db.flush()
    for tag in tags:
        item.tag_links.append(ItemTag(tag=tag))


def item_response_options() -> tuple:
    return (
        selectinload(Item.category),
        selectinload(Item.status),
        selectinload(Item.owner_member),
        selectinload(Item.keeper_member),
        selectinload(Item.location_node).selectinload(LocationNode.residence),
        selectinload(Item.container_item),
        selectinload(Item.attribute_values).selectinload(ItemAttributeValue.attribute_definition),
        selectinload(Item.images),
        selectinload(Item.attachments),
        selectinload(Item.tag_links).selectinload(ItemTag.tag),
        selectinload(Item.movements).selectinload(ItemMovement.previous_location_node),
        selectinload(Item.movements).selectinload(ItemMovement.new_location_node),
        selectinload(Item.movements).selectinload(ItemMovement.previous_container_item),
        selectinload(Item.movements).selectinload(ItemMovement.new_container_item),
        selectinload(Item.movements).selectinload(ItemMovement.previous_status),
        selectinload(Item.movements).selectinload(ItemMovement.new_status),
        selectinload(Item.quantity_changes),
        selectinload(Item.loans).selectinload(ItemLoan.return_location_node),
        selectinload(Item.loans).selectinload(ItemLoan.return_container_item),
    )


def load_item_for_response(db: Session, item_id: int) -> Item | None:
    return db.scalar(
        select(Item)
        .where(Item.id == item_id)
        .options(*item_response_options())
    )


def apply_list_sort(stmt, sort: str):
    if sort == "name_asc":
        return stmt.order_by(Item.name.asc(), Item.id.asc())
    if sort == "name_desc":
        return stmt.order_by(Item.name.desc(), Item.id.desc())
    if sort == "updated_asc":
        return stmt.order_by(Item.updated_at.asc(), Item.id.asc())
    if sort == "created_desc":
        return stmt.order_by(Item.created_at.desc(), Item.id.desc())
    if sort == "created_asc":
        return stmt.order_by(Item.created_at.asc(), Item.id.asc())
    return stmt.order_by(Item.updated_at.desc(), Item.id.desc())


def build_item_summary_response(item: Item) -> ItemSummaryResponse:
    location_node = item.location_node
    residence = location_node.residence if location_node is not None else None
    primary_image = first_active_primary_image(item)
    return ItemSummaryResponse(
        id=item.id,
        name=item.name,
        description=item.description,
        category_id=item.category_id,
        category_name=item.category.name if item.category is not None else "",
        status_id=item.status_id,
        status_name=item.status.name if item.status is not None else "",
        status_semantic=item.status.semantic if item.status is not None else "",
        quantity=item.quantity,
        unit=item.unit,
        owner_member_id=item.owner_member_id,
        owner_member_name=item.owner_member.name if item.owner_member is not None else None,
        keeper_member_id=item.keeper_member_id,
        keeper_member_name=item.keeper_member.name if item.keeper_member is not None else None,
        location_node_id=item.location_node_id,
        location_node_name=location_node.name if location_node is not None else None,
        residence_id=residence.id if residence is not None else None,
        residence_name=residence.name if residence is not None else None,
        container_item_id=item.container_item_id,
        container_item_name=item.container_item.name if item.container_item is not None else None,
        is_container=item.is_container,
        privacy_level=item.privacy_level,
        is_archived=item.is_archived,
        primary_image_url=primary_image.file_path if primary_image is not None else None,
        tags=build_tag_responses(item),
        created_at=item.created_at,
        updated_at=item.updated_at,
    )


def build_item_detail_response(item: Item) -> ItemDetailResponse:
    summary = build_item_summary_response(item)
    return ItemDetailResponse(
        **summary.model_dump(),
        archive_reason=item.archive_reason,
        archived_at=item.archived_at,
        created_by_id=item.created_by_id,
        updated_by_id=item.updated_by_id,
        attribute_values=build_attribute_value_responses(item),
        images=build_image_responses(item),
        attachments=build_attachment_responses(item),
        movements=build_movement_responses(item),
        quantity_changes=build_quantity_change_responses(item),
        loans=build_loan_responses(item),
    )


def build_tag_responses(item: Item) -> list[TagResponse]:
    return [
        TagResponse.model_validate(link.tag)
        for link in sorted(
            item.tag_links,
            key=lambda link: (link.tag.normalized_name if link.tag is not None else "", link.id),
        )
        if link.tag is not None
    ]


def build_attribute_value_responses(item: Item) -> list[ItemAttributeValueResponse]:
    return [
        ItemAttributeValueResponse(
            id=value.id,
            attribute_definition_id=value.attribute_definition_id,
            attribute_key=value.attribute_definition.key if value.attribute_definition is not None else "",
            attribute_name=value.attribute_definition.name if value.attribute_definition is not None else "",
            field_type=value.attribute_definition.field_type if value.attribute_definition is not None else "",
            value=value.value,
        )
        for value in sorted(
            item.attribute_values,
            key=lambda value: (
                value.attribute_definition.sort_order if value.attribute_definition is not None else 0,
                value.attribute_definition_id,
            ),
        )
    ]


def first_active_primary_image(item: Item):
    active_images = [image for image in item.images if not image.is_archived]
    if not active_images:
        return None
    return sorted(active_images, key=lambda image: (not image.is_primary, image.sort_order, image.id))[0]


def build_image_responses(item: Item) -> list[ItemImageResponse]:
    return [
        ItemImageResponse.model_validate({**image.__dict__, "url": image.file_path})
        for image in sorted(
            (image for image in item.images if not image.is_archived),
            key=lambda image: (image.sort_order, image.id),
        )
    ]


def build_attachment_responses(item: Item) -> list[ItemAttachmentResponse]:
    return [
        ItemAttachmentResponse.model_validate({**attachment.__dict__, "download_url": attachment.file_path})
        for attachment in sorted(
            (attachment for attachment in item.attachments if not attachment.is_archived),
            key=lambda attachment: (attachment.created_at, attachment.id),
        )
    ]


def build_movement_responses(item: Item) -> list[ItemMovementResponse]:
    return [
        ItemMovementResponse(
            id=movement.id,
            item_id=movement.item_id,
            previous_location_node_id=movement.previous_location_node_id,
            previous_location_node_name=(
                movement.previous_location_node.name if movement.previous_location_node is not None else None
            ),
            new_location_node_id=movement.new_location_node_id,
            new_location_node_name=movement.new_location_node.name if movement.new_location_node is not None else None,
            previous_container_item_id=movement.previous_container_item_id,
            previous_container_item_name=(
                movement.previous_container_item.name if movement.previous_container_item is not None else None
            ),
            new_container_item_id=movement.new_container_item_id,
            new_container_item_name=movement.new_container_item.name if movement.new_container_item is not None else None,
            previous_status_id=movement.previous_status_id,
            previous_status_name=movement.previous_status.name if movement.previous_status is not None else None,
            new_status_id=movement.new_status_id,
            new_status_name=movement.new_status.name if movement.new_status is not None else None,
            movement_type=movement.movement_type,
            reason=movement.reason,
            note=movement.note,
            actor_id=movement.actor_id,
            created_at=movement.created_at,
        )
        for movement in sorted(item.movements, key=lambda movement: (movement.created_at, movement.id))
    ]


def build_quantity_change_responses(item: Item) -> list[ItemQuantityChangeResponse]:
    return [
        ItemQuantityChangeResponse.model_validate(quantity_change)
        for quantity_change in sorted(
            item.quantity_changes,
            key=lambda quantity_change: (quantity_change.created_at, quantity_change.id),
        )
    ]


def build_loan_responses(item: Item) -> list[ItemLoanResponse]:
    return [
        ItemLoanResponse(
            id=loan.id,
            item_id=loan.item_id,
            borrower_name=loan.borrower_name,
            borrower_contact=loan.borrower_contact,
            expected_return_date=loan.expected_return_date,
            loan_note=loan.loan_note,
            loaned_at=loan.loaned_at,
            returned_at=loan.returned_at,
            return_note=loan.return_note,
            return_location_node_id=loan.return_location_node_id,
            return_location_node_name=loan.return_location_node.name if loan.return_location_node is not None else None,
            return_container_item_id=loan.return_container_item_id,
            return_container_item_name=loan.return_container_item.name if loan.return_container_item is not None else None,
            loan_actor_id=loan.loan_actor_id,
            return_actor_id=loan.return_actor_id,
            created_at=loan.created_at,
            updated_at=loan.updated_at,
        )
        for loan in sorted(item.loans, key=lambda loan: (loan.created_at, loan.id))
    ]
