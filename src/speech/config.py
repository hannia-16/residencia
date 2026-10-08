from pydantic_settings import BaseSettings, SettingsConfigDict


class SpeechConfig(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="GROQ_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    API_KEY: str = ""
    BASE_URL: str = "https://api.groq.com/openai/v1"
    STT_MODEL: str = "whisper-large-v3"
    STT_LANGUAGE: str = "en"
    TIMEOUT_SECONDS: float = 60.0

    @property
    def is_configured(self) -> bool:
        return bool(self.API_KEY.strip())


speech_settings = SpeechConfig()
