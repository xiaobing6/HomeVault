from collections.abc import Iterator
from datetime import datetime, timezone

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.config import get_settings
from app.core.errors import forbidden, unauthorized
from app.core.security import decode_access_token
from app.db.session import get_db as session_get_db
from app.models.auth import AuthSession, Role, User

bearer_scheme = HTTPBearer(auto_error=False)


def get_db() -> Iterator[Session]:
    yield from session_get_db()


def get_current_user_and_session(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> tuple[User, AuthSession]:
    if credentials is None:
        raise unauthorized()
    try:
        payload = decode_access_token(credentials.credentials, get_settings().secret_key)
    except ValueError as exc:
        raise unauthorized(str(exc)) from exc

    session = db.scalar(
        select(AuthSession)
        .where(AuthSession.session_id == payload.session_id)
        .options(selectinload(AuthSession.user).selectinload(User.roles).selectinload(Role.permissions))
    )
    now = datetime.now(timezone.utc)
    if session is None or not session.is_active:
        raise unauthorized("登录状态已失效，请重新登录")
    expires_at = session.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at <= now:
        raise unauthorized("登录状态已失效，请重新登录")
    if session.user_id != payload.user_id or not session.user.is_active:
        raise unauthorized("登录状态已失效，请重新登录")
    return session.user, session


def get_current_user(
    user_and_session: tuple[User, AuthSession] = Depends(get_current_user_and_session),
) -> User:
    user, _session = user_and_session
    return user


def require_permission(permission_code: str):
    def dependency(user: User = Depends(get_current_user)) -> User:
        user_permissions = {
            permission.code
            for role in user.roles
            for permission in role.permissions
        }
        if permission_code not in user_permissions:
            raise forbidden()
        return user

    return dependency
