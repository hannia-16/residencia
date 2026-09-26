from datetime import timedelta

from pydantic_settings import BaseSettings, SettingsConfigDict


class AuthConfig(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="AUTH_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    JWT_ALG: str = "HS256"
    JWT_SECRET: str = "insecure-development-secret"
    JWT_EXP_MINUTES: int = 5
    REFRESH_TOKEN_KEY: str = "insecure-development-refresh-secret"
    REFRESH_TOKEN_EXP: timedelta = timedelta(days=30)
    SECURE_COOKIES: bool = True
    REFRESH_COOKIE_NAME: str = "refresh_token"

    @property
    def access_token_exp(self) -> timedelta:
        return timedelta(minutes=self.JWT_EXP_MINUTES)


auth_settings = AuthConfig()
