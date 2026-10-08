import uuid
from typing import Annotated

from fastapi import Depends

from src.auth.dependencies import CurrentUser
from src.datasources.dependencies import DbSession
from src.sessions.exceptions import SessionNotFound
from src.sessions.models import Sesion
from src.sessions.repository import SesionRepository


async def valid_sesion(
    id_sesion: uuid.UUID,
    user: CurrentUser,
    session: DbSession,
) -> Sesion:
    sesion = await SesionRepository(session).get_by_id_for_user(id_sesion, user.id)
    if sesion is None:
        raise SessionNotFound()
    return sesion


OwnedSession = Annotated[Sesion, Depends(valid_sesion)]
