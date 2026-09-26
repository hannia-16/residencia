import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.models import User
from src.auth.repository import UserRepository
from src.datasources.registry import registry
from src.health.exceptions import DatabaseUnavailable
from src.main import app


def test_user_datasource_is_registered() -> None:
    assert "user" in registry
    assert registry.names() == ["user"]


def test_registry_rejects_duplicate_registration() -> None:
    with pytest.raises(ValueError, match="already registered"):
        registry.register("user", UserRepository)


def test_registry_reports_unknown_datasource() -> None:
    with pytest.raises(LookupError, match="Unknown datasource"):
        registry.factory("nope")


def test_registry_lookups_are_idempotent() -> None:
    from src.main import register_datasources

    register_datasources()
    register_datasources()

    assert registry.names() == ["user"]


async def test_repository_crud_round_trip(session: AsyncSession) -> None:
    users = UserRepository(session)

    created = await users.create(
        email="repo@example.com", username="repo", hashed_password="x"
    )
    await session.commit()

    assert await users.get(created.id) is not None
    assert await users.get_by_email("repo@example.com") is not None
    assert await users.get_by_username("repo") is not None
    assert await users.exists(email="repo@example.com") is True
    assert await users.exists(email="missing@example.com") is False
    assert await users.count() == 1

    await users.update(created, username="renamed")
    await session.commit()
    assert (await users.get(created.id)).username == "renamed"

    await users.delete(created)
    await session.commit()
    assert await users.get(created.id) is None
    assert await users.count() == 0


async def test_repository_one_or_none_returns_none(session: AsyncSession) -> None:
    assert await UserRepository(session).one_or_none(email="ghost@x.com") is None


async def test_repository_delete_where(session: AsyncSession) -> None:
    users = UserRepository(session)
    for index in range(3):
        await users.create(
            email=f"bulk{index}@example.com",
            username=f"bulk{index}",
            hashed_password="x",
        )
    await session.commit()

    assert await users.count() == 3
    removed = await users.delete_where(username="bulk1")
    await session.commit()

    assert removed == 1
    assert await users.count() == 2


async def test_database_unavailable_is_a_503() -> None:
    error = DatabaseUnavailable()

    assert error.status_code == 503
    assert error.code == "database_unavailable"


def test_user_table_name_is_singular() -> None:
    assert User.__tablename__ == "user"
    assert app.title == "cosa-backend"
