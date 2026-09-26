from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
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

DESCRIPTION = (
    "FastAPI + SQLite + DeepSeek scaffold. See AGENTS.md for the conventions this "
    "project follows."
)


def register_datasources() -> None:
    from src.auth.repository import UserRepository

    if "user" not in registry:
        registry.register("user", UserRepository)


register_datasources()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    app.state.ai_client = DeepSeekClient(config=ai_settings)
    try:
        yield
    finally:
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
