import uuid
from datetime import datetime

from pydantic import Field

from src.models import CustomModel
from src.sessions.constants import (
    MAX_MENSAJE_IA,
    MAX_TEXTO_TURNO,
    Escenario,
    EstadoSesion,
    NivelMCER,
    RolTurno,
    TipoError,
)


class EscenarioRead(CustomModel):
    clave: Escenario
    nombre: str
    descripcion: str


class CatalogoRead(CustomModel):
    escenarios: list[EscenarioRead]
    niveles: list[NivelMCER]


class TurnoHistorial(CustomModel):
    rol: RolTurno
    contenido: str
    fecha: datetime


class SesionCreate(CustomModel):
    escenario: Escenario
    nivel: NivelMCER


class SesionResumen(CustomModel):
    model_config = {"from_attributes": True}

    id_sesion: uuid.UUID
    escenario: Escenario
    nivel: NivelMCER
    estado: EstadoSesion
    fecha_inicio: datetime
    fecha_fin: datetime | None = None


class SesionListado(SesionResumen):
    puede_reanudarse: bool


class SesionRead(SesionResumen):
    historial: list[TurnoHistorial] = Field(default_factory=list)
    evaluacion_sistema: "EvaluacionSistema | None" = None


class CorreccionIA(CustomModel):
    tipo: TipoError
    original: str = Field(min_length=1, max_length=MAX_TEXTO_TURNO)
    correccion: str = Field(min_length=1, max_length=MAX_TEXTO_TURNO)
    explicacion: str = Field(min_length=1, max_length=MAX_TEXTO_TURNO)


class TurnoIA(CustomModel):
    mensaje: str = Field(min_length=1, max_length=MAX_MENSAJE_IA)
    errores: list[CorreccionIA] = Field(default_factory=list)


class InformeIA(CustomModel):
    resumen: str = Field(min_length=1, max_length=MAX_TEXTO_TURNO)
    gramatica: list[str] = Field(default_factory=list)
    vocabulario: list[str] = Field(default_factory=list)
    areas_mejora: list[str] = Field(default_factory=list)
    fortalezas: list[str] = Field(default_factory=list)


class TurnoCreate(CustomModel):
    texto: str = Field(min_length=1, max_length=MAX_TEXTO_TURNO)


class TurnoRespuesta(CustomModel):
    id_sesion: uuid.UUID
    estado: EstadoSesion
    texto_estudiante: str
    mensaje: TurnoHistorial


class RetroalimentacionRead(CustomModel):
    model_config = {"from_attributes": True}

    id_retroalimentacion: uuid.UUID
    entrada_usuario: str
    correccion_ia: CorreccionIA


class InformeRead(CustomModel):
    id_sesion: uuid.UUID
    escenario: Escenario
    nivel: NivelMCER
    generado_en: datetime
    resumen: str
    gramatica: list[str]
    vocabulario: list[str]
    areas_mejora: list[str]
    fortalezas: list[str]
    errores: list[CorreccionIA]
    retroalimentaciones: list[RetroalimentacionRead]
    aviso: str


class EvaluacionCreate(CustomModel):
    calificacion: int = Field(ge=1, le=5)
    comentario: str | None = Field(default=None, max_length=1000)


class EvaluacionSistema(CustomModel):
    calificacion: int
    comentario: str | None = None
    fecha: datetime


SesionRead.model_rebuild()
