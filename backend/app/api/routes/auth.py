from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_current_user_and_session, get_db
from app.core.errors import unauthorized
from app.models.auth import AuthSession, User
from app.schemas.auth import LoginRequest, LoginResponse
from app.schemas.user import CurrentUserResponse
from app.services.auth import (
    authenticate_user,
    create_login_session,
    revoke_session,
    serialize_current_user,
)
from app.services.audit import record_audit_log

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=LoginResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> LoginResponse:
    user = authenticate_user(db, payload.username, payload.password)
    if user is None:
        record_audit_log(
            db,
            action="auth.login",
            resource_type="auth_session",
            result="failure",
            metadata={"attempted_username": payload.username},
        )
        db.commit()
        raise unauthorized("账号或密码不正确")
    access_token, session = create_login_session(db, user)
    record_audit_log(
        db,
        actor=user,
        action="auth.login",
        resource_type="auth_session",
        resource_id=session.session_id,
        resource_label=user.username,
        result="success",
    )
    db.commit()
    return LoginResponse(access_token=access_token, user=serialize_current_user(user))


@router.get("/me", response_model=CurrentUserResponse)
def me(user: User = Depends(get_current_user)) -> CurrentUserResponse:
    return serialize_current_user(user)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    user_and_session: tuple[User, AuthSession] = Depends(get_current_user_and_session),
    db: Session = Depends(get_db),
) -> Response:
    user, session = user_and_session
    revoke_session(db, session)
    record_audit_log(
        db,
        actor=user,
        action="auth.logout",
        resource_type="auth_session",
        resource_id=session.session_id,
        resource_label=user.username,
        result="success",
    )
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
