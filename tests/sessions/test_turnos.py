from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.sessions.repository import RetroalimentacionRepository
from tests.support import (
    FakeLLM,
    FakeSpeechToText,
    correccion,
    informe_ia,
    start_session,
    turn_ia,
    use_speech,
)


async def test_text_turn_appends_history(authed: AsyncClient) -> None:
    fake = FakeLLM(turn_ia("Opening"), turn_ia("Sure, coming right up!"))
    _, body = await start_session(authed, fake)
    id_sesion = body["id_sesion"]

    response = await authed.post(
        f"/sessions/{id_sesion}/turnos", json={"texto": "I want a pizza"}
    )

    assert response.status_code == 200, response.text
    turno = response.json()
    assert turno["texto_estudiante"] == "I want a pizza"
    assert turno["estado"] == "activa"
    assert turno["mensaje"]["rol"] == "agente"
    assert turno["mensaje"]["contenido"] == "Sure, coming right up!"
    assert "errores" not in turno

    detail = await authed.get(f"/sessions/{id_sesion}")
    historial = detail.json()["historial"]
    assert [item["rol"] for item in historial] == ["agente", "estudiante", "agente"]
    assert historial[1]["contenido"] == "I want a pizza"

    enviado = fake.requests[-1]
    assert enviado["messages"][-1] == {"role": "user", "content": "I want a pizza"}
    assert enviado["response_format"] == {"type": "json_object"}


async def test_turn_with_corrections_persists_but_hides_them(
    authed: AsyncClient, session: AsyncSession
) -> None:
    fake = FakeLLM(
        turn_ia("Opening"),
        turn_ia(
            "I see!",
            errores=[
                correccion(),
                correccion(
                    tipo="vocabulario", original="big", correccion_texto="large"
                ),
            ],
        ),
    )
    _, body = await start_session(authed, fake)
    id_sesion = body["id_sesion"]

    response = await authed.post(
        f"/sessions/{id_sesion}/turnos", json={"texto": "I go yesterday to big hotel"}
    )

    assert response.status_code == 200
    assert "errores" not in response.json()

    repositorio = RetroalimentacionRepository(session)
    assert await repositorio.count() == 2

    informe = await authed.get(f"/sessions/{id_sesion}/retroalimentacion")
    assert informe.status_code == 404
    assert informe.json()["detail"]["code"] == "feedback_not_available"


async def test_turn_invalid_json_retries_then_fails(authed: AsyncClient) -> None:
    fake = FakeLLM(turn_ia("Opening"), "this is not json")
    _, body = await start_session(authed, fake)
    id_sesion = body["id_sesion"]

    response = await authed.post(
        f"/sessions/{id_sesion}/turnos", json={"texto": "Hello"}
    )

    assert response.status_code == 502
    assert response.json()["detail"]["code"] == "turn_failed"
    assert len(fake.requests) == 3

    detail = await authed.get(f"/sessions/{id_sesion}")
    assert len(detail.json()["historial"]) == 1


async def test_turn_on_closed_session_conflict(authed: AsyncClient) -> None:
    fake = FakeLLM(turn_ia("Opening"), turn_ia("Reply"), informe_ia())
    _, body = await start_session(authed, fake)
    id_sesion = body["id_sesion"]

    await authed.post(f"/sessions/{id_sesion}/turnos", json={"texto": "Hello"})
    cierre = await authed.post(f"/sessions/{id_sesion}/cerrar")
    assert cierre.status_code == 200

    response = await authed.post(
        f"/sessions/{id_sesion}/turnos", json={"texto": "One more?"}
    )

    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "session_concluded"


async def test_audio_turn_uses_transcription(authed: AsyncClient) -> None:
    fake = FakeLLM(turn_ia("Opening"), turn_ia("A coffee it is."))
    speech = FakeSpeechToText("I would like a coffee, please.")
    use_speech(speech)
    _, body = await start_session(authed, fake)
    id_sesion = body["id_sesion"]

    response = await authed.post(
        f"/sessions/{id_sesion}/turnos/audio",
        files={"archivo": ("turno.webm", b"fake-bytes", "audio/webm")},
    )

    assert response.status_code == 200, response.text
    turno = response.json()
    assert turno["texto_estudiante"] == "I would like a coffee, please."
    assert turno["mensaje"]["contenido"] == "A coffee it is."
    assert speech.calls == [(b"fake-bytes", "turno.webm", "audio/webm")]

    detail = await authed.get(f"/sessions/{id_sesion}")
    assert detail.json()["historial"][1]["rol"] == "estudiante"


async def test_audio_rejects_unknown_format(authed: AsyncClient) -> None:
    fake = FakeLLM(turn_ia())
    speech = FakeSpeechToText()
    use_speech(speech)
    _, body = await start_session(authed, fake)

    response = await authed.post(
        f"/sessions/{body['id_sesion']}/turnos/audio",
        files={"archivo": ("notes.txt", b"hello", "text/plain")},
    )

    assert response.status_code == 415
    assert response.json()["detail"]["code"] == "unsupported_audio_format"
    assert speech.calls == []


async def test_audio_rejects_oversized_file(authed: AsyncClient, monkeypatch) -> None:
    monkeypatch.setattr("src.sessions.router.MAX_AUDIO_BYTES", 10)
    fake = FakeLLM(turn_ia())
    speech = FakeSpeechToText()
    use_speech(speech)
    _, body = await start_session(authed, fake)

    response = await authed.post(
        f"/sessions/{body['id_sesion']}/turnos/audio",
        files={"archivo": ("turno.webm", b"x" * 11, "audio/webm")},
    )

    assert response.status_code == 413
    assert response.json()["detail"]["code"] == "audio_too_large"
    assert speech.calls == []


async def test_audio_rejects_empty_transcription(authed: AsyncClient) -> None:
    fake = FakeLLM(turn_ia())
    speech = FakeSpeechToText("   ")
    use_speech(speech)
    _, body = await start_session(authed, fake)

    response = await authed.post(
        f"/sessions/{body['id_sesion']}/turnos/audio",
        files={"archivo": ("turno.webm", b"fake-bytes", "audio/webm")},
    )

    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "empty_transcription"
