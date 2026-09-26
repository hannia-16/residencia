import uuid
from datetime import datetime

from pydantic import EmailStr, Field

from src.models import CustomModel

USERNAME_PATTERN = r"^[A-Za-z0-9_-]+$"


class UserCreate(CustomModel):
    email: EmailStr
    username: str = Field(min_length=1, max_length=128, pattern=USERNAME_PATTERN)
    password: str = Field(min_length=8, max_length=128)


class UserLogin(CustomModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class UserRead(CustomModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    email: EmailStr
    username: str
    is_active: bool
    created_at: datetime
    updated_at: datetime


class TokenPair(CustomModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserRead
