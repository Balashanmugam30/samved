from functools import lru_cache
from typing import List, Literal, Optional
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

AppEnv = Literal["development", "staging", "production"]
AppMode = Literal["DEV", "SIMULATION", "LIVE"]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Core Application Settings
    APP_NAME: str = "samved-api"
    APP_VERSION: str = "0.1.0"
    APP_ENV: AppEnv = "development"
    APP_MODE: AppMode = "DEV"

    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    LOG_LEVEL: str = "INFO"
    ENABLE_STRUCTURED_JSON_LOGS: bool = True

    # Security
    JWT_SECRET: str = "insecure-dev-secret-change-in-production-min-32-chars"
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]

    # Database & Cache (Optional in DEV, inspected gracefully in /ready)
    DATABASE_URL: Optional[str] = None
    REDIS_URL: Optional[str] = None

    # Telephony Provider (Phase 1+)
    EXOTEL_ENABLED: bool = False
    EXOTEL_ACCOUNT_SID: Optional[str] = None
    EXOTEL_API_KEY: Optional[str] = None
    EXOTEL_API_TOKEN: Optional[str] = None
    EXOTEL_SUB_DOMAIN: str = "api.exotel.com"
    EXOTEL_CALLER_ID: Optional[str] = None
    EXOTEL_PHONE_NUMBER: Optional[str] = None
    EXOTEL_WEBHOOK_BASE_URL: Optional[str] = None
    EXOTEL_STREAM_URL: Optional[str] = None
    EXOTEL_VERIFY_SIGNATURE: bool = False
    EXOTEL_WEBHOOK_SECRET: Optional[str] = None

    PUBLIC_BASE_URL: str = "http://localhost:8000"
    PUBLIC_WS_BASE_URL: str = "ws://localhost:8000"

    TWILIO_ACCOUNT_SID: Optional[str] = None
    TWILIO_AUTH_TOKEN: Optional[str] = None
    TWILIO_PHONE_NUMBER: Optional[str] = None

    # Speech Provider (Phase 2+)
    SARVAM_API_KEY: Optional[str] = None

    # LLM Providers (Phase 2+)
    GEMINI_API_KEY: Optional[str] = None
    OPENAI_API_KEY: Optional[str] = None
    OPENROUTER_API_KEY: Optional[str] = None

    # Observability
    SENTRY_DSN: Optional[str] = None

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v):
        if isinstance(v, str):
            return [i.strip() for i in v.split(",") if i.strip()]
        return v

    def is_dev(self) -> bool:
        return self.APP_MODE == "DEV"

    def is_simulation(self) -> bool:
        return self.APP_MODE == "SIMULATION"

    def is_live(self) -> bool:
        return self.APP_MODE == "LIVE"

    def has_exotel_credentials(self) -> bool:
        return bool(
            self.EXOTEL_ACCOUNT_SID
            and self.EXOTEL_API_KEY
            and self.EXOTEL_API_TOKEN
        )

    def is_exotel_live_ready(self) -> bool:
        return self.is_live() and self.EXOTEL_ENABLED and self.has_exotel_credentials()


@lru_cache()
def get_settings() -> Settings:
    return Settings()
