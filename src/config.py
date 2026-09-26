from pydantic_settings import BaseSettings, SettingsConfigDict

SHOW_DOCS_ENVIRONMENTS = frozenset({"local", "staging"})


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    ENVIRONMENT: str = "local"
    DATABASE_URL: str = "sqlite+aiosqlite:///./cosa.db"
    SQL_ECHO: bool = False
    CORS_ORIGINS: list[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]

    @property
    def show_docs(self) -> bool:
        return self.ENVIRONMENT in SHOW_DOCS_ENVIRONMENTS


settings = Settings()
