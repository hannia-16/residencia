import json
from typing import Any

import httpx
from httpx import AsyncClient

from src.ai.client import DeepSeekClient
from src.ai.config import AIConfig
from src.ai.dependencies import get_ai_client
from src.main import app
from src.speech.dependencies import get_speech_client

DEFAULT_TURN = "Hello! What would you like to do?"
DEFAULT_REPORT = "Good job overall."


def chat_body(content: str) -> dict[str, Any]:
    return {
        "id": "chatcmpl-test",
        "model": "deepseek-flash",
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": content},
                "finish_reason": "stop",
            }
        ],
        "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
    }


def turn_ia(mensaje: str = DEFAULT_TURN, errores: list[dict] | None = None) -> str:
    return json.dumps({"mensaje": mensaje, "errores": errores or []})


def correccion(
    tipo: str = "gramatica",
    original: str = "I go yesterday",
    correccion_texto: str = "I went yesterday",
    explicacion: str = "Use the past tense with yesterday.",
) -> dict:
    return {
        "tipo": tipo,
        "original": original,
        "correccion": correccion_texto,
        "explicacion": explicacion,
    }


def informe_ia(resumen: str = DEFAULT_REPORT, **extra: list[str]) -> str:
    return json.dumps(
        {
            "resumen": resumen,
            "gramatica": extra.get("gramatica", []),
            "vocabulario": extra.get("vocabulario", []),
            "areas_mejora": extra.get("areas_mejora", ["Practice past tenses"]),
            "fortalezas": extra.get("fortalezas", ["Good interaction"]),
        }
    )


class FakeLLM:
    def __init__(self, *contents: str, api_key: str = "test-key") -> None:
        assert contents, "FakeLLM needs at least one scripted response."
        self._queue = list(contents)
        self._client = DeepSeekClient(
            config=AIConfig(API_KEY=api_key, BASE_URL="https://mock.deepseek"),
            transport=httpx.MockTransport(self._handle),
        )
        self.requests: list[dict[str, Any]] = []

    def _handle(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(json.loads(request.content))
        content = self._queue.pop(0) if len(self._queue) > 1 else self._queue[0]
        return httpx.Response(200, json=chat_body(content))

    @property
    def client(self) -> DeepSeekClient:
        return self._client


def use_llm(fake: FakeLLM) -> None:
    app.dependency_overrides[get_ai_client] = lambda: fake.client


class FakeSpeechToText:
    def __init__(self, text: str = "I would like a coffee, please.") -> None:
        self.text = text
        self.calls: list[tuple[bytes, str, str]] = []

    async def transcribe(self, data: bytes, *, filename: str, content_type: str) -> str:
        self.calls.append((data, filename, content_type))
        return self.text


def use_speech(speech: FakeSpeechToText) -> None:
    app.dependency_overrides[get_speech_client] = lambda: speech


async def start_session(
    client: AsyncClient,
    fake: FakeLLM | None = None,
    *,
    escenario: str = "restaurante",
    nivel: str = "B1",
) -> tuple[FakeLLM, dict]:
    resolved = fake or FakeLLM(turn_ia())
    use_llm(resolved)
    response = await client.post(
        "/sessions", json={"escenario": escenario, "nivel": nivel}
    )
    assert response.status_code == 201, response.text
    return resolved, response.json()
