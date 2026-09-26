from enum import StrEnum
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class DeepSeekModel(StrEnum):
    FLASH = "deepseek-flash"
    V4_PRO = "deepseek-v4-pro"


ReasoningEffort = Literal["low", "medium", "high"]


class AIConfig(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="DEEPSEEK_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    API_KEY: str = ""
    BASE_URL: str = "https://api.deepseek.com"
    MODEL: DeepSeekModel = DeepSeekModel.FLASH
    TIMEOUT_SECONDS: float = 60.0
    MAX_TOKENS: int = 2048
    TEMPERATURE: float = 1.0
    THINKING: bool = False
    REASONING_EFFORT: ReasoningEffort = "medium"

    @property
    def is_configured(self) -> bool:
        return bool(self.API_KEY.strip())


ai_settings = AIConfig()
