import uuid
from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from src.models import Base
from src.sessions.constants import EstadoSesion


class Sesion(Base):
    __tablename__ = "sesion"

    id_sesion: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    id_usuario: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("user.id", ondelete="CASCADE"), index=True
    )
    escenario: Mapped[str] = mapped_column(String(64))
    nivel: Mapped[str] = mapped_column(String(8))
    estado: Mapped[str] = mapped_column(
        String(16),
        default=EstadoSesion.ACTIVA.value,
        server_default=EstadoSesion.ACTIVA.value,
        index=True,
    )
    fecha_inicio: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    fecha_fin: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    historial: Mapped[list[dict]] = mapped_column(JSON, default=list)
    resumen_desempeno: Mapped[dict | None] = mapped_column(JSON)
    evaluacion_sistema: Mapped[dict | None] = mapped_column(JSON)


class Retroalimentacion(Base):
    __tablename__ = "retroalimentacion"

    id_retroalimentacion: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, default=uuid.uuid4
    )
    id_sesion: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("sesion.id_sesion", ondelete="CASCADE"), index=True
    )
    entrada_usuario: Mapped[str] = mapped_column(Text)
    correccion_ia: Mapped[dict] = mapped_column(JSON)


class Metrica(Base):
    __tablename__ = "metrica"

    id_metrica: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    id_usuario: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("user.id", ondelete="CASCADE"), index=True
    )
    escenario: Mapped[str] = mapped_column(String(64))
    nivel: Mapped[str] = mapped_column(String(8))
    fecha_inicio: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    duracion: Mapped[int] = mapped_column(Integer)
    errores: Mapped[dict] = mapped_column(JSON, default=dict)
    resumen_ia: Mapped[str] = mapped_column(Text)
