from typing import Protocol

import httpx

from src.speech.config import SpeechConfig, speech_settings
from src.speech.constants import TRANSCRIPTIONS_PATH
from src.speech.exceptions import (
    SpeechNotConfigured,
    SpeechRateLimited,
    SpeechRequestError,
    SpeechResponseError,
    SpeechTimeout,
    SpeechUpstreamError,
)


class SpeechToText(Protocol):
    async def transcribe(
        self, data: bytes, *, filename: str, content_type: str
    ) -> str: ...


class GroqSpeechToText:
    def __init__(
        self,
        *,
        config: SpeechConfig | None = None,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self.config = config or speech_settings
        self._transport = transport
        self._client: httpx.AsyncClient | None = None

    def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self.config.BASE_URL,
                timeout=self.config.TIMEOUT_SECONDS,
                transport=self._transport,
                headers={"Authorization": f"Bearer {self.config.API_KEY}"},
            )
        return self._client

    async def aclose(self) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    async def __aenter__(self) -> "GroqSpeechToText":
        return self

    async def __aexit__(self, *_exc: object) -> None:
        await self.aclose()

    def _raise_for_status(self, response: httpx.Response) -> None:
        if response.is_success:
            return
        if response.status_code == 429:
            retry_after = response.headers.get("Retry-After")
            headers = {"Retry-After": retry_after} if retry_after else None
            raise SpeechRateLimited(headers=headers)
        if 400 <= response.status_code < 500:
            raise SpeechRequestError(
                f"The speech service rejected the audio (HTTP {response.status_code})."
            )
        raise SpeechUpstreamError(
            f"The speech service returned HTTP {response.status_code}."
        )

    async def transcribe(self, data: bytes, *, filename: str, content_type: str) -> str:
        if not self.config.is_configured:
            raise SpeechNotConfigured()
        files = {"file": (filename, data, content_type)}
        form = {
            "model": self.config.STT_MODEL,
            "language": self.config.STT_LANGUAGE,
            "response_format": "json",
        }
        try:
            response = await self._get_client().post(
                TRANSCRIPTIONS_PATH, data=form, files=files
            )
        except httpx.TimeoutException as exc:
            raise SpeechTimeout() from exc
        except httpx.RequestError as exc:
            raise SpeechUpstreamError("The speech service is unreachable.") from exc
        self._raise_for_status(response)
        try:
            payload = response.json()
        except ValueError as exc:
            raise SpeechResponseError() from exc
        if not isinstance(payload, dict) or not isinstance(payload.get("text"), str):
            raise SpeechResponseError()
        return payload["text"]
