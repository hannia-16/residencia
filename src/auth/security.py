import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import jwt
from jwt.exceptions import InvalidTokenError
from pwdlib import PasswordHash
from pwdlib.exceptions import UnknownHashError

from src.auth.config import auth_settings
from src.auth.constants import TokenType
from src.auth.exceptions import InvalidCredentials, InvalidToken

password_hash = PasswordHash.recommended()


def hash_password(password: str) -> str:
    return password_hash.hash(password)


def verify_password(password: str, hashed: str) -> bool:
    try:
        return password_hash.verify(password, hashed)
    except (UnknownHashError, ValueError):
        return False


def _create_token(
    *,
    subject: uuid.UUID | str,
    token_type: TokenType,
    key: str,
    expires_in: timedelta,
) -> str:
    now = datetime.now(UTC)
    payload: dict[str, Any] = {
        "sub": str(subject),
        "type": token_type.value,
        "jti": uuid.uuid4().hex,
        "iat": now,
        "exp": now + expires_in,
    }
    return jwt.encode(payload, key, algorithm=auth_settings.JWT_ALG)


def create_access_token(
    subject: uuid.UUID | str,
    expires_in: timedelta | None = None,
) -> str:
    return _create_token(
        subject=subject,
        token_type=TokenType.ACCESS,
        key=auth_settings.JWT_SECRET,
        expires_in=expires_in or auth_settings.access_token_exp,
    )


def create_refresh_token(
    subject: uuid.UUID | str,
    expires_in: timedelta | None = None,
) -> str:
    return _create_token(
        subject=subject,
        token_type=TokenType.REFRESH,
        key=auth_settings.REFRESH_TOKEN_KEY,
        expires_in=expires_in or auth_settings.REFRESH_TOKEN_EXP,
    )


def decode_token(token: str, *, expected_type: TokenType) -> dict[str, Any]:
    key = (
        auth_settings.JWT_SECRET
        if expected_type is TokenType.ACCESS
        else auth_settings.REFRESH_TOKEN_KEY
    )
    try:
        payload = jwt.decode(token, key, algorithms=[auth_settings.JWT_ALG])
    except InvalidTokenError as exc:
        raise InvalidToken() from exc
    if payload.get("type") != expected_type.value:
        raise InvalidToken("The token is not valid for this operation.")
    subject = payload.get("sub")
    if not subject:
        raise InvalidToken("The token is missing a subject.")
    try:
        payload["user_id"] = uuid.UUID(str(subject))
    except ValueError as exc:
        raise InvalidToken("The token subject is not a valid identifier.") from exc
    return payload


def authenticate_password(password: str, hashed: str) -> None:
    if not verify_password(password, hashed):
        raise InvalidCredentials()
