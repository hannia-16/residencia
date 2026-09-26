import uuid
from datetime import UTC, datetime, timedelta

import jwt
import pytest

from src.auth.config import auth_settings
from src.auth.constants import TokenType
from src.auth.exceptions import InvalidToken
from src.auth.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)


def make_token(payload: dict, key: str) -> str:
    now = datetime.now(UTC)
    return jwt.encode(
        {**payload, "iat": now, "exp": now + timedelta(minutes=5)},
        key,
        algorithm=auth_settings.JWT_ALG,
    )


def test_hash_and_verify_password() -> None:
    hashed = hash_password("correct-horse-battery")

    assert hashed != "correct-horse-battery"
    assert verify_password("correct-horse-battery", hashed) is True
    assert verify_password("wrong", hashed) is False


def test_verify_password_tolerates_garbage_hash() -> None:
    assert verify_password("anything", "not-a-real-hash") is False


def test_access_token_round_trip() -> None:
    user_id = uuid.uuid4()

    payload = decode_token(create_access_token(user_id), expected_type=TokenType.ACCESS)

    assert payload["user_id"] == user_id
    assert payload["sub"] == str(user_id)
    assert payload["type"] == "access"


def test_refresh_token_round_trip() -> None:
    user_id = uuid.uuid4()

    payload = decode_token(
        create_refresh_token(user_id), expected_type=TokenType.REFRESH
    )

    assert payload["user_id"] == user_id
    assert payload["type"] == "refresh"


def test_access_and_refresh_tokens_are_not_interchangeable() -> None:
    user_id = uuid.uuid4()

    with pytest.raises(InvalidToken):
        decode_token(create_refresh_token(user_id), expected_type=TokenType.ACCESS)

    with pytest.raises(InvalidToken):
        decode_token(create_access_token(user_id), expected_type=TokenType.REFRESH)


def test_access_token_signed_with_refresh_key_is_rejected() -> None:
    forged = make_token(
        {"sub": str(uuid.uuid4()), "type": "access"}, auth_settings.REFRESH_TOKEN_KEY
    )

    with pytest.raises(InvalidToken):
        decode_token(forged, expected_type=TokenType.ACCESS)


def test_expired_token_is_rejected() -> None:
    token = create_access_token(uuid.uuid4(), expires_in=timedelta(seconds=-10))

    with pytest.raises(InvalidToken):
        decode_token(token, expected_type=TokenType.ACCESS)


def test_malformed_token_is_rejected() -> None:
    with pytest.raises(InvalidToken):
        decode_token("clearly.not.a.jwt", expected_type=TokenType.ACCESS)


def test_token_without_subject_is_rejected() -> None:
    token = make_token({"type": "access"}, auth_settings.JWT_SECRET)

    with pytest.raises(InvalidToken):
        decode_token(token, expected_type=TokenType.ACCESS)


def test_token_with_non_uuid_subject_is_rejected() -> None:
    token = make_token(
        {"sub": "not-a-uuid", "type": "access"}, auth_settings.JWT_SECRET
    )

    with pytest.raises(InvalidToken):
        decode_token(token, expected_type=TokenType.ACCESS)
