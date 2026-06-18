from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.auth import Permission, Role, User
from app.services.seed import seed_auth_baseline


def test_seed_auth_baseline_creates_admin_user(db_session: Session) -> None:
    admin = seed_auth_baseline(
        db_session,
        admin_username="admin",
        admin_password="ChangeMe123!",
    )

    roles = db_session.scalars(select(Role)).all()
    permissions = db_session.scalars(select(Permission)).all()
    users = db_session.scalars(select(User)).all()

    assert admin.username == "admin"
    assert admin.is_active is True
    assert {role.code for role in roles} == {"admin", "editor", "viewer"}
    assert "items:view" in {permission.code for permission in permissions}
    assert users == [admin]
    assert {role.code for role in admin.roles} == {"admin"}
