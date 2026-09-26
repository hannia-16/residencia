from typing import Annotated

from fastapi import APIRouter, Cookie, Response, status

from src.auth import service as auth_service
from src.auth.config import auth_settings
from src.auth.dependencies import CurrentUser
from src.auth.exceptions import InvalidToken
from src.auth.schemas import TokenPair, UserCreate, UserLogin, UserRead
from src.datasources.dependencies import DbSession
from src.exceptions import ErrorResponse

router = APIRouter(prefix="/auth", tags=["auth"])

ERROR_RESPONSES = {
    status.HTTP_401_UNAUTHORIZED: {
        "model": ErrorResponse,
        "description": "Invalid credentials",
    },
    status.HTTP_409_CONFLICT: {
        "model": ErrorResponse,
        "description": "User already exists",
    },
}


def _set_refresh_cookie(response: Response, refresh_token: str) -> None:
    response.set_cookie(
        key=auth_settings.REFRESH_COOKIE_NAME,
        value=refresh_token,
        max_age=int(auth_settings.REFRESH_TOKEN_EXP.total_seconds()),
        httponly=True,
        secure=auth_settings.SECURE_COOKIES,
        samesite="lax",
        path="/auth",
    )


@router.post(
    "/signup",
    response_model=TokenPair,
    status_code=status.HTTP_201_CREATED,
    summary="Create an account",
    description="Registers a new user and returns a fresh token pair.",
    responses={
        status.HTTP_409_CONFLICT: {
            "model": ErrorResponse,
            "description": "Email or username already registered",
        }
    },
)
async def signup(
    payload: UserCreate, response: Response, session: DbSession
) -> TokenPair:
    pair = await auth_service.create_user(session, payload)
    _set_refresh_cookie(response, pair.refresh_token)
    return pair


@router.post(
    "/login",
    response_model=TokenPair,
    summary="Exchange credentials for tokens",
    responses=ERROR_RESPONSES,
)
async def login(
    payload: UserLogin, response: Response, session: DbSession
) -> TokenPair:
    pair = await auth_service.authenticate(session, payload)
    _set_refresh_cookie(response, pair.refresh_token)
    return pair


@router.post(
    "/refresh",
    response_model=TokenPair,
    summary="Rotate a token pair",
    description="Reads the refresh token cookie and issues a new access/refresh pair.",
    responses=ERROR_RESPONSES,
)
async def refresh(
    response: Response,
    session: DbSession,
    refresh_token: Annotated[
        str | None, Cookie(alias=auth_settings.REFRESH_COOKIE_NAME)
    ] = None,
) -> TokenPair:
    if not refresh_token:
        raise InvalidToken("A refresh token cookie is required.")
    pair = await auth_service.refresh_token_pair(session, refresh_token)
    _set_refresh_cookie(response, pair.refresh_token)
    return pair


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Clear the refresh cookie",
)
async def logout(response: Response) -> None:
    response.delete_cookie(
        key=auth_settings.REFRESH_COOKIE_NAME,
        path="/auth",
    )


@router.get(
    "/me",
    response_model=UserRead,
    summary="Return the authenticated user",
    responses={
        status.HTTP_401_UNAUTHORIZED: {
            "model": ErrorResponse,
            "description": "Missing or invalid access token",
        }
    },
)
async def read_me(user: CurrentUser) -> UserRead:
    return UserRead.model_validate(user)
