from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models.auth import Permission, Role, User

PERMISSIONS = [
    ("items:view", "查看物品", "查看物品列表和详情"),
    ("items:create", "新增物品", "创建新的物品记录"),
    ("items:edit", "编辑物品", "修改物品、位置、状态和数量"),
    ("items:archive", "归档物品", "软删除或归档物品"),
    ("config:manage", "管理配置", "管理住宅、位置、分类、字段和字典"),
    ("users:manage", "管理用户", "管理账号、角色和家庭成员"),
    ("logs:view", "查看日志", "查看全局操作日志"),
]

ROLE_PERMISSIONS = {
    "admin": [code for code, _name, _description in PERMISSIONS],
    "editor": ["items:view", "items:create", "items:edit"],
    "viewer": ["items:view"],
}

ROLES = [
    ("admin", "管理员", "拥有全部管理权限"),
    ("editor", "编辑者", "可维护物品但不能管理系统配置"),
    ("viewer", "查看者", "只能查看和搜索物品"),
]


def seed_auth_baseline(db: Session, admin_username: str, admin_password: str) -> User:
    permissions_by_code: dict[str, Permission] = {}
    for code, name, description in PERMISSIONS:
        permission = db.scalar(select(Permission).where(Permission.code == code))
        if permission is None:
            permission = Permission(code=code, name=name, description=description)
            db.add(permission)
        permissions_by_code[code] = permission

    roles_by_code: dict[str, Role] = {}
    for code, name, description in ROLES:
        role = db.scalar(select(Role).where(Role.code == code))
        if role is None:
            role = Role(code=code, name=name, description=description, is_system=True)
            db.add(role)
        role.permissions = [permissions_by_code[item] for item in ROLE_PERMISSIONS[code]]
        roles_by_code[code] = role

    admin = db.scalar(select(User).where(User.username == admin_username))
    if admin is None:
        admin = User(
            username=admin_username,
            password_hash=hash_password(admin_password),
            display_name="管理员",
            is_active=True,
        )
        db.add(admin)
    admin.roles = [roles_by_code["admin"]]
    db.commit()
    db.refresh(admin)
    return admin
