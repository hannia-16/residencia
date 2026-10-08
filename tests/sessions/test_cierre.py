from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.sessions.repository import MetricaRepository
from tests.support import (
    DEFAULT_REPORT,
    FakeLLM,
    correccion,
    informe_ia,
    start_session,
    turn_ia,
)


async def test_close_generates_report_and_metric(
    authed: AsyncClient, session: AsyncSession
) -> None:
    fake = FakeLLM(
        turn_ia("Opening"),
        turn_ia("Noted.", errores=[correccion()]),
        informe_ia(),
    )
    _, body = await start_session(authed, fake)
    id_sesion = body["id_sesion"]
    await authed.post(f"/sessions/{id_sesion}/turnos", json={"texto": "I go yesterday"})

    metrics = MetricaRepository(session)
    assert await metrics.count() == 0

    cierre = await authed.post(f"/sessions/{id_sesion}/cerrar")

    assert cierre.status_code == 200, cierre.text
    informe = cierre.json()
    assert informe["id_sesion"] == id_sesion
    assert informe["resumen"] == DEFAULT_REPORT
    assert informe["areas_mejora"] == ["Practice past tenses"]
    assert informe["fortalezas"] == ["Good interaction"]
    assert informe["aviso"].startswith("Este reporte es orientativo")
    assert len(informe["errores"]) == 1
    assert informe["errores"][0]["tipo"] == "gramatica"
    assert len(informe["retroalimentaciones"]) == 1
    assert informe["retroalimentaciones"][0]["entrada_usuario"] == "I go yesterday"

    detail = await authed.get(f"/sessions/{id_sesion}")
    assert detail.json()["estado"] == "concluida"
    assert detail.json()["fecha_fin"] is not None

    guardado = await authed.get(f"/sessions/{id_sesion}/retroalimentacion")
    assert guardado.status_code == 200
    assert guardado.json()["resumen"] == DEFAULT_REPORT

    assert await metrics.count() == 1
    metrica = (await metrics.list())[0]
    assert metrica.errores == {"gramatica": 1}
    assert metrica.duracion >= 0
    assert metrica.resumen_ia == DEFAULT_REPORT

    doble_cierre = await authed.post(f"/sessions/{id_sesion}/cerrar")
    assert doble_cierre.status_code == 409
    assert doble_cierre.json()["detail"]["code"] == "session_concluded"


async def test_metrics_are_not_recorded_for_open_sessions(
    authed: AsyncClient, session: AsyncSession
) -> None:
    fake = FakeLLM(turn_ia("Opening"))
    await start_session(authed, fake)

    assert await MetricaRepository(session).count() == 0


async def test_evaluation_flow(authed: AsyncClient) -> None:
    fake = FakeLLM(turn_ia("Opening"), turn_ia("Reply"), informe_ia())
    _, body = await start_session(authed, fake)
    id_sesion = body["id_sesion"]

    antes = await authed.post(
        f"/sessions/{id_sesion}/evaluacion", json={"calificacion": 4}
    )
    assert antes.status_code == 409
    assert antes.json()["detail"]["code"] == "evaluation_not_allowed"

    await authed.post(f"/sessions/{id_sesion}/turnos", json={"texto": "Hello"})
    await authed.post(f"/sessions/{id_sesion}/cerrar")

    evaluacion = await authed.post(
        f"/sessions/{id_sesion}/evaluacion",
        json={"calificacion": 4, "comentario": "Muy útil"},
    )
    assert evaluacion.status_code == 204

    duplicada = await authed.post(
        f"/sessions/{id_sesion}/evaluacion", json={"calificacion": 5}
    )
    assert duplicada.status_code == 409
    assert duplicada.json()["detail"]["code"] == "evaluation_already_submitted"

    invalida = await authed.post(
        f"/sessions/{id_sesion}/evaluacion", json={"calificacion": 6}
    )
    assert invalida.status_code == 422

    detail = await authed.get(f"/sessions/{id_sesion}")
    evaluacion_guardada = detail.json()["evaluacion_sistema"]
    assert evaluacion_guardada["calificacion"] == 4
    assert evaluacion_guardada["comentario"] == "Muy útil"
