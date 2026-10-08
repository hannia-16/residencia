from typing import Any, ClassVar, Generic, TypeVar

from sqlalchemy import delete as sa_delete
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models import Base

ModelT = TypeVar("ModelT", bound=Base)


class Repository(Generic[ModelT]):
    model: ClassVar[type[Base]]

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    @classmethod
    def columns(cls) -> tuple[Any, ...]:
        return cls.model.__table__.columns

    async def get(self, pk: Any) -> ModelT | None:
        return await self.session.get(self.model, pk)

    async def one_or_none(self, **filters: Any) -> ModelT | None:
        statement = select(self.model).filter_by(**filters).limit(1)
        return await self.session.scalar(statement)

    async def exists(self, **filters: Any) -> bool:
        primary_key = self.model.__mapper__.primary_key[0]
        statement = select(primary_key).filter_by(**filters).limit(1)
        return await self.session.scalar(statement) is not None

    async def list(
        self,
        *,
        filters: dict[str, Any] | None = None,
        order_by: tuple[Any, ...] = (),
        limit: int | None = None,
        offset: int | None = None,
    ) -> list[ModelT]:
        statement = select(self.model)
        if filters:
            statement = statement.filter_by(**filters)
        if order_by:
            statement = statement.order_by(*order_by)
        if offset:
            statement = statement.offset(offset)
        if limit:
            statement = statement.limit(limit)
        result = await self.session.execute(statement)
        return list(result.scalars().unique().all())

    async def count(self, *, filters: dict[str, Any] | None = None) -> int:
        statement = select(func.count()).select_from(self.model)
        if filters:
            statement = statement.filter_by(**filters)
        return int(await self.session.scalar(statement) or 0)

    async def create(self, **values: Any) -> ModelT:
        entity = self.model(**values)
        self.session.add(entity)
        await self.session.flush()
        await self.session.refresh(entity)
        return entity

    async def update(self, entity: ModelT, **values: Any) -> ModelT:
        for field, value in values.items():
            setattr(entity, field, value)
        self.session.add(entity)
        await self.session.flush()
        return entity

    async def delete(self, entity: ModelT) -> None:
        await self.session.delete(entity)
        await self.session.flush()

    async def delete_where(self, **filters: Any) -> int:
        result = await self.session.execute(
            sa_delete(self.model).filter_by(**filters)  # type: ignore[arg-type]
        )
        await self.session.flush()
        return int(result.rowcount or 0)
