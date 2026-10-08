import uuid
from datetime import UTC, datetime, timedelta

from httpx import AsyncClient
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from src.sessions.models import Sesion
from tests.factories import unique_signup
from tests.helpers import auth_headers
from tests.support import FakeLLM, informe_ia, start_session, turn_ia, use_llm


async def test_catalogo_requires_authentication(client: AsyncClient) -> None:
    response = await client.get("/scenarios")

    assert response.status_code == 401


async def test_catalogo_lists_scenarios_and_levels(authed: AsyncClient) -> None:
    response = await authed.get("/scenarios")

    assert response.status_code == 200
    body = response.json()
    claves = [escenario["clave"] for escenario in body["escenarios"]]
    assert claves == [
        "restaurante",
        "aeropuerto",
        "hotel",
        "entrevista_trabajo",
        "consultorio_medico",
        "tienda",
    ]
    assert body["niveles"] == ["A1", "A2", "B1", "B2", "C1"]
    assert body["escenarios"][0]["nombre"] == "En el restaurante"


async def test_iniciar_sesion_creates_opening_turn(authed: AsyncClient) -> None:
    fake = FakeLLM(turn_ia("Welcome to the restaurant! What can I get you?"))
    _, body = await start_session(authed, fake)

    assert body["estado"] == "activa"
    assert body["escenario"] == "restaurante"
    assert body["nivel"] == "B1"
    assert body["fecha_fin"] is None
    assert len(body["historial"]) == 1
    assert body["historial"][0]["rol"] == "agente"
    assert body["historial"][0]["contenido"].startswith("Welcome")
    sent = fake.requests[0]
    assert sent["response_format"] == {"type": "json_object"}
    assert sent["messages"][0]["role"] == "system"
    assert "restaurante" in sent["messages"][0]["content"]


async def test_iniciar_sesion_rejects_unknown_scenario(authed: AsyncClient) -> None:
    use_llm(FakeLLM(turn_ia()))

    response = await authed.post("/sessions", json={"escenario": "luna", "nivel": "B1"})

    assert response.status_code == 422


async def test_iniciar_sesion_reports_missing_ai_key(authed: AsyncClient) -> None:
    use_llm(FakeLLM(turn_ia(), api_key=""))

    response = await authed.post(
        "/sessions", json={"escenario": "restaurante", "nivel": "B1"}
    )

    assert response.status_code == 503
    assert response.json()["detail"]["code"] == "ai_not_configured"


async def test_listar_y_obtener_sesiones(authed: AsyncClient) -> None:
    first = FakeLLM(turn_ia("Opening one"))
    _, primera = await start_session(authed, first)
    second = FakeLLM(turn_ia("Opening two"))
    _, segunda = await start_session(authed, second, escenario="hotel", nivel="A2")

    response = await authed.get("/sessions")

    assert response.status_code == 200
    sesiones = response.json()
    assert {sesion["id_sesion"] for sesion in sesiones} == {
        primera["id_sesion"],
        segunda["id_sesion"],
    }
    assert all(sesion["puede_reanudarse"] for sesion in sesiones)
    assert sesiones[0]["escenario"] in {"restaurante", "hotel"}

    detail = await authed.get(f"/sessions/{primera['id_sesion']}")
    assert detail.status_code == 200
    assert len(detail.json()["historial"]) == 1

    filtered = await authed.get("/sessions", params={"estado": "concluida"})
    assert filtered.json() == []


async def test_other_user_cannot_access(authed: AsyncClient) -> None:
    fake = FakeLLM(turn_ia())
    _, body = await start_session(authed, fake)
    id_sesion = body["id_sesion"]

    segundo = await authed.post("/auth/signup", json=unique_signup("b"))
    assert segundo.status_code == 201
    authed.headers.update(auth_headers(segundo.json()["access_token"]))

    detail = await authed.get(f"/sessions/{id_sesion}")
    assert detail.status_code == 404
    assert detail.json()["detail"]["code"] == "session_not_found"

    turno = await authed.post(f"/sessions/{id_sesion}/turnos", json={"texto": "Hello?"})
    assert turno.status_code == 404

    listado = await authed.get("/sessions")
    assert listado.json() == []


async def test_expired_session_is_gone(
    authed: AsyncClient, session: AsyncSession
) -> None:
    fake = FakeLLM(turn_ia())
    _, body = await start_session(authed, fake)
    id_sesion = uuid.UUID(body["id_sesion"])

    await session.execute(
        update(Sesion)
        .where(Sesion.id_sesion == id_sesion)
        .values(fecha_inicio=datetime.now(UTC) - timedelta(days=31))
    )
    await session.commit()

    detail = await authed.get(f"/sessions/{id_sesion}")
    assert detail.status_code == 410
    assert detail.json()["detail"]["code"] == "session_not_available"

    turno = await authed.post(f"/sessions/{id_sesion}/turnos", json={"texto": "Hello?"})
    assert turno.status_code == 410

    cierre = await authed.post(f"/sessions/{id_sesion}/cerrar")
    assert cierre.status_code == 410

    listado = await authed.get("/sessions")
    assert listado.json()[0]["puede_reanudarse"] is False


async def test_pause_and_resume_flow(authed: AsyncClient) -> None:
    fake = FakeLLM(
        turn_ia("Opening"),
        turn_ia("Reply one"),
        turn_ia("Reply two"),
    )
    _, body = await start_session(authed, fake)
    id_sesion = body["id_sesion"]

    turno = await authed.post(
        f"/sessions/{id_sesion}/turnos", json={"texto": "I want a pizza"}
    )
    assert turno.status_code == 200

    pausar = await authed.post(f"/sessions/{id_sesion}/pausar")
    assert pausar.status_code == 200
    assert pausar.json()["estado"] == "pausada"

    bloqueado = await authed.post(
        f"/sessions/{id_sesion}/turnos", json={"texto": "Hello?"}
    )
    assert bloqueado.status_code == 409
    assert bloqueado.json()["detail"]["code"] == "session_not_active"

    otra_pausa = await authed.post(f"/sessions/{id_sesion}/pausar")
    assert otra_pausa.status_code == 409

    reanudar = await authed.post(f"/sessions/{id_sesion}/reanudar")
    assert reanudar.status_code == 200
    assert reanudar.json()["estado"] == "activa"

    turno_dos = await authed.post(
        f"/sessions/{id_sesion}/turnos", json={"texto": "And a soda"}
    )
    assert turno_dos.status_code == 200
    assert turno_dos.json()["mensaje"]["contenido"] == "Reply two"

    doble_reanudar = await authed.post(f"/sessions/{id_sesion}/reanudar")
    assert doble_reanudar.status_code == 409
    assert doble_reanudar.json()["detail"]["code"] == "session_not_paused"


async def test_concluded_session_rejects_state_changes(authed: AsyncClient) -> None:
    fake = FakeLLM(turn_ia("Opening"), turn_ia("Reply"), informe_ia())
    _, body = await start_session(authed, fake)
    id_sesion = body["id_sesion"]

    await authed.post(f"/sessions/{id_sesion}/turnos", json={"texto": "Hello"})
    cierre = await authed.post(f"/sessions/{id_sesion}/cerrar")
    assert cierre.status_code == 200

    reanudar = await authed.post(f"/sessions/{id_sesion}/reanudar")
    assert reanudar.status_code == 409
    assert reanudar.json()["detail"]["code"] == "session_concluded"

    pausar = await authed.post(f"/sessions/{id_sesion}/pausar")
    assert pausar.status_code == 409
