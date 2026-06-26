from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.core.errors import bad_request, not_found
from app.core.security import hash_password
from app.models.auth import Role, User
from app.schemas.admin import (
    AdminPasswordReset,
    AdminRoleResponse,
    AdminUserCreate,
    AdminUserListQuery,
    AdminUserListResponse,
    AdminUserResponse,
    AdminUserUpdate,
)


def serialize_admin_user(user: User) -> AdminUserResponse:
    roles = sorted({role.code for role in user.roles})
    permissions = sorted(
        {
            permission.code
            for role in user.roles
            for permission in role.permissions
        }
    )
    return AdminUserResponse(
        id=user.id,
        username=user.username,
        display_name=user.display_name,
        is_active=user.is_active,
        roles=roles,
        permissions=permissions,
        created_at=user.created_at,
        updated_at=user.updated_at,
    )


def serialize_admin_role(role: Role) -> AdminRoleResponse:
    return AdminRoleResponse(
        id=role.id,
        code=role.code,
        name=role.name,
        description=role.description,
        is_system=role.is_system,
        permissions=sorted({permission.code for permission in role.permissions}),
    )


def list_roles(db: Session) -> list[AdminRoleResponse]:
    roles = db.scalars(
        select(Role)
        .options(selectinload(Role.permissions))
        .order_by(Role.code)
    ).all()
    return [serialize_admin_role(role) for role in roles]


def role_map_by_code(db: Session, role_codes: list[str]) -> dict[str, Role]:
    unique_codes = sorted(set(role_codes))
    if not unique_codes:
        raise bad_request("用户至少需要一个角色")

    roles = db.scalars(
        select(Role)
        .where(Role.code.in_(unique_codes))
        .options(selectinload(Role.permissions))
    ).all()
    roles_by_code = {role.code: role for role in roles}
    if set(roles_by_code) != set(unique_codes):
        raise bad_request("角色不存在")
    return roles_by_code


def active_admin_count(db: Session, excluded_user_id: int | None = None) -> int:
    statement = (
        select(func.count(User.id))
        .join(User.roles)
        .where(User.is_active.is_(True), Role.code == "admin")
    )
    if excluded_user_id is not None:
        statement = statement.where(User.id != excluded_user_id)
    return db.scalar(statement) or 0


def assert_not_last_active_admin(
    db: Session,
    user: User,
    next_is_active: bool,
    next_role_codes: list[str],
) -> None:
    is_current_active_admin = user.is_active and any(role.code == "admin" for role in user.roles)
    is_next_active_admin = next_is_active and "admin" in set(next_role_codes)
    if is_current_active_admin and not is_next_active_admin and active_admin_count(db, user.id) == 0:
        raise bad_request("至少保留一个启用的管理员")


def _user_select():
    return select(User).options(selectinload(User.roles).selectinload(Role.permissions))


def list_users(db: Session, query: AdminUserListQuery) -> AdminUserListResponse:
    statement = _user_select()
    count_statement = select(func.count(User.id))

    if query.search:
        pattern = f"%{query.search}%"
        statement = statement.where(
            User.username.ilike(pattern) | User.display_name.ilike(pattern)
        )
        count_statement = count_statement.where(
            User.username.ilike(pattern) | User.display_name.ilike(pattern)
        )
    if query.is_active is not None:
        statement = statement.where(User.is_active.is_(query.is_active))
        count_statement = count_statement.where(User.is_active.is_(query.is_active))
    if query.role:
        statement = statement.join(User.roles).where(Role.code == query.role)
        count_statement = count_statement.join(User.roles).where(Role.code == query.role)

    total = db.scalar(count_statement) or 0
    users = db.scalars(
        statement
        .order_by(User.id)
        .offset((query.page - 1) * query.page_size)
        .limit(query.page_size)
    ).unique().all()
    return AdminUserListResponse(
        items=[serialize_admin_user(user) for user in users],
        total=total,
        page=query.page,
        page_size=query.page_size,
    )


def create_user(db: Session, payload: AdminUserCreate) -> AdminUserResponse:
    roles_by_code = role_map_by_code(db, payload.role_codes)
    existing = db.scalar(select(User.id).where(User.username == payload.username))
    if existing is not None:
        raise bad_request("账号已存在")

    user = User(
        username=payload.username,
        password_hash=hash_password(payload.password),
        display_name=payload.display_name,
        is_active=True,
    )
    user.roles = [roles_by_code[code] for code in sorted(roles_by_code)]
    db.add(user)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise bad_request("账号已存在") from exc
    db.refresh(user)
    return serialize_admin_user(user)


def get_user_for_admin(db: Session, user_id: int) -> User:
    user = db.scalar(_user_select().where(User.id == user_id))
    if user is None:
        raise not_found("用户不存在")
    return user


def update_user(db: Session, user_id: int, payload: AdminUserUpdate) -> AdminUserResponse:
    user = get_user_for_admin(db, user_id)
    roles_by_code = role_map_by_code(db, payload.role_codes)
    assert_not_last_active_admin(db, user, payload.is_active, payload.role_codes)

    user.display_name = payload.display_name
    user.is_active = payload.is_active
    user.roles = [roles_by_code[code] for code in sorted(roles_by_code)]
    db.commit()
    db.refresh(user)
    return serialize_admin_user(user)


def reset_user_password(db: Session, user_id: int, payload: AdminPasswordReset) -> AdminUserResponse:
    user = get_user_for_admin(db, user_id)
    user.password_hash = hash_password(payload.password)
    db.commit()
    db.refresh(user)
    return serialize_admin_user(user)
