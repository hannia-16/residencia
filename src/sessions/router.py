from typing import Annotated

from fastapi import APIRouter, File, Query, UploadFile, status

from src.ai.dependencies import AIClient
from src.auth.dependencies import CurrentUser
from src.datasources.dependencies import DbSession
from src.exceptions import ErrorResponse
from src.sessions import service as sessions_service
from src.sessions.constants import (
    AUDIO_CONTENT_TYPES,
    MAX_AUDIO_BYTES,
    EstadoSesion,
)
from src.sessions.dependencies import OwnedSession
from src.sessions.exceptions import (
    AudioTooLarge,
    EmptyTranscription,
    UnsupportedAudioFormat,
)
from src.sessions.schemas import (
    CatalogoRead,
    EvaluacionCreate,
    InformeRead,
    SesionCreate,
    SesionListado,
    SesionRead,
    SesionResumen,
    TurnoCreate,
    TurnoRespuesta,
)
from src.speech.dependencies import SpeechClient

catalog_router = APIRouter(tags=["scenarios"])
router = APIRouter(prefix="/sessions", tags=["sessions"])

AUTHENTICATION_ERRORS = {
    status.HTTP_401_UNAUTHORIZED: {
        "model": ErrorResponse,
        "description": "Missing or invalid access token",
    },
    status.HTTP_404_NOT_FOUND: {
        "model": ErrorResponse,
        "description": "Session not found or not owned by the user",
    },
}

AI_ERRORS = {
    status.HTTP_429_TOO_MANY_REQUESTS: {
        "model": ErrorResponse,
        "description": "AI provider rate limit reached",
    },
    status.HTTP_502_BAD_GATEWAY: {
        "model": ErrorResponse,
        "description": "AI provider failed or returned an invalid turn",
    },
    status.HTTP_504_GATEWAY_TIMEOUT: {
        "model": ErrorResponse,
        "description": "AI provider did not respond in time",
    },
}


@catalog_router.get(
    "/scenarios",
    response_model=CatalogoRead,
    summary="List the available scenarios and CEFR levels",
    description=(
        "Returns the preloaded scenarios and levels the frontend needs to start a "
        "practice session."
    ),
    responses=AUTHENTICATION_ERRORS,
)
async def listar_catalogo(_user: CurrentUser) -> CatalogoRead:
    return sessions_service.catalogo()


@router.post(
    "",
    response_model=SesionRead,
    status_code=status.HTTP_201_CREATED,
    summary="Start a practice session",
    description=(
        "Creates an active session for the authenticated student and generates the "
        "agent's opening message for the chosen scenario and level."
    ),
    responses={**AUTHENTICATION_ERRORS, **AI_ERRORS},
)
async def iniciar_sesion(
    payload: SesionCreate,
    user: CurrentUser,
    session: DbSession,
    ai: AIClient,
) -> SesionRead:
    sesion = await sessions_service.iniciar_sesion(session, ai, user, payload)
    return SesionRead.model_validate(sesion)


@router.get(
    "",
    response_model=list[SesionListado],
    summary="List the student's sessions",
    description="Returns every session of the authenticated student, newest first.",
    responses=AUTHENTICATION_ERRORS,
)
async def listar_sesiones(
    user: CurrentUser,
    session: DbSession,
    estado: Annotated[EstadoSesion | None, Query()] = None,
) -> list[SesionListado]:
    return await sessions_service.listar_sesiones(session, user, estado=estado)


@router.get(
    "/{id_sesion}",
    response_model=SesionRead,
    summary="Get a session with its conversation history",
    description=(
        "Used to render or resume the chat window. Sessions expire after 30 days."
    ),
    responses={
        **AUTHENTICATION_ERRORS,
        status.HTTP_410_GONE: {
            "model": ErrorResponse,
            "description": "Session older than 30 days and no longer available",
        },
    },
)
async def obtener_sesion(sesion: OwnedSession) -> SesionRead:
    return SesionRead.model_validate(await sessions_service.obtener_sesion(sesion))


@router.post(
    "/{id_sesion}/turnos",
    response_model=TurnoRespuesta,
    summary="Send a text turn",
    description=(
        "Runs a full conversational turn from text: the agent reply is stored in "
        "the session history. Corrections are stored but only revealed when the "
        "session closes."
    ),
    responses={
        **AUTHENTICATION_ERRORS,
        **AI_ERRORS,
        status.HTTP_409_CONFLICT: {
            "model": ErrorResponse,
            "description": "Session is paused or already closed",
        },
        status.HTTP_410_GONE: {
            "model": ErrorResponse,
            "description": "Session older than 30 days and no longer available",
        },
    },
)
async def registrar_turno(
    sesion: OwnedSession,
    payload: TurnoCreate,
    session: DbSession,
    ai: AIClient,
) -> TurnoRespuesta:
    return await sessions_service.registrar_turno(session, ai, sesion, payload.texto)


