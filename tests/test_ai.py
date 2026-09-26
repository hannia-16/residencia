import json
from collections.abc import AsyncIterator
from typing import Any

import httpx
import pytest
from httpx import AsyncClient

from src.ai.client import DeepSeekClient
from src.ai.config import AIConfig, DeepSeekModel
from src.ai.dependencies import get_ai_client
from src.main import app
from tests.helpers import auth_headers, register

SUCCESS_BODY: dict[str, Any] = {
    "id": "chatcmpl-test",
    "object": "chat.completion",
    "model": "deepseek-flash",
    "choices": [
        {
            "index": 0,
            "message": {"role": "assistant", "content": "Hola, cosa."},
            "finish_reason": "stop",
        }
    ],
    "usage": {
        "prompt_tokens": 12,
        "completion_tokens": 4,
        "total_tokens": 16,
    },
}


class Recorder:
    def __init__(self) -> None:
        self.requests: list[httpx.Request] = []

    @property
    def last_payload(self) -> dict[str, Any]:
        return json.loads(self.requests[-1].content)


def make_client(
    handler: Any, config: AIConfig | None = None
) -> tuple[DeepSeekClient, Recorder]:
    recorder = Recorder()

    def wrapped(request: httpx.Request) -> httpx.Response:
        recorder.requests.append(request)
        return handler(request)

    transport = httpx.MockTransport(wrapped)
    resolved = config or AIConfig(API_KEY="test-key", BASE_URL="https://mock.deepseek")
    return DeepSeekClient(config=resolved, transport=transport), recorder


async def override_client(client: DeepSeekClient) -> AsyncIterator[None]:
    async def _dependency() -> DeepSeekClient:
        yield client

    app.dependency_overrides[get_ai_client] = _dependency


@pytest.fixture
async def authed(client: AsyncClient) -> AsyncClient:
    body = await register(client)
    client.headers.update(auth_headers(body["access_token"]))
    return client


async def test_chat_returns_completion(authed: AsyncClient) -> None:
    deepseek, recorder = make_client(lambda _r: httpx.Response(200, json=SUCCESS_BODY))
    await override_client(deepseek)

    response = await authed.post(
        "/ai/chat", json={"messages": [{"role": "user", "content": "Hola"}]}
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["id"] == "chatcmpl-test"
    assert body["model"] == "deepseek-flash"
    assert body["content"] == "Hola, cosa."
    assert body["finish_reason"] == "stop"
    assert body["usage"] == {
        "prompt_tokens": 12,
        "completion_tokens": 4,
        "total_tokens": 16,
    }
    assert recorder.last_payload["model"] == "deepseek-flash"
    assert recorder.last_payload["stream"] is False
    assert recorder.last_payload["messages"] == [{"role": "user", "content": "Hola"}]
    assert "thinking" not in recorder.last_payload
    assert recorder.requests[-1].headers["Authorization"] == "Bearer test-key"
    await deepseek.aclose()


async def test_chat_sends_thinking_flag_when_requested(authed: AsyncClient) -> None:
    deepseek, recorder = make_client(lambda _r: httpx.Response(200, json=SUCCESS_BODY))
    await override_client(deepseek)

    response = await authed.post(
        "/ai/chat",
        json={
            "messages": [{"role": "user", "content": "Hola"}],
            "thinking": True,
            "model": "deepseek-v4-pro",
        },
    )

    assert response.status_code == 200
    assert recorder.last_payload["thinking"] == {"type": "enabled"}
    assert recorder.last_payload["reasoning_effort"] == "medium"
    assert recorder.last_payload["model"] == "deepseek-v4-pro"
    await deepseek.aclose()


async def test_chat_surfaces_reasoning_content(authed: AsyncClient) -> None:
    body = {
        **SUCCESS_BODY,
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": "Respuesta",
                    "reasoning_content": "Pensando...",
                },
                "finish_reason": "stop",
            }
        ],
    }
    deepseek, _recorder = make_client(lambda _r: httpx.Response(200, json=body))
    await override_client(deepseek)

    response = await authed.post(
        "/ai/chat", json={"messages": [{"role": "user", "content": "Hola"}]}
    )

    assert response.json()["reasoning_content"] == "Pensando..."
    await deepseek.aclose()


async def test_chat_requires_authentication(client: AsyncClient) -> None:
    deepseek, _recorder = make_client(lambda _r: httpx.Response(200, json=SUCCESS_BODY))
    await override_client(deepseek)

    response = await client.post(
        "/ai/chat", json={"messages": [{"role": "user", "content": "Hola"}]}
    )

    assert response.status_code == 401
    await deepseek.aclose()


