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
