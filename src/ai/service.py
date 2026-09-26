from src.ai.client import DeepSeekClient
from src.ai.schemas import ChatRequest, ChatResponse


async def complete_chat(client: DeepSeekClient, payload: ChatRequest) -> ChatResponse:
    return await client.chat(
        payload.messages,
        model=payload.model,
        thinking=payload.thinking,
    )
