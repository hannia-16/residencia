from httpx import AsyncClient

FRONTEND_ORIGIN = "http://127.0.0.1:5173"


async def test_preflight_allows_frontend_origin(client: AsyncClient) -> None:
    response = await client.options(
        "/auth/signup",
        headers={
            "Origin": FRONTEND_ORIGIN,
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == FRONTEND_ORIGIN
    assert response.headers["access-control-allow-credentials"] == "true"
    assert "POST" in response.headers["access-control-allow-methods"]


async def test_actual_request_includes_cors_headers(client: AsyncClient) -> None:
    response = await client.get("/health", headers={"Origin": FRONTEND_ORIGIN})

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == FRONTEND_ORIGIN


async def test_disallowed_origin_gets_no_cors_headers(client: AsyncClient) -> None:
    response = await client.options(
        "/auth/signup",
        headers={
            "Origin": "http://evil.example.com",
            "Access-Control-Request-Method": "POST",
        },
    )

    assert "access-control-allow-origin" not in response.headers
