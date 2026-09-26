from typing import Annotated

from fastapi import Depends, Request

from src.ai.client import DeepSeekClient


def get_ai_client(request: Request) -> DeepSeekClient:
    return request.app.state.ai_client


AIClient = Annotated[DeepSeekClient, Depends(get_ai_client)]
