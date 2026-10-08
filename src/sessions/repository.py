import uuid

from src.datasources.base import Repository
from src.sessions.models import Metrica, Retroalimentacion, Sesion


class SesionRepository(Repository[Sesion]):
    model = Sesion

    async def get_by_id_for_user(
        self, id_sesion: uuid.UUID, id_usuario: uuid.UUID
    ) -> Sesion | None:
        return await self.one_or_none(id_sesion=id_sesion, id_usuario=id_usuario)

    async def list_by_user(
        self, id_usuario: uuid.UUID, *, estado: str | None = None
    ) -> list[Sesion]:
        filters: dict[str, object] = {"id_usuario": id_usuario}
        if estado is not None:
            filters["estado"] = estado
        return await self.list(filters=filters, order_by=(Sesion.fecha_inicio.desc(),))


class RetroalimentacionRepository(Repository[Retroalimentacion]):
    model = Retroalimentacion

    async def list_by_sesion(self, id_sesion: uuid.UUID) -> list[Retroalimentacion]:
        return await self.list(filters={"id_sesion": id_sesion})


class MetricaRepository(Repository[Metrica]):
    model = Metrica

    async def list_by_user(self, id_usuario: uuid.UUID) -> list[Metrica]:
        return await self.list(
            filters={"id_usuario": id_usuario},
            order_by=(Metrica.fecha_inicio.desc(),),
        )
