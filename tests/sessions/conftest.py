import pytest
from httpx import AsyncClient

from tests.helpers import auth_headers, register


@pytest.fixture
async def authed(client: AsyncClient) -> AsyncClient:
    body = await register(client)
    client.headers.update(auth_headers(body["access_token"]))
    return client
