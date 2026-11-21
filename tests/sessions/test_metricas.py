from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.sessions.repository import MetricaRepository
from tests.factories import unique_signup
from tests.helpers import auth_headers
from tests.support import (
    FakeLLM,
    correccion,
    informe_ia,
    start_session,
    turn_ia,
)


async def test_metricas_requires_authentication(client: AsyncClient) -> None:
    response = await client.get("/metrics")

    assert response.status_code == 401


async def test_metricas_resumen(authed: AsyncClient, session: AsyncSession) -> None:
    await start_session(authed, FakeLLM(turn_ia("Opening")))

    fake = FakeLLM(
        turn_ia("Opening"),
        turn_ia("Noted.", errores=[correccion()]),
        turn_ia(
            "Noted.",
            errores=[
                correccion(),
                correccion(
                    tipo="vocabulario",
                    original="very good",
                    correccion_texto="excellent",
                    explicacion="Use a more precise adjective.",
                ),
            ],
        ),
        informe_ia(),
    )
    _, body = await start_session(authed, fake, modo="writing")
    await authed.post(
        f"/sessions/{body['id_sesion']}/turnos", json={"texto": "I go yesterday"}
    )
    await authed.post(
        f"/sessions/{body['id_sesion']}/turnos", json={"texto": "It is very good"}
    )
    cierre = await authed.post(f"/sessions/{body['id_sesion']}/cerrar")
    assert cierre.status_code == 200, cierre.text

    metrica = (await MetricaRepository(session).list())[0]
    metrica.duracion = 185
    await session.commit()

    response = await authed.get("/metrics")

    assert response.status_code == 200
    data = response.json()
    assert data["total_sesiones"] == 2
    assert data["sesiones_concluidas"] == 1
    assert data["sesiones_en_curso"] == 1
    assert data["tiempo_total_segundos"] == 185
    assert data["ultima_practica"] is not None
    assert data["errores_por_tipo"] == {
        "gramatica": 2,
        "vocabulario": 1,
        "orden": 0,
        "otro": 0,
    }
    assert data["errores_gramaticales"] == [
        {
            "original": "I go yesterday",
            "correccion": "I went yesterday",
            "explicacion": "Use the past tense with yesterday.",
            "veces": 2,
        }
    ]


async def test_metricas_are_isolated_by_user(
    authed: AsyncClient, client: AsyncClient
) -> None:
    fake = FakeLLM(turn_ia("Opening"), informe_ia())
    _, body = await start_session(authed, fake)
    await authed.post(f"/sessions/{body['id_sesion']}/cerrar")

    segundo = await client.post("/auth/signup", json=unique_signup("metricas"))
    assert segundo.status_code == 201

    response = await client.get(
        "/metrics",
        headers=auth_headers(segundo.json()["access_token"]),
    )

    assert response.status_code == 200
    data = response.json()
    assert data["total_sesiones"] == 0
    assert data["sesiones_concluidas"] == 0
    assert data["sesiones_en_curso"] == 0
    assert data["tiempo_total_segundos"] == 0
    assert data["ultima_practica"] is None
    assert data["errores_gramaticales"] == []
