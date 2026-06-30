from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
from io import StringIO
from secrets import token_urlsafe

from fastapi import HTTPException
from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.core.errors import bad_request
from app.models.configuration import AttributeDefinition, Category, FamilyMember, ItemStatus, LocationNode, Residence
from app.models.inventory import Item
from app.schemas.inventory import (
    ImportConfirmResponse,
    ImportFieldMessage,
    ImportPreviewResponse,
    ImportRowPreview,
    ItemAttributeValueInput,
    ItemCreate,
)
from app.services.inventory import (
    create_item_record,
    flush_or_bad_request,
    normalize_attribute_value,
)


STATIC_IMPORT_COLUMNS = [
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
MAX_IMPORT_ROWS = 500
IMPORT_TOKEN_TTL = timedelta(minutes=30)


@dataclass(frozen=True)
class CachedImport:
    expires_at: datetime
    payloads: list[ItemCreate]


_IMPORT_CACHE: dict[str, CachedImport] = {}


def import_template_csv(db: Session) -> str:
    dynamic_columns = [
        f"field:{definition.key}"
        for definition in db.scalars(
            select(AttributeDefinition)
            .where(AttributeDefinition.is_active.is_(True))
            .order_by(AttributeDefinition.category_id, AttributeDefinition.sort_order, AttributeDefinition.id)
        ).all()
    ]
    output = StringIO()
    writer = csv.writer(output, lineterminator="\n")
    writer.writerow([*STATIC_IMPORT_COLUMNS, *dynamic_columns])
    return output.getvalue()


def read_import_csv(content: bytes) -> list[tuple[int, dict[str, str]]]:
    text = content.decode("utf-8-sig")
    reader = csv.DictReader(StringIO(text))
    if not reader.fieldnames:
        raise bad_request("CSV file is empty")

    rows: list[tuple[int, dict[str, str]]] = []
    for row_number, row in enumerate(reader, start=2):
        normalized = {
            str(key).strip(): str(value or "").strip()
            for key, value in row.items()
            if key is not None
        }
        if not any(value for value in normalized.values()):
            continue
        rows.append((row_number, normalized))
        if len(rows) > MAX_IMPORT_ROWS:
            raise bad_request(f"Import is limited to {MAX_IMPORT_ROWS} rows")

    if not rows:
        raise bad_request("CSV file is empty")
    return rows


def preview_inventory_import(db: Session, content: bytes) -> ImportPreviewResponse:
    rows = [
        build_row_preview(db, row_number, original)
        for row_number, original in read_import_csv(content)
    ]
    invalid_count = sum(1 for row in rows if not row.is_valid)
    valid_payloads = [ItemCreate.model_validate(row.normalized) for row in rows if row.normalized is not None]
    token = cache_import(valid_payloads) if invalid_count == 0 else None
    return ImportPreviewResponse(
        token=token,
        rows=rows,
        total_count=len(rows),
        valid_count=len(rows) - invalid_count,
        invalid_count=invalid_count,
    )


def confirm_inventory_import(db: Session, token: str, actor_id: int | None = None) -> ImportConfirmResponse:
    cleanup_import_cache()
    cached = _IMPORT_CACHE.get(token)
    if cached is None or cached.expires_at <= utcnow():
        _IMPORT_CACHE.pop(token, None)
        raise bad_request("Import preview expired; upload the CSV again")

    item_ids: list[int] = []
    try:
        for payload in cached.payloads:
            item = create_item_record(db, payload, actor_id=actor_id)
            flush_or_bad_request(db, "Failed to save item")
            item_ids.append(item.id)
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise bad_request("Failed to save item") from exc
    except Exception:
        db.rollback()
        raise
    finally:
        _IMPORT_CACHE.pop(token, None)

    return ImportConfirmResponse(imported_count=len(item_ids), item_ids=item_ids)


def build_row_preview(db: Session, row_number: int, original: dict[str, str]) -> ImportRowPreview:
    errors: list[ImportFieldMessage] = []
    warnings: list[ImportFieldMessage] = []

    name = original.get("name", "").strip()
    if name == "":
        errors.append(field_error("name", "Name is required"))

    category = resolve_category(db, original.get("category", ""))
    if category is None:
        errors.append(field_error("category", "Category does not exist"))

    item_status = resolve_status(db, original.get("status", ""))
    if item_status is None:
        errors.append(field_error("status", "Status does not exist"))

    quantity = parse_quantity(original.get("quantity", ""), errors)
    is_container = parse_bool(original.get("is_container", ""), "is_container", errors, default=False)
    privacy_level = parse_privacy_level(original.get("privacy_level", ""), errors)
    owner = resolve_member(db, original.get("owner", ""), "owner", errors)
    keeper = resolve_member(db, original.get("keeper", ""), "keeper", errors)
    residence = resolve_residence(db, original.get("residence", ""), errors)
    location = resolve_location(db, original.get("location", ""), residence, errors)
    container = resolve_container(db, original.get("container", ""), errors)
    if location is not None and container is not None:
        errors.append(field_error("location", "Location and container cannot both be set"))

    attribute_values: list[ItemAttributeValueInput] = []
    if category is not None:
        attribute_values = parse_dynamic_fields(db, category, original, errors)
        if name and duplicate_active_item_exists(db, name, category.id):
            warnings.append(field_error("name", "An active item with the same name and category already exists"))

    tags = parse_tags(original.get("tags", ""))
    normalized = None
    if not errors and category is not None and item_status is not None:
        normalized = {
            "name": name,
            "description": original.get("description", ""),
            "category_id": category.id,
            "status_id": item_status.id,
            "quantity": str(quantity),
            "unit": original.get("unit", "") or "pcs",
            "owner_member_id": owner.id if owner is not None else None,
            "keeper_member_id": keeper.id if keeper is not None else None,
            "location_node_id": location.id if location is not None else None,
            "container_item_id": container.id if container is not None else None,
            "is_container": is_container,
            "privacy_level": privacy_level,
            "attribute_values": [value.model_dump() for value in attribute_values],
            "tags": tags,
        }
        try:
            ItemCreate.model_validate(normalized)
        except ValueError as exc:
            errors.append(field_error("row", str(exc)))
            normalized = None

    return ImportRowPreview(
        row_number=row_number,
        original=original,
        normalized=normalized,
        errors=errors,
        warnings=warnings,
        is_valid=not errors,
    )


def resolve_category(db: Session, raw_value: str) -> Category | None:
    value = raw_value.strip()
    if value == "":
        return None
    return db.scalar(
        select(Category)
        .where(Category.is_active.is_(True), or_(Category.code == value, Category.name == value))
        .order_by(Category.id)
        .limit(1)
    )


def resolve_status(db: Session, raw_value: str) -> ItemStatus | None:
    value = raw_value.strip()
    if value == "":
        return None
    return db.scalar(
        select(ItemStatus)
        .where(ItemStatus.is_active.is_(True), or_(ItemStatus.code == value, ItemStatus.name == value))
        .order_by(ItemStatus.id)
        .limit(1)
    )


def resolve_member(db: Session, raw_value: str, field: str, errors: list[ImportFieldMessage]) -> FamilyMember | None:
    value = raw_value.strip()
    if value == "":
        return None
    member = db.scalar(
        select(FamilyMember)
        .where(FamilyMember.is_active.is_(True), FamilyMember.name == value)
        .order_by(FamilyMember.id)
        .limit(1)
    )
    if member is None:
        errors.append(field_error(field, "Family member does not exist"))
    return member


def resolve_residence(db: Session, raw_value: str, errors: list[ImportFieldMessage]) -> Residence | None:
    value = raw_value.strip()
    if value == "":
        return None
    residence = db.scalar(
        select(Residence)
        .where(Residence.is_active.is_(True), Residence.name == value)
        .order_by(Residence.id)
        .limit(1)
    )
    if residence is None:
        errors.append(field_error("residence", "Residence does not exist"))
    return residence


def resolve_location(
    db: Session,
    raw_value: str,
    residence: Residence | None,
    errors: list[ImportFieldMessage],
) -> LocationNode | None:
    value = raw_value.strip()
    if value == "":
        return None
    stmt = (
        select(LocationNode)
        .where(LocationNode.is_active.is_(True))
        .options(selectinload(LocationNode.parent), selectinload(LocationNode.residence))
        .order_by(LocationNode.id)
    )
    if residence is not None:
        stmt = stmt.where(LocationNode.residence_id == residence.id)
    locations = db.scalars(stmt).all()
    for location in locations:
        if location.name == value or location_path(location) == value:
            return location
    errors.append(field_error("location", "Location does not exist"))
    return None


def resolve_container(db: Session, raw_value: str, errors: list[ImportFieldMessage]) -> Item | None:
    value = raw_value.strip()
    if value == "":
        return None
    container = db.scalar(
        select(Item)
        .where(Item.is_archived.is_(False), Item.is_container.is_(True), Item.name == value)
        .order_by(Item.id)
        .limit(1)
    )
    if container is None:
        errors.append(field_error("container", "Container does not exist"))
    return container


def parse_dynamic_fields(
    db: Session,
    category: Category,
    original: dict[str, str],
    errors: list[ImportFieldMessage],
) -> list[ItemAttributeValueInput]:
    definitions = db.scalars(
        select(AttributeDefinition)
        .where(AttributeDefinition.category_id == category.id, AttributeDefinition.is_active.is_(True))
        .options(selectinload(AttributeDefinition.options))
        .order_by(AttributeDefinition.sort_order, AttributeDefinition.id)
    ).all()
    values: list[ItemAttributeValueInput] = []
    for definition in definitions:
        field = f"field:{definition.key}"
        raw_value = original.get(field, "").strip()
        if raw_value == "":
            if definition.is_required:
                errors.append(field_error(field, f"{definition.name} is required"))
            continue
        try:
            normalized_value = normalize_attribute_value(definition, raw_value)
        except HTTPException as exc:
            errors.append(field_error(field, error_message(exc)))
            continue
        values.append(ItemAttributeValueInput(attribute_definition_id=definition.id, value=normalized_value))
    return values


def parse_quantity(raw_value: str, errors: list[ImportFieldMessage]) -> Decimal:
    value = raw_value.strip()
    if value == "":
        return Decimal("1")
    try:
        quantity = Decimal(value)
    except (InvalidOperation, ValueError):
        errors.append(field_error("quantity", "Quantity format is invalid"))
        return Decimal("0")
    if not quantity.is_finite():
        errors.append(field_error("quantity", "Quantity format is invalid"))
        return Decimal("0")
    return quantity


def parse_bool(
    raw_value: str,
    field: str,
    errors: list[ImportFieldMessage],
    *,
    default: bool,
) -> bool:
    value = raw_value.strip().lower()
    if value == "":
        return default
    if value in {"true", "1", "yes", "y"}:
        return True
    if value in {"false", "0", "no", "n"}:
        return False
    errors.append(field_error(field, "Boolean format is invalid"))
    return default


def parse_privacy_level(raw_value: str, errors: list[ImportFieldMessage]) -> str:
    value = raw_value.strip() or "normal"
    if value == "private":
        return "sensitive"
    if value in {"normal", "sensitive"}:
        return value
    errors.append(field_error("privacy_level", "Privacy level is invalid"))
    return "normal"


def parse_tags(raw_value: str) -> list[str]:
    tags = [" ".join(tag.strip().split()) for tag in raw_value.split(",") if tag.strip()]
    return sorted(dict.fromkeys(tags), key=str.lower)


def duplicate_active_item_exists(db: Session, name: str, category_id: int) -> bool:
    return db.scalar(
        select(Item.id)
        .where(Item.is_archived.is_(False), Item.name == name, Item.category_id == category_id)
        .limit(1)
    ) is not None


def location_path(location: LocationNode) -> str:
    names = [location.name]
    parent = location.parent
    while parent is not None:
        names.append(parent.name)
        parent = parent.parent
    return "/".join(reversed(names))


def cache_import(payloads: list[ItemCreate]) -> str:
    cleanup_import_cache()
    token = token_urlsafe(24)
    _IMPORT_CACHE[token] = CachedImport(expires_at=utcnow() + IMPORT_TOKEN_TTL, payloads=payloads)
    return token


def cleanup_import_cache() -> None:
    now = utcnow()
    expired_tokens = [token for token, cached in _IMPORT_CACHE.items() if cached.expires_at <= now]
    for token in expired_tokens:
        _IMPORT_CACHE.pop(token, None)


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def field_error(field: str, message: str) -> ImportFieldMessage:
    return ImportFieldMessage(field=field, message=message)


def error_message(exc: HTTPException) -> str:
    detail = exc.detail
    if isinstance(detail, dict) and isinstance(detail.get("message"), str):
        return detail["message"]
    if isinstance(detail, str):
        return detail
    return "Field format is invalid"
