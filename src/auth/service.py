import uuid

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.config import auth_settings
from src.auth.constants import TokenType
from src.auth.exceptions import (
    InvalidCredentials,
    UserAlreadyExists,
    UserNotActive,
    UserNotFound,
)
from src.auth.models import User
from src.auth.repository import UserRepository
from src.auth.schemas import TokenPair, UserCreate, UserLogin, UserRead
from src.auth.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)


def _token_pair(user: User) -> TokenPair:
    return TokenPair(
        access_token=create_access_token(user.id),
        refresh_token=create_refresh_token(user.id),
        expires_in=auth_settings.JWT_EXP_MINUTES * 60,
        user=UserRead.model_validate(user),
    )


async def _get_active_user(session: AsyncSession, user_id: uuid.UUID) -> User:
    users = UserRepository(session)
    user = await users.get(user_id)
    if user is None:
        raise UserNotFound()
    if not user.is_active:
        raise UserNotActive()
    return user


async def create_user(session: AsyncSession, data: UserCreate) -> TokenPair:
    users = UserRepository(session)
    email = str(data.email)
    if await users.exists(email=email) or await users.exists(username=data.username):
        raise UserAlreadyExists()
    try:
        user = await users.create(
            email=email,
            username=data.username,
            hashed_password=hash_password(data.password),
            is_active=True,
        )
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise UserAlreadyExists() from exc
    return _token_pair(user)


async def authenticate(session: AsyncSession, data: UserLogin) -> TokenPair:
    users = UserRepository(session)
    user = await users.get_by_email(str(data.email))
    if user is None or not verify_password(data.password, user.hashed_password):
        raise InvalidCredentials()
    if not user.is_active:
        raise UserNotActive()
    return _token_pair(user)


async def refresh_token_pair(session: AsyncSession, token: str) -> TokenPair:
    payload = decode_token(token, expected_type=TokenType.REFRESH)
    user = await _get_active_user(session, payload["user_id"])
    return _token_pair(user)


async def get_current_user(session: AsyncSession, user_id: uuid.UUID) -> User:
    return await _get_active_user(session, user_id)
