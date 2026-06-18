from datetime import datetime, timedelta, timezone
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.config import get_settings
from app.core.security import create_access_token, verify_password
from app.models.auth import AuthSession, Role, User
from app.schemas.user import CurrentUserResponse


def serialize_current_user(user: User) -> CurrentUserResponse:
    permissions = sorted(
        {
            permission.code
            for role in user.roles
            for permission in role.permissions
        }
    )
    roles = sorted({role.code for role in user.roles})
    return CurrentUserResponse(
        id=user.id,
        username=user.username,
        display_name=user.display_name,
        roles=roles,
        permissions=permissions,
    )


def get_user_by_username(db: Session, username: str) -> User | None:
    return db.scalar(
        select(User)
        .where(User.username == username)
        .options(selectinload(User.roles).selectinload(Role.permissions))
    )


def authenticate_user(db: Session, username: str, password: str) -> User | None:
    user = get_user_by_username(db, username)
    if user is None or not user.is_active:
        return None
    if not verify_password(password, user.password_hash):
        return None
    return user


def create_login_session(db: Session, user: User) -> tuple[str, AuthSession]:
    settings = get_settings()
    session = AuthSession(
        session_id=uuid4().hex,
        user_id=user.id,
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=settings.access_token_minutes),
        is_active=True,
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    token = create_access_token(
        user_id=user.id,
        session_id=session.session_id,
        secret_key=settings.secret_key,
        minutes=settings.access_token_minutes,
    )
    return token, session


def revoke_session(db: Session, session: AuthSession) -> None:
    session.is_active = False
    session.revoked_at = datetime.now(timezone.utc)
    db.commit()
