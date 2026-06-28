from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_permission
from app.models.auth import User
from app.schemas.admin import (
    AdminPasswordReset,
    AdminRoleResponse,
    AdminUserCreate,
    AdminUserListQuery,
    AdminUserListResponse,
    AdminUserResponse,
    AdminUserUpdate,
)
from app.services.admin import (
    create_user as create_user_record,
    list_roles as list_role_records,
    list_users as list_user_records,
    reset_user_password as reset_user_password_record,
    update_user as update_user_record,
)

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/users", response_model=AdminUserListResponse)
def users(
    search: str | None = Query(default=None, max_length=120),
    role: str | None = Query(default=None, max_length=80),
    is_active: bool | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("users:manage")),
) -> AdminUserListResponse:
    query = AdminUserListQuery(
        search=search,
        role=role,
        is_active=is_active,
        page=page,
        page_size=page_size,
    )
    return list_user_records(db, query)


@router.post("/users", response_model=AdminUserResponse, status_code=status.HTTP_201_CREATED)
def create_user(
    payload: AdminUserCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("users:manage")),
) -> AdminUserResponse:
    return create_user_record(db, payload, actor=user)


@router.patch("/users/{user_id}", response_model=AdminUserResponse)
def update_user(
    user_id: int,
    payload: AdminUserUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("users:manage")),
) -> AdminUserResponse:
    return update_user_record(db, user_id, payload, actor=user)


@router.post("/users/{user_id}/reset-password", response_model=AdminUserResponse)
def reset_password(
    user_id: int,
    payload: AdminPasswordReset,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("users:manage")),
) -> AdminUserResponse:
    return reset_user_password_record(db, user_id, payload, actor=user)


@router.get("/roles", response_model=list[AdminRoleResponse])
def roles(
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("users:manage")),
) -> list[AdminRoleResponse]:
    return list_role_records(db)