async def test_chat_rejects_empty_messages(authed: AsyncClient) -> None:
    deepseek, _recorder = make_client(lambda _r: httpx.Response(200, json=SUCCESS_BODY))
    await override_client(deepseek)

    response = await authed.post("/ai/chat", json={"messages": []})

    assert response.status_code == 422
    await deepseek.aclose()


async def test_chat_rejects_unknown_model(authed: AsyncClient) -> None:
    deepseek, _recorder = make_client(lambda _r: httpx.Response(200, json=SUCCESS_BODY))
    await override_client(deepseek)

    response = await authed.post(
        "/ai/chat",
        json={
            "messages": [{"role": "user", "content": "Hola"}],
            "model": "gpt-4o",
        },
    )

    assert response.status_code == 422
    await deepseek.aclose()


async def test_chat_reports_missing_api_key(authed: AsyncClient) -> None:
    config = AIConfig(API_KEY="", BASE_URL="https://mock.deepseek")
    deepseek, _recorder = make_client(
        lambda _r: httpx.Response(200, json=SUCCESS_BODY), config
    )
    await override_client(deepseek)

    response = await authed.post(
        "/ai/chat", json={"messages": [{"role": "user", "content": "Hola"}]}
    )

    assert response.status_code == 503
    assert response.json()["detail"]["code"] == "ai_not_configured"
    await deepseek.aclose()


async def test_chat_maps_rate_limit(authed: AsyncClient) -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            429, headers={"Retry-After": "30"}, json={"error": "slow"}
        )

    deepseek, _recorder = make_client(handler)
    await override_client(deepseek)

    response = await authed.post(
        "/ai/chat", json={"messages": [{"role": "user", "content": "Hola"}]}
    )

    assert response.status_code == 429
    assert response.json()["detail"]["code"] == "ai_rate_limited"
    assert response.headers["Retry-After"] == "30"
    await deepseek.aclose()


async def test_chat_maps_upstream_4xx(authed: AsyncClient) -> None:
    deepseek, _recorder = make_client(
        lambda _r: httpx.Response(400, json={"error": "bad"})
    )
    await override_client(deepseek)

    response = await authed.post(
        "/ai/chat", json={"messages": [{"role": "user", "content": "Hola"}]}
    )

    assert response.status_code == 502
    assert response.json()["detail"]["code"] == "ai_request_rejected"
    await deepseek.aclose()


async def test_chat_maps_upstream_5xx(authed: AsyncClient) -> None:
    deepseek, _recorder = make_client(lambda _r: httpx.Response(503, text="down"))
    await override_client(deepseek)

    response = await authed.post(
        "/ai/chat", json={"messages": [{"role": "user", "content": "Hola"}]}
    )

    assert response.status_code == 502
    assert response.json()["detail"]["code"] == "ai_upstream_error"
    await deepseek.aclose()


async def test_chat_maps_unparseable_response(authed: AsyncClient) -> None:
    deepseek, _recorder = make_client(lambda _r: httpx.Response(200, text="<html>"))
    await override_client(deepseek)

    response = await authed.post(
        "/ai/chat", json={"messages": [{"role": "user", "content": "Hola"}]}
    )

    assert response.status_code == 502
    assert response.json()["detail"]["code"] == "ai_invalid_response"
    await deepseek.aclose()


async def test_chat_maps_timeout(authed: AsyncClient) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("too slow", request=request)

    deepseek, _recorder = make_client(handler)
    await override_client(deepseek)

    response = await authed.post(
        "/ai/chat", json={"messages": [{"role": "user", "content": "Hola"}]}
    )

    assert response.status_code == 504
    assert response.json()["detail"]["code"] == "ai_timeout"
    await deepseek.aclose()


async def test_chat_maps_connection_error(authed: AsyncClient) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("refused", request=request)

    deepseek, _recorder = make_client(handler)
    await override_client(deepseek)

    response = await authed.post(
        "/ai/chat", json={"messages": [{"role": "user", "content": "Hola"}]}
    )

    assert response.status_code == 502
    assert response.json()["detail"]["code"] == "ai_upstream_error"
    await deepseek.aclose()


def test_default_model_is_flash() -> None:
    assert DeepSeekModel.FLASH == "deepseek-flash"
    assert DeepSeekModel.V4_PRO == "deepseek-v4-pro"
