from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_permission
from app.models.auth import User
from app.schemas.audit import AuditLogListQuery, AuditLogListResponse, AuditLogResponse
from app.services.audit import get_audit_log, list_audit_logs

router = APIRouter(prefix="/audit", tags=["audit"])


@router.get("/logs", response_model=AuditLogListResponse)
def logs(
    action: str | None = Query(default=None, max_length=120),
    resource_type: str | None = Query(default=None, max_length=80),
    result: str | None = Query(default=None, max_length=40),
    actor_user_id: int | None = Query(default=None),
    search: str | None = Query(default=None, max_length=120),
    occurred_from: datetime | None = Query(default=None),
    occurred_to: datetime | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("logs:view")),
) -> AuditLogListResponse:
    query = AuditLogListQuery(
        action=action,
        resource_type=resource_type,
        result=result,
        actor_user_id=actor_user_id,
        search=search,
        occurred_from=occurred_from,
        occurred_to=occurred_to,
        page=page,
        page_size=page_size,
    )
    return list_audit_logs(db, query)


@router.get("/logs/{log_id}", response_model=AuditLogResponse)
def log_detail(
    log_id: int,
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("logs:view")),
) -> AuditLogResponse:
    return get_audit_log(db, log_id)
