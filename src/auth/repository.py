import uuid

from src.auth.models import User
from src.datasources.base import Repository


class UserRepository(Repository[User]):
    model = User

    async def get_by_email(self, email: str) -> User | None:
        return await self.one_or_none(email=email)

    async def get_by_username(self, username: str) -> User | None:
        return await self.one_or_none(username=username)

    async def get_by_id(self, user_id: uuid.UUID) -> User | None:
        return await self.get(user_id)
