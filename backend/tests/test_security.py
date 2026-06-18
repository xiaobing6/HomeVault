from datetime import datetime, timezone

import pytest

from app.core.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)

UNIT_TEST_SECRET = "unit-test-secret-with-at-least-32-bytes"
DIFFERENT_UNIT_TEST_SECRET = "different-unit-test-secret-32-bytes"


def test_password_hash_verifies_plain_password() -> None:
    password_hash = hash_password("ChangeMe123!")

    assert password_hash != "ChangeMe123!"
    assert verify_password("ChangeMe123!", password_hash) is True
    assert verify_password("wrong-password", password_hash) is False


def test_access_token_round_trip() -> None:
    token = create_access_token(
        user_id=7,
        session_id="session-123",
        secret_key=UNIT_TEST_SECRET,
        minutes=30,
    )

    payload = decode_access_token(token, secret_key=UNIT_TEST_SECRET)

    assert payload.user_id == 7
    assert payload.session_id == "session-123"
    assert payload.expires_at > datetime.now(timezone.utc)


def test_access_token_rejects_wrong_secret() -> None:
    token = create_access_token(
        user_id=7,
        session_id="session-123",
        secret_key=UNIT_TEST_SECRET,
        minutes=30,
    )

    with pytest.raises(ValueError, match="登录状态无效"):
        decode_access_token(token, secret_key=DIFFERENT_UNIT_TEST_SECRET)
