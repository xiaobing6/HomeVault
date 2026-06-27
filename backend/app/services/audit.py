from __future__ import annotations

import math
from collections.abc import Mapping
from datetime import datetime
from typing import Any, cast

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.core.errors import not_found
from app.models import AuditLog, User
from app.schemas.audit import AuditLogListQuery, AuditLogListResponse, AuditLogResponse

SENSITIVE_METADATA_KEYS = {"password", "token", "access_token", "password_hash"}

_DROP = object()


def _is_sensitive_key(key: object) -> bool:
    return isinstance(key, str) and key.lower() in SENSITIVE_METADATA_KEYS


def _sanitize_mapping(value: Mapping[object, object]) -> dict[str, Any] | object:
    sanitized: dict[str, Any] = {}
    for key, raw_value in value.items():
        if not isinstance(key, str) or _is_sensitive_key(key):
            continue
        sanitized_value = _sanitize_value(raw_value)
        if sanitized_value is _DROP:
            continue
        sanitized[key] = sanitized_value
    return sanitized if sanitized else _DROP


def _sanitize_sequence(value: list[object] | tuple[object, ...]) -> list[Any]:
    sanitized: list[Any] = []
    for item in value:
        sanitized_item = _sanitize_value(item)
        if sanitized_item is _DROP or sanitized_item is None:
            continue
        sanitized.append(sanitized_item)
    return sanitized


def _sanitize_value(value: object) -> Any | object:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, set):
        return sorted(str(item) for item in value)
    if isinstance(value, Mapping):
        return _sanitize_mapping(value)
    if isinstance(value, tuple):
        return _sanitize_sequence(value)
    if isinstance(value, list):
        return _sanitize_sequence(value)
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return value if math.isfinite(value) else _DROP
    if isinstance(value, str):
        return value
    return _DROP


def sanitize_metadata(metadata: Mapping[object, object] | None) -> dict[str, Any] | None:
    if not metadata:
        return None
    sanitized = _sanitize_mapping(metadata)
    if sanitized is _DROP:
        return None
    return cast(dict[str, Any], sanitized)


def record_audit_log(
    db: Session,
    *,
    action: str,
    resource_type: str,
    actor: User | None = None,
    actor_user_id: int | None = None,
    actor_username: str | None = None,
    resource_id: object | None = None,
    resource_label: str | None = None,
    result: str = "success",
    metadata: Mapping[object, object] | None = None,
) -> AuditLog:
    log = AuditLog(
        actor_user_id=actor.id if actor is not None else actor_user_id,
        actor_username=actor.username if actor is not None else actor_username,
        action=action,
        resource_type=resource_type,
        resource_id=str(resource_id) if resource_id is not None else None,
        resource_label=resource_label,
        result=result,
        metadata_json=sanitize_metadata(metadata),
    )
    db.add(log)
    return log


def serialize_audit_log(log: AuditLog) -> AuditLogResponse:
    return AuditLogResponse(
        id=log.id,
        occurred_at=log.occurred_at,
        actor_user_id=log.actor_user_id,
        actor_username=log.actor_username,
        action=log.action,
        resource_type=log.resource_type,
        resource_id=log.resource_id,
        resource_label=log.resource_label,
        result=log.result,
        metadata=log.metadata_json,
    )


def _audit_log_filters(query: AuditLogListQuery) -> list[object]:
    filters: list[object] = []
    if query.action:
        filters.append(AuditLog.action == query.action)
    if query.resource_type:
        filters.append(AuditLog.resource_type == query.resource_type)
    if query.result:
        filters.append(AuditLog.result == query.result)
    if query.actor_user_id is not None:
        filters.append(AuditLog.actor_user_id == query.actor_user_id)
    if query.occurred_from is not None:
        filters.append(AuditLog.occurred_at >= query.occurred_from)
    if query.occurred_to is not None:
        filters.append(AuditLog.occurred_at <= query.occurred_to)
    if query.search:
        pattern = f"%{query.search}%"
        filters.append(
            or_(
                AuditLog.actor_username.ilike(pattern),
                AuditLog.action.ilike(pattern),
                AuditLog.resource_type.ilike(pattern),
                AuditLog.resource_id.ilike(pattern),
                AuditLog.resource_label.ilike(pattern),
            )
        )
    return filters


def list_audit_logs(db: Session, query: AuditLogListQuery) -> AuditLogListResponse:
    filters = _audit_log_filters(query)
    statement = select(AuditLog).where(*filters)
    count_statement = select(func.count(AuditLog.id)).where(*filters)

    total = db.scalar(count_statement) or 0
    logs = db.scalars(
        statement
        .order_by(AuditLog.occurred_at.desc(), AuditLog.id.desc())
        .offset((query.page - 1) * query.page_size)
        .limit(query.page_size)
    ).all()
    return AuditLogListResponse(
        items=[serialize_audit_log(log) for log in logs],
        total=total,
        page=query.page,
        page_size=query.page_size,
    )


def get_audit_log(db: Session, log_id: int) -> AuditLogResponse:
    log = db.get(AuditLog, log_id)
    if log is None:
        raise not_found("日志不存在")
    return serialize_audit_log(log)
