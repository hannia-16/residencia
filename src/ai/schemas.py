from enum import StrEnum

from pydantic import Field

from src.ai.config import DeepSeekModel
from src.models import CustomModel


class MessageRole(StrEnum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"


class ChatMessage(CustomModel):
    role: MessageRole
    content: str = Field(min_length=1)


class ChatRequest(CustomModel):
    messages: list[ChatMessage] = Field(min_length=1)
    model: DeepSeekModel | None = None
    thinking: bool | None = None


class TokenUsage(CustomModel):
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


class ChatResponse(CustomModel):
    id: str
    model: str
    content: str
    reasoning_content: str | None = None
    finish_reason: str | None = None
    usage: TokenUsage = Field(default_factory=TokenUsage)
