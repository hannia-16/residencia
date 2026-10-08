from enum import StrEnum
from typing import Final


class Escenario(StrEnum):
    RESTAURANTE = "restaurante"
    AEROPUERTO = "aeropuerto"
    HOTEL = "hotel"
    ENTREVISTA_TRABAJO = "entrevista_trabajo"
    CONSULTORIO_MEDICO = "consultorio_medico"
    TIENDA = "tienda"


class NivelMCER(StrEnum):
    A1 = "A1"
    A2 = "A2"
    B1 = "B1"
    B2 = "B2"
    C1 = "C1"


class EstadoSesion(StrEnum):
    ACTIVA = "activa"
    PAUSADA = "pausada"
    CONCLUIDA = "concluida"


class RolTurno(StrEnum):
    AGENTE = "agente"
    ESTUDIANTE = "estudiante"


class TipoError(StrEnum):
    GRAMATICA = "gramatica"
    VOCABULARIO = "vocabulario"
    ORDEN = "orden"
    OTRO = "otro"


ESCENARIO_CATALOGO: dict[Escenario, tuple[str, str]] = {
    Escenario.RESTAURANTE: (
        "En el restaurante",
        "Pedir comida y bebida, preguntar por el menú y resolver una queja sencilla.",
    ),
    Escenario.AEROPUERTO: (
        "En el aeropuerto",
        "Check-in, control de seguridad y preguntas sobre un vuelo.",
    ),
    Escenario.HOTEL: (
        "En el hotel",
        "Reservar una habitación, pedir servicios y resolver dudas de la estancia.",
    ),
    Escenario.ENTREVISTA_TRABAJO: (
        "Entrevista de trabajo",
        "Responder preguntas básicas de una entrevista laboral.",
    ),
    Escenario.CONSULTORIO_MEDICO: (
        "En el consultorio médico",
        "Describir síntomas y seguir las indicaciones del personal médico.",
    ),
    Escenario.TIENDA: (
        "De compras",
        "Preguntar precios, tallas y métodos de pago en una tienda.",
    ),
}

RESUME_WINDOW_DAYS: Final = 30
MAX_TEXTO_TURNO: Final = 2000
MAX_MENSAJE_IA: Final = 1000
MAX_AUDIO_BYTES: Final = 10 * 1024 * 1024
AUDIO_CONTENT_TYPES: Final = frozenset(
    {
        "audio/webm",
        "audio/ogg",
        "audio/wav",
        "audio/x-wav",
        "audio/mpeg",
        "audio/mp4",
        "audio/m4a",
        "audio/x-m4a",
    }
)
AVISO_ORIENTATIVO: Final = (
    "Este reporte es orientativo y no constituye una certificación oficial de "
    "nivel MCER."
)
