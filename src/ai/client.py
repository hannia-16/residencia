from collections.abc import Sequence
from typing import Any

import httpx

from src.ai.config import AIConfig, DeepSeekModel, ReasoningEffort, ai_settings
from src.ai.constants import CHAT_COMPLETIONS_PATH
from src.ai.exceptions import (
    AINotConfigured,
    AIRateLimited,
    AIRequestError,
    AIResponseError,
    AITimeout,
    AIUpstreamError,
)
from src.ai.schemas import ChatMessage, ChatResponse, TokenUsage


class DeepSeekClient:
    def __init__(
        self,
        *,
        config: AIConfig | None = None,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self.config = config or ai_settings
        self._transport = transport
        self._client: httpx.AsyncClient | None = None

    def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self.config.BASE_URL,
                timeout=self.config.TIMEOUT_SECONDS,
                transport=self._transport,
                headers={
                    "Authorization": f"Bearer {self.config.API_KEY}",
                    "Content-Type": "application/json",
                },
            )
        return self._client

    async def aclose(self) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    async def __aenter__(self) -> "DeepSeekClient":
        return self

    async def __aexit__(self, *_exc: object) -> None:
        await self.aclose()

    def _build_payload(
        self,
        messages: Sequence[ChatMessage],
        *,
        model: DeepSeekModel | None,
        thinking: bool | None,
        reasoning_effort: ReasoningEffort | None,
        temperature: float | None,
        max_tokens: int | None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "model": (model or self.config.MODEL).value,
            "messages": [
                {"role": message.role.value, "content": message.content}
                for message in messages
            ],
            "stream": False,
            "temperature": (
                self.config.TEMPERATURE if temperature is None else temperature
            ),
            "max_tokens": self.config.MAX_TOKENS if max_tokens is None else max_tokens,
        }
        use_thinking = self.config.THINKING if thinking is None else thinking
        if use_thinking:
            payload["thinking"] = {"type": "enabled"}
            payload["reasoning_effort"] = (
                reasoning_effort or self.config.REASONING_EFFORT
            )
        return payload

    def _raise_for_status(self, response: httpx.Response) -> None:
        if response.is_success:
            return
        if response.status_code == 429:
            retry_after = response.headers.get("Retry-After")
            headers = {"Retry-After": retry_after} if retry_after else None
            raise AIRateLimited(headers=headers)
        if 400 <= response.status_code < 500:
            raise AIRequestError(
                f"The AI provider rejected the request (HTTP {response.status_code})."
            )
        raise AIUpstreamError(f"The AI provider returned HTTP {response.status_code}.")

    @staticmethod
    def _parse(response: httpx.Response) -> ChatResponse:
        try:
            data = response.json()
            choice = data["choices"][0]
            message = choice["message"]
        except (ValueError, KeyError, IndexError, TypeError) as exc:
            raise AIResponseError() from exc
        usage = data.get("usage") or {}
        return ChatResponse(
            id=str(data.get("id", "")),
            model=str(data.get("model", "")),
            content=message.get("content") or "",
            reasoning_content=message.get("reasoning_content"),
            finish_reason=choice.get("finish_reason"),
            usage=TokenUsage(
                prompt_tokens=int(usage.get("prompt_tokens") or 0),
                completion_tokens=int(usage.get("completion_tokens") or 0),
                total_tokens=int(usage.get("total_tokens") or 0),
            ),
        )

    async def chat(
        self,
        messages: Sequence[ChatMessage],
        *,
        model: DeepSeekModel | None = None,
        thinking: bool | None = None,
        reasoning_effort: ReasoningEffort | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> ChatResponse:
        if not self.config.is_configured:
            raise AINotConfigured()
        payload = self._build_payload(
            messages,
            model=model,
            thinking=thinking,
            reasoning_effort=reasoning_effort,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        try:
            response = await self._get_client().post(
                CHAT_COMPLETIONS_PATH, json=payload
            )
        except httpx.TimeoutException as exc:
            raise AITimeout() from exc
        except httpx.RequestError as exc:
            raise AIUpstreamError("The AI provider is unreachable.") from exc
        self._raise_for_status(response)
        return self._parse(response)
