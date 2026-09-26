import pytest
from httpx import AsyncClient

from tests.factories import VALID_SIGNUP, unique_signup
from tests.helpers import auth_headers, register


async def test_signup_creates_user_and_returns_pair(client: AsyncClient) -> None:
    body = await register(client)

    assert body["token_type"] == "bearer"
    assert body["expires_in"] == 300
    assert body["user"]["email"] == VALID_SIGNUP["email"]
    assert body["user"]["username"] == VALID_SIGNUP["username"]
    assert body["user"]["is_active"] is True
    assert "password" not in body["user"]
    assert "hashed_password" not in body["user"]


async def test_signup_sets_httponly_refresh_cookie(client: AsyncClient) -> None:
    response = await client.post("/auth/signup", json=VALID_SIGNUP)

    cookie_header = response.headers.get("set-cookie", "")
    assert "refresh_token=" in cookie_header
    assert "HttpOnly" in cookie_header
    assert "Path=/auth" in cookie_header
    assert "Secure" not in cookie_header


@pytest.mark.parametrize(
    "payload",
    [
        {"email": "not-an-email", "username": "kenia", "password": "correct-horse"},
        {"email": "a@b.com", "username": "bad name", "password": "correct-horse"},
        {"email": "a@b.com", "username": "kenia", "password": "short"},
    ],
)
async def test_signup_rejects_invalid_payload(
    client: AsyncClient, payload: dict[str, str]
) -> None:
    response = await client.post("/auth/signup", json=payload)

    assert response.status_code == 422


async def test_signup_rejects_duplicate_email(client: AsyncClient) -> None:
    await register(client)

    response = await client.post("/auth/signup", json=unique_signup("dup"))

    assert response.status_code == 201

    duplicate = await client.post(
        "/auth/signup",
        json={**unique_signup("dup"), "username": "another_name"},
    )
    assert duplicate.status_code == 409
    assert duplicate.json()["detail"]["code"] == "user_already_exists"


async def test_login_returns_new_pair(client: AsyncClient) -> None:
    await register(client)

    response = await client.post(
        "/auth/login",
        json={
            "email": VALID_SIGNUP["email"],
            "password": VALID_SIGNUP["password"],
        },
    )

    assert response.status_code == 200
    assert response.json()["user"]["email"] == VALID_SIGNUP["email"]


async def test_login_rejects_wrong_password(client: AsyncClient) -> None:
    await register(client)

    response = await client.post(
        "/auth/login",
        json={"email": VALID_SIGNUP["email"], "password": "wrong-password"},
    )

    assert response.status_code == 401
    assert response.json()["detail"]["code"] == "invalid_credentials"


async def test_login_rejects_unknown_email(client: AsyncClient) -> None:
    response = await client.post(
        "/auth/login",
        json={"email": "ghost@example.com", "password": "correct-horse"},
    )

    assert response.status_code == 401
    assert response.json()["detail"]["code"] == "invalid_credentials"


async def test_refresh_rotates_pair_using_cookie(client: AsyncClient) -> None:
    first = await register(client)

    response = await client.post("/auth/refresh")

    assert response.status_code == 200
    rotated = response.json()
    assert rotated["access_token"] != first["access_token"]
    assert rotated["user"]["id"] == first["user"]["id"]


async def test_refresh_requires_cookie(client: AsyncClient) -> None:
    response = await client.post("/auth/refresh")

    assert response.status_code == 401
    assert response.json()["detail"]["code"] == "invalid_token"


async def test_refresh_rejects_access_token(client: AsyncClient) -> None:
    body = await register(client)
    client.cookies.set("refresh_token", body["access_token"])

    response = await client.post("/auth/refresh")

    assert response.status_code == 401
    assert response.json()["detail"]["code"] == "invalid_token"


async def test_me_returns_authenticated_user(client: AsyncClient) -> None:
    body = await register(client)

    response = await client.get("/auth/me", headers=auth_headers(body["access_token"]))

    assert response.status_code == 200
    assert response.json()["email"] == VALID_SIGNUP["email"]


async def test_me_rejects_missing_token(client: AsyncClient) -> None:
    response = await client.get("/auth/me")

    assert response.status_code == 401
    assert response.json()["detail"]["code"] == "invalid_token"


async def test_me_rejects_garbage_token(client: AsyncClient) -> None:
    response = await client.get("/auth/me", headers=auth_headers("not.a.real.token"))

    assert response.status_code == 401
    assert response.json()["detail"]["code"] == "invalid_token"


async def test_me_rejects_refresh_token(client: AsyncClient) -> None:
    body = await register(client)

    response = await client.get("/auth/me", headers=auth_headers(body["refresh_token"]))

    assert response.status_code == 401
    assert response.json()["detail"]["code"] == "invalid_token"


async def test_me_rejects_token_for_deleted_user(client: AsyncClient) -> None:
    from src.auth.security import create_access_token

    token = create_access_token("00000000-0000-0000-0000-0000000000ff")

    response = await client.get("/auth/me", headers=auth_headers(token))

    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "user_not_found"


async def test_logout_clears_cookie(client: AsyncClient) -> None:
    await register(client)

    response = await client.post("/auth/logout")

    assert response.status_code == 204
    assert 'refresh_token=""' in response.headers.get("set-cookie", "") or (
        "refresh_token=;" in response.headers.get("set-cookie", "")
    )
