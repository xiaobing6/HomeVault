from __future__ import annotations

from datetime import datetime, timezone
from threading import RLock

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.core.errors import bad_request, not_found
from app.core.security import hash_password
from app.models.auth import AuthSession, Permission, Role, User
from app.schemas.admin import (
    AdminPasswordReset,
    AdminPermissionResponse,
    AdminRoleCreate,
    AdminRoleResponse,
    AdminRoleUpdate,
    AdminUserCreate,
    AdminUserListQuery,
    AdminUserListResponse,
    AdminUserResponse,
    AdminUserUpdate,
)
from app.services.audit import record_audit_log
from app.services.auth import effective_permission_codes

_admin_user_update_lock = RLock()

ROLE_REQUIRED_MESSAGE = "角色至少需要一个权限"
PERMISSION_NOT_FOUND_MESSAGE = "权限不存在"
SYSTEM_ROLE_READONLY_MESSAGE = "系统角色不能编辑"
INACTIVE_ROLE_ASSIGNMENT_MESSAGE = "角色未启用"
DUPLICATE_ROLE_CODE_MESSAGE = "角色编码已存在"
ROLE_NOT_FOUND_MESSAGE = "角色不存在"


def serialize_admin_user(user: User) -> AdminUserResponse:
    roles = sorted({role.code for role in user.roles})
    permissions = effective_permission_codes(user)
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
        is_active=role.is_active,
        permissions=[
            AdminPermissionResponse.model_validate(permission)
            for permission in sorted(role.permissions, key=lambda item: item.code)
        ],
    )


def list_roles(db: Session) -> list[AdminRoleResponse]:
    roles = db.scalars(
        select(Role)
        .options(selectinload(Role.permissions))
        .order_by(Role.code)
    ).all()
    return [serialize_admin_role(role) for role in roles]


def normalize_permission_codes(permission_codes: list[str]) -> list[str]:
    unique_codes = sorted(
        {
            permission_code.strip()
            for permission_code in permission_codes
            if permission_code.strip()
        }
    )
    if not unique_codes:
        raise bad_request(ROLE_REQUIRED_MESSAGE)
    return unique_codes


def permission_map_by_code(db: Session, permission_codes: list[str]) -> dict[str, Permission]:
    unique_codes = normalize_permission_codes(permission_codes)
    permissions = db.scalars(
        select(Permission).where(Permission.code.in_(unique_codes))
    ).all()
    permissions_by_code = {permission.code: permission for permission in permissions}
    if set(permissions_by_code) != set(unique_codes):
        raise bad_request(PERMISSION_NOT_FOUND_MESSAGE)
    return permissions_by_code


def get_role_for_admin(db: Session, role_id: int) -> Role:
    role = db.scalar(
        select(Role)
        .where(Role.id == role_id)
        .options(selectinload(Role.permissions))
    )
    if role is None:
        raise not_found(ROLE_NOT_FOUND_MESSAGE)
    return role


def create_role(
    db: Session,
    payload: AdminRoleCreate,
    actor: User | None = None,
) -> AdminRoleResponse:
    normalized_permission_codes = normalize_permission_codes(payload.permission_codes)
    permissions_by_code = permission_map_by_code(db, normalized_permission_codes)
    existing = db.scalar(select(Role.id).where(Role.code == payload.code))
    if existing is not None:
        raise bad_request(DUPLICATE_ROLE_CODE_MESSAGE)

    role = Role(
        code=payload.code,
        name=payload.name,
        description=payload.description,
        is_system=False,
        is_active=payload.is_active,
    )
    role.permissions = [
        permissions_by_code[permission_code]
        for permission_code in normalized_permission_codes
    ]
    db.add(role)
    try:
        db.flush()
        record_audit_log(
            db,
            action="admin.role.create",
            resource_type="role",
            actor=actor,
            resource_id=role.id,
            resource_label=role.code,
            metadata={
                "permission_codes": normalized_permission_codes,
                "is_active": role.is_active,
            },
        )
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise bad_request(DUPLICATE_ROLE_CODE_MESSAGE) from exc
    db.refresh(role)
    return serialize_admin_role(role)


