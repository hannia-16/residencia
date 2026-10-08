import json
from collections.abc import Sequence
from typing import TypeVar

from pydantic import ValidationError

from src.ai.client import DeepSeekClient
from src.ai.schemas import ChatMessage, MessageRole
from src.models import CustomModel
from src.sessions.exceptions import TurnFailed
from src.sessions.prompts import build_correction_prompt

T = TypeVar("T", bound=CustomModel)

MAX_ATTEMPTS = 2
JSON_RESPONSE_FORMAT = {"type": "json_object"}


def _loads(content: str) -> object:
    text = content.strip()
    if text.startswith("```"):
        text = text.strip("`").strip()
        if text.startswith("json"):
            text = text[4:]
    return json.loads(text)


async def complete_structured(
    client: DeepSeekClient,
    messages: Sequence[ChatMessage],
    schema: type[T],
    *,
    max_tokens: int | None = None,
) -> T:
    conversation = list(messages)
    last_error: Exception | None = None
    for attempt in range(MAX_ATTEMPTS):
        response = await client.chat(
            conversation,
            response_format=JSON_RESPONSE_FORMAT,
            max_tokens=max_tokens,
        )
        try:
            return schema.model_validate(_loads(response.content))
        except (ValueError, ValidationError) as exc:
            last_error = exc
            if attempt + 1 < MAX_ATTEMPTS:
                conversation.extend(
                    [
                        ChatMessage(
                            role=MessageRole.ASSISTANT,
                            content=response.content,
                        ),
                        ChatMessage(
                            role=MessageRole.USER,
                            content=build_correction_prompt(str(exc)),
                        ),
                    ]
                )
    raise TurnFailed() from last_error
