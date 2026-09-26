import uuid
from typing import Annotated

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from src.auth.constants import TokenType
from src.auth.exceptions import InvalidToken
from src.auth.models import User
from src.auth.security import decode_token
from src.auth.service import get_current_user
from src.datasources.dependencies import DbSession

bearer_scheme = HTTPBearer(auto_error=False)


async def parse_jwt_data(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
) -> dict:
    if credentials is None or not credentials.credentials:
        raise InvalidToken("An Authorization header is required.")
    return decode_token(credentials.credentials, expected_type=TokenType.ACCESS)


async def valid_user(
    token_data: Annotated[dict, Depends(parse_jwt_data)],
    session: DbSession,
) -> User:
    return await get_current_user(session, token_data["user_id"])


TokenData = Annotated[dict, Depends(parse_jwt_data)]
CurrentUser = Annotated[User, Depends(valid_user)]


def user_id_from(token_data: dict) -> uuid.UUID:
    return token_data["user_id"]