def update_role(
    db: Session,
    role_id: int,
    payload: AdminRoleUpdate,
    actor: User | None = None,
) -> AdminRoleResponse:
    role = get_role_for_admin(db, role_id)
    if role.is_system:
        raise bad_request(SYSTEM_ROLE_READONLY_MESSAGE)

    next_permission_codes = normalize_permission_codes(payload.permission_codes)
    permissions_by_code = permission_map_by_code(db, next_permission_codes)
    current_permission_codes = sorted({permission.code for permission in role.permissions})
    changed_fields: list[str] = []
    if role.name != payload.name:
        changed_fields.append("name")
    if role.description != payload.description:
        changed_fields.append("description")
    if current_permission_codes != next_permission_codes:
        changed_fields.append("permission_codes")
    active_changed = role.is_active != payload.is_active

    role.name = payload.name
    role.description = payload.description
    role.permissions = [
        permissions_by_code[permission_code]
        for permission_code in next_permission_codes
    ]
    role.is_active = payload.is_active

    if changed_fields:
        record_audit_log(
            db,
            action="admin.role.update",
            resource_type="role",
            actor=actor,
            resource_id=role.id,
            resource_label=role.code,
            metadata={
                "changed_fields": changed_fields,
                "permission_codes": next_permission_codes,
                "is_active": role.is_active,
            },
        )
    if active_changed:
        record_audit_log(
            db,
            action="admin.role.activate" if role.is_active else "admin.role.deactivate",
            resource_type="role",
            actor=actor,
            resource_id=role.id,
            resource_label=role.code,
            metadata={"is_active": role.is_active},
        )
    db.commit()
    db.refresh(role)
    return serialize_admin_role(role)


def normalize_role_codes(role_codes: list[str]) -> list[str]:
    unique_codes = sorted({role_code.strip() for role_code in role_codes if role_code.strip()})
    if not unique_codes:
        raise bad_request("用户至少需要一个角色")
    return unique_codes


def role_map_by_code(
    db: Session,
    role_codes: list[str],
    allowed_inactive_role_codes: set[str] | None = None,
) -> dict[str, Role]:
    unique_codes = normalize_role_codes(role_codes)
    allowed_inactive_role_codes = allowed_inactive_role_codes or set()

    roles = db.scalars(
        select(Role)
        .where(Role.code.in_(unique_codes))
        .options(selectinload(Role.permissions))
    ).all()
    roles_by_code = {role.code: role for role in roles}
    if set(roles_by_code) != set(unique_codes):
        raise bad_request("角色不存在")
    if any(
        not role.is_system and not role.is_active and role.code not in allowed_inactive_role_codes
        for role in roles_by_code.values()
    ):
        raise bad_request(INACTIVE_ROLE_ASSIGNMENT_MESSAGE)
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
    is_next_active_admin = next_is_active and "admin" in set(normalize_role_codes(next_role_codes))
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


def create_user(db: Session, payload: AdminUserCreate, actor: User | None = None) -> AdminUserResponse:
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
        db.flush()
        record_audit_log(
            db,
            action="admin.user.create",
            resource_type="user",
            actor=actor,
            resource_id=user.id,
            resource_label=user.username,
            metadata={"role_codes": sorted(roles_by_code)},
        )
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


def update_user(
    db: Session,
    user_id: int,
    payload: AdminUserUpdate,
    actor: User | None = None,
) -> AdminUserResponse:
    with _admin_user_update_lock:
        user = get_user_for_admin(db, user_id)
        current_role_codes = sorted({role.code for role in user.roles})
        roles_by_code = role_map_by_code(
            db,
            payload.role_codes,
            allowed_inactive_role_codes=set(current_role_codes),
        )
        normalized_role_codes = sorted(roles_by_code)
        assert_not_last_active_admin(db, user, payload.is_active, normalized_role_codes)

        changed_fields: list[str] = []
        if user.display_name != payload.display_name:
            changed_fields.append("display_name")
        if user.is_active != payload.is_active:
            changed_fields.append("is_active")
        if current_role_codes != normalized_role_codes:
            changed_fields.append("role_codes")

        user.display_name = payload.display_name
        user.is_active = payload.is_active
        user.roles = [roles_by_code[code] for code in normalized_role_codes]
        record_audit_log(
            db,
            action="admin.user.update",
            resource_type="user",
            actor=actor,
            resource_id=user.id,
            resource_label=user.username,
            metadata={
                "changed_fields": changed_fields,
                "role_codes": normalized_role_codes,
                "is_active": user.is_active,
            },
        )
        db.commit()
        db.refresh(user)
        return serialize_admin_user(user)


def reset_user_password(
    db: Session,
    user_id: int,
    payload: AdminPasswordReset,
    actor: User | None = None,
) -> AdminUserResponse:
    user = get_user_for_admin(db, user_id)
    user.password_hash = hash_password(payload.password)
    revoked_at = datetime.now(timezone.utc)
    sessions = db.scalars(
        select(AuthSession).where(
            AuthSession.user_id == user.id,
            AuthSession.is_active.is_(True),
        )
    ).all()
    for session in sessions:
        session.is_active = False
        session.revoked_at = revoked_at
    record_audit_log(
        db,
        action="admin.user.reset_password",
        resource_type="user",
        actor=actor,
        resource_id=user.id,
        resource_label=user.username,
        metadata={"revoked_session_count": len(sessions)},
    )
    db.commit()
    db.refresh(user)
    return serialize_admin_user(user)
