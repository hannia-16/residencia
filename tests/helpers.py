from httpx import AsyncClient

from tests.factories import VALID_SIGNUP


async def register(client: AsyncClient) -> dict:
    response = await client.post("/auth/signup", json=VALID_SIGNUP)
    assert response.status_code == 201, response.text
    return response.json()


def auth_headers(access_token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {access_token}"}
