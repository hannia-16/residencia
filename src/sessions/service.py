from datetime import UTC, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from src.ai.client import DeepSeekClient
from src.ai.schemas import ChatMessage, MessageRole
from src.auth.models import User
from src.sessions import prompts
from src.sessions.constants import (
    AVISO_ORIENTATIVO,
    ESCENARIO_CATALOGO,
    RESUME_WINDOW_DAYS,
    Escenario,
    EstadoSesion,
    NivelMCER,
    RolTurno,
)
from src.sessions.exceptions import (
    EvaluationAlreadySubmitted,
    EvaluationNotAllowed,
    FeedbackNotAvailable,
    SessionConcluded,
    SessionNotActive,
    SessionNotPaused,
    SessionUnavailable,
)
from src.sessions.llm import complete_structured
from src.sessions.models import Retroalimentacion, Sesion
from src.sessions.repository import (
    MetricaRepository,
    RetroalimentacionRepository,
    SesionRepository,
)
from src.sessions.schemas import (
    CatalogoRead,
    CorreccionIA,
    EscenarioRead,
    EvaluacionCreate,
    EvaluacionSistema,
    InformeIA,
    InformeRead,
    RetroalimentacionRead,
    SesionCreate,
    SesionListado,
    SesionResumen,
    TurnoHistorial,
    TurnoIA,
    TurnoRespuesta,
)


def _now() -> datetime:
    return datetime.now(UTC)


def _ensure_utc(value: datetime) -> datetime:
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value


def _puede_reanudarse(sesion: Sesion, ahora: datetime | None = None) -> bool:
    if sesion.estado == EstadoSesion.CONCLUIDA.value:
        return False
    momento = ahora or _now()
    return momento - _ensure_utc(sesion.fecha_inicio) < timedelta(
        days=RESUME_WINDOW_DAYS
    )


def _ensure_disponible(sesion: Sesion) -> None:
    if sesion.estado != EstadoSesion.CONCLUIDA.value and not _puede_reanudarse(sesion):
        raise SessionUnavailable()


def _ensure_mutable(sesion: Sesion) -> None:
    if sesion.estado == EstadoSesion.CONCLUIDA.value:
        raise SessionConcluded()
    _ensure_disponible(sesion)


def _turno(rol: RolTurno, contenido: str) -> dict:
    return {"rol": rol.value, "contenido": contenido, "fecha": _now().isoformat()}


def _mensajes(system: str, historial: list[dict]) -> list[ChatMessage]:
    mensajes = [ChatMessage(role=MessageRole.SYSTEM, content=system)]
    for turno in historial:
        rol = (
            MessageRole.ASSISTANT
            if turno.get("rol") == RolTurno.AGENTE.value
            else MessageRole.USER
        )
        mensajes.append(ChatMessage(role=rol, content=turno["contenido"]))
    return mensajes


def _correcciones_de(turno_ia: TurnoIA) -> list[dict]:
    return [correccion.model_dump(mode="json") for correccion in turno_ia.errores]


async def _persistir_correcciones(
    session: AsyncSession, sesion: Sesion, texto: str, turno_ia: TurnoIA
) -> None:
    if not turno_ia.errores:
        return
    repositorio = RetroalimentacionRepository(session)
    for correccion in turno_ia.errores:
        await repositorio.create(
            id_sesion=sesion.id_sesion,
            entrada_usuario=texto,
            correccion_ia=correccion.model_dump(mode="json"),
        )


def catalogo() -> CatalogoRead:
    return CatalogoRead(
        escenarios=[
            EscenarioRead(clave=clave, nombre=nombre, descripcion=descripcion)
            for clave, (nombre, descripcion) in ESCENARIO_CATALOGO.items()
        ],
        niveles=list(NivelMCER),
    )


async def iniciar_sesion(
    session: AsyncSession,
    ai: DeepSeekClient,
    user: User,
    payload: SesionCreate,
) -> Sesion:
    mensajes = [
        ChatMessage(
            role=MessageRole.SYSTEM,
            content=prompts.build_system_prompt(payload.escenario, payload.nivel),
        ),
        ChatMessage(role=MessageRole.USER, content=prompts.build_opening_prompt()),
    ]
    turno_ia = await complete_structured(ai, mensajes, TurnoIA)
    sesion = await SesionRepository(session).create(
        id_usuario=user.id,
        escenario=payload.escenario.value,
        nivel=payload.nivel.value,
        estado=EstadoSesion.ACTIVA.value,
        historial=[_turno(RolTurno.AGENTE, turno_ia.mensaje)],
    )
    await session.commit()
    return sesion


async def listar_sesiones(
    session: AsyncSession, user: User, *, estado: EstadoSesion | None = None
) -> list[SesionListado]:
    sesiones = await SesionRepository(session).list_by_user(
        user.id, estado=estado.value if estado is not None else None
    )
    return [
        SesionListado(
            id_sesion=sesion.id_sesion,
            escenario=sesion.escenario,
            nivel=sesion.nivel,
            estado=sesion.estado,
            fecha_inicio=sesion.fecha_inicio,
            fecha_fin=sesion.fecha_fin,
            puede_reanudarse=_puede_reanudarse(sesion),
        )
        for sesion in sesiones
    ]


async def obtener_sesion(sesion: Sesion) -> Sesion:
    _ensure_disponible(sesion)
    return sesion


