from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import AuditLog, User
from app.schemas.audit import AuditLogListQuery
from app.services.audit import get_audit_log, list_audit_logs, record_audit_log


def create_actor(db: Session, username: str) -> User:
    actor = User(
        username=username,
        password_hash="hashed-password",
        display_name=username.replace("-", " ").title(),
    )
    db.add(actor)
    db.commit()
    db.refresh(actor)
    return actor


def test_record_audit_log_sanitizes_metadata_without_committing(db_session: Session) -> None:
    actor = create_actor(db_session, "manager")

    log = record_audit_log(
        db_session,
        actor=actor,
        action="admin.user.update",
        resource_type="user",
        resource_id=42,
        resource_label="manager",
        metadata={
            "changed_fields": {"roles", "display_name"},
            "ignored": object(),
            "password": "Secret123!",
            "token": "secret-token",
        },
    )

    assert log.id is None
    assert log.actor_user_id == actor.id
    assert log.actor_username == actor.username
    assert log.resource_id == "42"
    assert log.metadata_json == {"changed_fields": ["display_name", "roles"]}

    db_session.commit()

    persisted_logs = db_session.scalars(select(AuditLog)).all()
    assert len(persisted_logs) == 1
    assert persisted_logs[0].id is not None


def test_record_audit_log_drops_sensitive_metadata_key_variants(db_session: Session) -> None:
    actor = create_actor(db_session, "privacy-admin")

    log = record_audit_log(
        db_session,
        actor=actor,
        action="auth.login",
        resource_type="auth_session",
        metadata={
            "refresh_token": "refresh-secret",
            "api_token": "api-secret",
            "token_hash": "token-hash",
            "passwordHash": "password-hash",
            "request_body": {"password": "Secret123!", "safe": "ignored"},
            "fullRequestBody": {"token": "nested-secret"},
            "changed_fields": ["display_name"],
            "nested": {
                "accessToken": "nested-token",
                "safe_key": "safe-value",
            },
        },
    )

    assert log.metadata_json == {
        "changed_fields": ["display_name"],
        "nested": {"safe_key": "safe-value"},
    }


def test_list_audit_logs_filters_by_resource_type_and_case_insensitive_search(
    db_session: Session,
) -> None:
    admin = create_actor(db_session, "admin")
    manager = create_actor(db_session, "manager")
    record_audit_log(
        db_session,
        actor=admin,
        action="auth.login",
        resource_type="auth_session",
        resource_id="session-1",
        resource_label="Admin Session",
    )
    record_audit_log(
        db_session,
        actor=manager,
        action="config.residence.update",
        resource_type="residence",
        resource_id=7,
        resource_label="Lake House",
        metadata={"is_active": False},
    )
    db_session.commit()

    result = list_audit_logs(
        db_session,
        AuditLogListQuery(resource_type="residence", search="lake", page=1, page_size=20),
    )

    assert result.total == 1
    assert result.items[0].action == "config.residence.update"
    assert result.items[0].metadata == {"is_active": False}


def test_list_audit_logs_filters_by_date_range(db_session: Session) -> None:
    actor = create_actor(db_session, "auditor")
    old_log = record_audit_log(
        db_session,
        actor=actor,
        action="auth.login",
        resource_type="auth_session",
        resource_id="old-session",
    )
    new_log = record_audit_log(
        db_session,
        actor=actor,
        action="auth.login",
        resource_type="auth_session",
        resource_id="new-session",
    )
    db_session.commit()

    now = datetime.now(timezone.utc)
    old_log.occurred_at = now - timedelta(days=3)
    new_log.occurred_at = now
    db_session.commit()

    result = list_audit_logs(
        db_session,
        AuditLogListQuery(occurred_from=now - timedelta(days=1)),
    )

    assert [item.resource_id for item in result.items] == ["new-session"]


def test_get_audit_log_returns_detail_or_raises_not_found_shape(db_session: Session) -> None:
    actor = create_actor(db_session, "detail-admin")
    log = record_audit_log(
        db_session,
        actor=actor,
        action="admin.user.update",
        resource_type="user",
        resource_id=actor.id,
    )
    db_session.commit()

    detail = get_audit_log(db_session, log.id)

    assert detail.id == log.id
    assert detail.action == "admin.user.update"

    with pytest.raises(HTTPException) as exc_info:
        get_audit_log(db_session, 999999)

    assert exc_info.value.detail["message"] == "日志不存在"
