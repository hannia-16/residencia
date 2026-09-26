from collections.abc import Callable

from sqlalchemy.ext.asyncio import AsyncSession

from src.datasources.base import Repository

RepositoryFactory = Callable[[AsyncSession], Repository]


class DatasourceRegistry:
    def __init__(self) -> None:
        self._factories: dict[str, RepositoryFactory] = {}

    def register(self, name: str, factory: RepositoryFactory) -> None:
        if name in self._factories:
            raise ValueError(f"Datasource {name!r} is already registered.")
        self._factories[name] = factory

    def factory(self, name: str) -> RepositoryFactory:
        try:
            return self._factories[name]
        except KeyError:
            known = ", ".join(self.names()) or "none"
            raise LookupError(
                f"Unknown datasource {name!r}. Registered: {known}."
            ) from None

    def repository(self, name: str, session: AsyncSession) -> Repository:
        return self.factory(name)(session)

    def names(self) -> list[str]:
        return sorted(self._factories)

    def __contains__(self, name: object) -> bool:
        return name in self._factories


registry = DatasourceRegistry()
