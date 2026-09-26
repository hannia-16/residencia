from collections.abc import AsyncIterator
from typing import Any

from sqlalchemy import event
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import StaticPool

from src.config import settings

SQLITE_PRAGMAS = (
    "PRAGMA foreign_keys=ON",
    "PRAGMA busy_timeout=5000",
    "PRAGMA journal_mode=WAL",
)


def _enable_sqlite_pragmas(engine: AsyncEngine) -> None:
    if engine.dialect.name != "sqlite":
        return

    @event.listens_for(engine.sync_engine, "connect")
    def _set_pragmas(dbapi_connection: Any, _record: Any) -> None:
        cursor = dbapi_connection.cursor()
        try:
            for pragma in SQLITE_PRAGMAS:
                cursor.execute(pragma)
        finally:
            cursor.close()


def build_engine(
    url: str | None = None,
    *,
    echo: bool | None = None,
    in_memory: bool = False,
) -> AsyncEngine:
    resolved_url = url or settings.DATABASE_URL
    resolved_echo = settings.SQL_ECHO if echo is None else echo
    kwargs: dict[str, Any] = {"echo": resolved_echo, "pool_pre_ping": True}
    if in_memory:
        kwargs["poolclass"] = StaticPool
    engine = create_async_engine(resolved_url, **kwargs)
    _enable_sqlite_pragmas(engine)
    return engine


def build_session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(engine, expire_on_commit=False)


engine = build_engine()
SessionFactory = build_session_factory(engine)


async def get_db() -> AsyncIterator[AsyncSession]:
    async with SessionFactory() as session:
        yield session


async def dispose_engine() -> None:
    await engine.dispose()
