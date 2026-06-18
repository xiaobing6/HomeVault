from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

import jwt
from pwdlib import PasswordHash

ALGORITHM = "HS256"
password_hasher = PasswordHash.recommended()


@dataclass(frozen=True)
class AccessTokenPayload:
    user_id: int
    session_id: str
    expires_at: datetime


def hash_password(password: str) -> str:
    return password_hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return password_hasher.verify(password, password_hash)


def create_access_token(user_id: int, session_id: str, secret_key: str, minutes: int) -> str:
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=minutes)
    payload = {
        "sub": str(user_id),
        "sid": session_id,
        "exp": expires_at,
    }
    return jwt.encode(payload, secret_key, algorithm=ALGORITHM)


def decode_access_token(token: str, secret_key: str) -> AccessTokenPayload:
    try:
        payload = jwt.decode(token, secret_key, algorithms=[ALGORITHM])
        user_id = int(payload["sub"])
        session_id = str(payload["sid"])
        expires_at = datetime.fromtimestamp(int(payload["exp"]), tz=timezone.utc)
    except Exception as exc:
        raise ValueError("登录状态无效，请重新登录") from exc
    return AccessTokenPayload(user_id=user_id, session_id=session_id, expires_at=expires_at)
