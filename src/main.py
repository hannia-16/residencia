from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from src import __version__
from src.ai import router as ai_router
from src.ai.client import DeepSeekClient
from src.ai.config import ai_settings
from src.auth import router as auth_router
from src.config import settings
from src.database import dispose_engine
from src.datasources.registry import registry
from src.exceptions import AppError, ErrorResponse
from src.health import router as health_router
from src.sessions import router as sessions_router
from src.speech.client import GroqSpeechToText
from src.speech.config import speech_settings

DESCRIPTION = (
    "Backend del simulador conversacional de inglés: autenticación, sesiones de "
    "práctica con IA, retroalimentación y métricas."
)


def register_datasources() -> None:
    from src.auth.repository import UserRepository
    from src.sessions.repository import (
        MetricaRepository,
        RetroalimentacionRepository,
        SesionRepository,
    )

    repositories = {
        "user": UserRepository,
        "sesion": SesionRepository,
        "retroalimentacion": RetroalimentacionRepository,
        "metrica": MetricaRepository,
    }
    for name, repository in repositories.items():
        if name not in registry:
            registry.register(name, repository)


register_datasources()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    app.state.ai_client = DeepSeekClient(config=ai_settings)
    app.state.speech_client = GroqSpeechToText(config=speech_settings)
    try:
        yield
    finally:
        await app.state.speech_client.aclose()
        await app.state.ai_client.aclose()
        await dispose_engine()


app_kwargs: dict[str, object] = {
    "title": "cosa-backend",
    "description": DESCRIPTION,
    "version": __version__,
    "lifespan": lifespan,
}
if not settings.show_docs:
    app_kwargs["openapi_url"] = None

app = FastAPI(**app_kwargs)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(AppError)
async def handle_app_error(_request: Request, exc: AppError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse.from_error(exc).model_dump(),
        headers=exc.headers,
    )


app.include_router(health_router.router)
app.include_router(auth_router.router)
app.include_router(ai_router.router)
app.include_router(sessions_router.catalog_router)
app.include_router(sessions_router.router)
