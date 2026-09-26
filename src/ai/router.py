from fastapi import APIRouter, status

from src.ai import service as ai_service
from src.ai.dependencies import AIClient
from src.ai.schemas import ChatRequest, ChatResponse
from src.auth.dependencies import CurrentUser
from src.exceptions import ErrorResponse

router = APIRouter(prefix="/ai", tags=["ai"])


@router.post(
    "/chat",
    response_model=ChatResponse,
    summary="Proxy a chat completion to DeepSeek",
    description=(
        "Sends the supplied messages to the configured DeepSeek model and returns the "
        "completion. Nothing is persisted."
    ),
    responses={
        status.HTTP_401_UNAUTHORIZED: {
            "model": ErrorResponse,
            "description": "Missing or invalid access token",
        },
        status.HTTP_429_TOO_MANY_REQUESTS: {
            "model": ErrorResponse,
            "description": "DeepSeek rate limit reached",
        },
        status.HTTP_502_BAD_GATEWAY: {
            "model": ErrorResponse,
            "description": "DeepSeek rejected the request or failed",
        },
        status.HTTP_503_SERVICE_UNAVAILABLE: {
            "model": ErrorResponse,
            "description": "DeepSeek API key is not configured",
        },
        status.HTTP_504_GATEWAY_TIMEOUT: {
            "model": ErrorResponse,
            "description": "DeepSeek did not respond in time",
        },
    },
)
async def chat_completion(
    payload: ChatRequest, client: AIClient, _user: CurrentUser
) -> ChatResponse:
    return await ai_service.complete_chat(client, payload)