@router.post(
    "/{id_sesion}/turnos/audio",
    response_model=TurnoRespuesta,
    summary="Send an audio turn",
    description=(
        "Transcribes the uploaded audio in memory (Groq Whisper), then runs the same "
        "conversational pipeline as the text turn endpoint."
    ),
    responses={
        **AUTHENTICATION_ERRORS,
        **AI_ERRORS,
        status.HTTP_409_CONFLICT: {
            "model": ErrorResponse,
            "description": "Session is paused or already closed",
        },
        status.HTTP_410_GONE: {
            "model": ErrorResponse,
            "description": "Session older than 30 days and no longer available",
        },
        status.HTTP_413_CONTENT_TOO_LARGE: {
            "model": ErrorResponse,
            "description": "Audio exceeds the maximum allowed size",
        },
        status.HTTP_415_UNSUPPORTED_MEDIA_TYPE: {
            "model": ErrorResponse,
            "description": "Audio format is not supported",
        },
        status.HTTP_422_UNPROCESSABLE_CONTENT: {
            "model": ErrorResponse,
            "description": "No speech detected in the audio",
        },
        status.HTTP_503_SERVICE_UNAVAILABLE: {
            "model": ErrorResponse,
            "description": "Speech-to-text service is not configured",
        },
    },
)
async def registrar_turno_audio(
    sesion: OwnedSession,
    session: DbSession,
    ai: AIClient,
    speech: SpeechClient,
    archivo: Annotated[UploadFile, File(description="Recorded audio of the student")],
) -> TurnoRespuesta:
    content_type = (archivo.content_type or "").split(";")[0].strip().lower()
    if content_type not in AUDIO_CONTENT_TYPES:
        raise UnsupportedAudioFormat()
    data = await archivo.read(MAX_AUDIO_BYTES + 1)
    if len(data) > MAX_AUDIO_BYTES:
        raise AudioTooLarge()
    texto = await speech.transcribe(
        data,
        filename=archivo.filename or "audio.webm",
        content_type=content_type,
    )
    if not texto.strip():
        raise EmptyTranscription()
    return await sessions_service.registrar_turno(session, ai, sesion, texto.strip())


@router.post(
    "/{id_sesion}/pausar",
    response_model=SesionResumen,
    summary="Pause a session",
    responses={
        **AUTHENTICATION_ERRORS,
        status.HTTP_409_CONFLICT: {
            "model": ErrorResponse,
            "description": "Session is not active",
        },
        status.HTTP_410_GONE: {
            "model": ErrorResponse,
            "description": "Session older than 30 days and no longer available",
        },
    },
)
async def pausar_sesion(sesion: OwnedSession, session: DbSession) -> SesionResumen:
    return await sessions_service.pausar(session, sesion)


@router.post(
    "/{id_sesion}/reanudar",
    response_model=SesionResumen,
    summary="Resume a paused session",
    description="A session can only be resumed within 30 days of its start.",
    responses={
        **AUTHENTICATION_ERRORS,
        status.HTTP_409_CONFLICT: {
            "model": ErrorResponse,
            "description": "Session is not paused or was already closed",
        },
        status.HTTP_410_GONE: {
            "model": ErrorResponse,
            "description": "Session older than 30 days and no longer available",
        },
    },
)
async def reanudar_sesion(sesion: OwnedSession, session: DbSession) -> SesionResumen:
    return await sessions_service.reanudar(session, sesion)


@router.post(
    "/{id_sesion}/cerrar",
    response_model=InformeRead,
    summary="Close a session and generate the feedback report",
    description=(
        "This is the only point where the feedback report is generated. It analyzes "
        "the full conversation, marks the session as concluded and updates metrics."
    ),
    responses={
        **AUTHENTICATION_ERRORS,
        **AI_ERRORS,
        status.HTTP_409_CONFLICT: {
            "model": ErrorResponse,
            "description": "Session was already closed",
        },
        status.HTTP_410_GONE: {
            "model": ErrorResponse,
            "description": "Session older than 30 days and no longer available",
        },
    },
)
async def cerrar_sesion(
    sesion: OwnedSession, session: DbSession, ai: AIClient
) -> InformeRead:
    return await sessions_service.cerrar(session, ai, sesion)


@router.get(
    "/{id_sesion}/retroalimentacion",
    response_model=InformeRead,
    summary="Get the feedback report",
    description="Available only after the session has been closed.",
    responses={
        **AUTHENTICATION_ERRORS,
        status.HTTP_404_NOT_FOUND: {
            "model": ErrorResponse,
            "description": "Session not found or feedback not generated yet",
        },
        status.HTTP_410_GONE: {
            "model": ErrorResponse,
            "description": "Session older than 30 days and no longer available",
        },
    },
)
async def obtener_retroalimentacion(
    sesion: OwnedSession, session: DbSession
) -> InformeRead:
    return await sessions_service.obtener_informe(session, sesion)


@router.post(
    "/{id_sesion}/evaluacion",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Rate the system (optional)",
    description=(
        "Stores the student's optional evaluation of the system. It is kept separate "
        "from the linguistic feedback."
    ),
    responses={
        **AUTHENTICATION_ERRORS,
        status.HTTP_409_CONFLICT: {
            "model": ErrorResponse,
            "description": "Session not closed yet or already evaluated",
        },
    },
)
async def evaluar_sistema(
    sesion: OwnedSession, payload: EvaluacionCreate, session: DbSession
) -> None:
    await sessions_service.evaluar(session, sesion, payload)
