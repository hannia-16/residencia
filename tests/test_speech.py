from typing import Any

import httpx
import pytest

from src.speech.client import GroqSpeechToText
from src.speech.config import SpeechConfig
from src.speech.exceptions import (
    SpeechNotConfigured,
    SpeechRateLimited,
    SpeechRequestError,
    SpeechResponseError,
    SpeechTimeout,
    SpeechUpstreamError,
)


def make_client(handler: Any, config: SpeechConfig | None = None) -> GroqSpeechToText:
    transport = httpx.MockTransport(handler)
    resolved = config or SpeechConfig(API_KEY="test-key", BASE_URL="https://mock.groq")
    return GroqSpeechToText(config=resolved, transport=transport)


async def test_transcribe_returns_text() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/audio/transcriptions"
        assert request.headers["Authorization"] == "Bearer test-key"
        body = request.content
        assert b'name="model"' in body
        assert b"whisper-large-v3" in body
        assert b'name="file"' in body
        return httpx.Response(200, json={"text": "Hello there"})

    client = make_client(handler)
    text = await client.transcribe(
        b"audio-bytes", filename="turno.webm", content_type="audio/webm"
    )

    assert text == "Hello there"
    await client.aclose()


async def test_transcribe_reports_missing_api_key() -> None:
    client = make_client(
        lambda _r: httpx.Response(200, json={"text": "hi"}),
        SpeechConfig(API_KEY="", BASE_URL="https://mock.groq"),
    )

    with pytest.raises(SpeechNotConfigured):
        await client.transcribe(
            b"audio", filename="turno.webm", content_type="audio/webm"
        )
    await client.aclose()


async def test_transcribe_maps_rate_limit() -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(429, headers={"Retry-After": "30"}, json={})

    client = make_client(handler)

    with pytest.raises(SpeechRateLimited) as excinfo:
        await client.transcribe(
            b"audio", filename="turno.webm", content_type="audio/webm"
        )

    assert excinfo.value.headers == {"Retry-After": "30"}
    await client.aclose()


async def test_transcribe_maps_timeout() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("too slow", request=request)

    client = make_client(handler)

    with pytest.raises(SpeechTimeout):
        await client.transcribe(
            b"audio", filename="turno.webm", content_type="audio/webm"
        )
    await client.aclose()


async def test_transcribe_maps_connection_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("refused", request=request)

    client = make_client(handler)

    with pytest.raises(SpeechUpstreamError):
        await client.transcribe(
            b"audio", filename="turno.webm", content_type="audio/webm"
        )
    await client.aclose()


async def test_transcribe_maps_upstream_4xx() -> None:
    client = make_client(lambda _r: httpx.Response(400, json={"error": "bad"}))

    with pytest.raises(SpeechRequestError):
        await client.transcribe(
            b"audio", filename="turno.webm", content_type="audio/webm"
        )
    await client.aclose()


async def test_transcribe_maps_upstream_5xx() -> None:
    client = make_client(lambda _r: httpx.Response(503, text="down"))

    with pytest.raises(SpeechUpstreamError):
        await client.transcribe(
            b"audio", filename="turno.webm", content_type="audio/webm"
        )
    await client.aclose()


async def test_transcribe_maps_unparseable_response() -> None:
    client = make_client(lambda _r: httpx.Response(200, text="<html>"))

    with pytest.raises(SpeechResponseError):
        await client.transcribe(
            b"audio", filename="turno.webm", content_type="audio/webm"
        )
    await client.aclose()


async def test_transcribe_rejects_unexpected_payload() -> None:
    client = make_client(lambda _r: httpx.Response(200, json=["nope"]))

    with pytest.raises(SpeechResponseError):
        await client.transcribe(
            b"audio", filename="turno.webm", content_type="audio/webm"
        )
    await client.aclose()