async def registrar_turno(
    session: AsyncSession, ai: DeepSeekClient, sesion: Sesion, texto: str
) -> TurnoRespuesta:
    _ensure_mutable(sesion)
    if sesion.estado != EstadoSesion.ACTIVA.value:
        raise SessionNotActive()
    escenario = Escenario(sesion.escenario)
    nivel = NivelMCER(sesion.nivel)
    mensajes = _mensajes(
        prompts.build_system_prompt(escenario, nivel), sesion.historial
    )
    mensajes.append(ChatMessage(role=MessageRole.USER, content=texto))
    turno_ia = await complete_structured(ai, mensajes, TurnoIA)
    turno_estudiante = _turno(RolTurno.ESTUDIANTE, texto)
    turno_agente = _turno(RolTurno.AGENTE, turno_ia.mensaje)
    sesion.historial = [*sesion.historial, turno_estudiante, turno_agente]
    await _persistir_correcciones(session, sesion, texto, turno_ia)
    await session.commit()
    return TurnoRespuesta(
        id_sesion=sesion.id_sesion,
        estado=sesion.estado,
        texto_estudiante=texto,
        mensaje=TurnoHistorial.model_validate(turno_agente),
    )


async def pausar(session: AsyncSession, sesion: Sesion) -> SesionResumen:
    _ensure_mutable(sesion)
    if sesion.estado != EstadoSesion.ACTIVA.value:
        raise SessionNotActive()
    sesion.estado = EstadoSesion.PAUSADA.value
    await session.commit()
    return SesionResumen.model_validate(sesion)


async def reanudar(session: AsyncSession, sesion: Sesion) -> SesionResumen:
    _ensure_mutable(sesion)
    if sesion.estado != EstadoSesion.PAUSADA.value:
        raise SessionNotPaused()
    sesion.estado = EstadoSesion.ACTIVA.value
    await session.commit()
    return SesionResumen.model_validate(sesion)


def _armar_informe(
    sesion: Sesion,
    datos: dict,
    correcciones: list[Retroalimentacion],
    generado_en: datetime | None,
) -> InformeRead:
    return InformeRead(
        id_sesion=sesion.id_sesion,
        escenario=sesion.escenario,
        nivel=sesion.nivel,
        generado_en=generado_en or sesion.fecha_fin,
        resumen=datos.get("resumen", ""),
        gramatica=list(datos.get("gramatica") or []),
        vocabulario=list(datos.get("vocabulario") or []),
        areas_mejora=list(datos.get("areas_mejora") or []),
        fortalezas=list(datos.get("fortalezas") or []),
        errores=[CorreccionIA.model_validate(c.correccion_ia) for c in correcciones],
        retroalimentaciones=[
            RetroalimentacionRead.model_validate(c) for c in correcciones
        ],
        aviso=str(datos.get("aviso") or AVISO_ORIENTATIVO),
    )


async def cerrar(
    session: AsyncSession, ai: DeepSeekClient, sesion: Sesion
) -> InformeRead:
    _ensure_mutable(sesion)
    repositorio = RetroalimentacionRepository(session)
    correcciones = await repositorio.list_by_sesion(sesion.id_sesion)
    mensajes = [
        ChatMessage(
            role=MessageRole.SYSTEM,
            content=prompts.build_report_system_prompt(
                Escenario(sesion.escenario), NivelMCER(sesion.nivel)
            ),
        ),
        ChatMessage(
            role=MessageRole.USER,
            content=prompts.build_report_prompt(
                sesion.historial, [c.correccion_ia for c in correcciones]
            ),
        ),
    ]
    informe = await complete_structured(ai, mensajes, InformeIA)
    ahora = _now()
    datos = informe.model_dump(mode="json")
    datos["generado_en"] = ahora.isoformat()
    datos["aviso"] = AVISO_ORIENTATIVO
    sesion.estado = EstadoSesion.CONCLUIDA.value
    sesion.fecha_fin = ahora
    sesion.resumen_desempeno = datos
    conteo: dict[str, int] = {}
    for correccion in correcciones:
        tipo = str(correccion.correccion_ia.get("tipo", "otro"))
        conteo[tipo] = conteo.get(tipo, 0) + 1
    await MetricaRepository(session).create(
        id_usuario=sesion.id_usuario,
        escenario=sesion.escenario,
        nivel=sesion.nivel,
        fecha_inicio=sesion.fecha_inicio,
        duracion=int((ahora - _ensure_utc(sesion.fecha_inicio)).total_seconds()),
        errores=conteo,
        resumen_ia=informe.resumen,
    )
    await session.commit()
    return _armar_informe(sesion, datos, correcciones, ahora)


async def obtener_informe(session: AsyncSession, sesion: Sesion) -> InformeRead:
    _ensure_disponible(sesion)
    if sesion.estado != EstadoSesion.CONCLUIDA.value or not sesion.resumen_desempeno:
        raise FeedbackNotAvailable()
    correcciones = await RetroalimentacionRepository(session).list_by_sesion(
        sesion.id_sesion
    )
    return _armar_informe(
        sesion, sesion.resumen_desempeno, correcciones, sesion.fecha_fin
    )


async def evaluar(
    session: AsyncSession, sesion: Sesion, payload: EvaluacionCreate
) -> None:
    if sesion.estado != EstadoSesion.CONCLUIDA.value:
        raise EvaluationNotAllowed()
    if sesion.evaluacion_sistema:
        raise EvaluationAlreadySubmitted()
    evaluacion = EvaluacionSistema(
        calificacion=payload.calificacion,
        comentario=payload.comentario,
        fecha=_now(),
    )
    sesion.evaluacion_sistema = evaluacion.model_dump(mode="json")
    await session.commit()
