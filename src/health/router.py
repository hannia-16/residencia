from fastapi import APIRouter, status
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from src.config import settings
from src.datasources.dependencies import DbSession
from src.exceptions import ErrorResponse
from src.health.exceptions import DatabaseUnavailable
from src.health.schemas import HealthStatus, ReadinessStatus

router = APIRouter(tags=["health"])


@router.get(
    "/health",
    response_model=HealthStatus,
    summary="Liveness probe",
    description="Returns 200 as long as the process is able to serve traffic.",
)
async def health() -> HealthStatus:
    return HealthStatus(status="ok", environment=settings.ENVIRONMENT)


@router.get(
    "/ready",
    response_model=ReadinessStatus,
    summary="Readiness probe",
    description="Verifies the database answers before reporting the service ready.",
    responses={
        status.HTTP_503_SERVICE_UNAVAILABLE: {
            "model": ErrorResponse,
            "description": "The database is not reachable",
        }
    },
)
async def ready(session: DbSession) -> ReadinessStatus:
    try:
        await session.execute(text("SELECT 1"))
    except SQLAlchemyError as exc:
        raise DatabaseUnavailable() from exc
    return ReadinessStatus(status="ok", database="ok")
