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
    APP_VERSION: str = "1.0.0-sih2026"
    APP_ENV: AppEnv = "development"
    APP_MODE: AppMode = "DEV"
    DEMO_MODE_ENABLED: bool = True

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

    def get_safe_diagnostics(self) -> dict:
        """Returns safe operational configuration without revealing sensitive keys."""
        return {
            "app_name": self.APP_NAME,
            "app_version": self.APP_VERSION,
            "app_env": self.APP_ENV,
            "app_mode": self.APP_MODE,
            "demo_mode_enabled": self.DEMO_MODE_ENABLED,
            "log_level": self.LOG_LEVEL,
            "structured_logging": self.ENABLE_STRUCTURED_JSON_LOGS,
            "has_database": bool(self.DATABASE_URL),
            "has_redis": bool(self.REDIS_URL),
            "has_exotel": self.has_exotel_credentials(),
            "has_sarvam": bool(self.SARVAM_API_KEY),
            "has_gemini": bool(self.GEMINI_API_KEY),
            "cors_origins_count": len(self.CORS_ORIGINS),
        }

    def validate_configuration(self) -> dict:
        """Verifies environment consistency and detects missing dependencies."""
        issues = []
        if self.is_live():
            if not self.DATABASE_URL:
                issues.append("DATABASE_URL is required in LIVE mode.")
            if not self.has_exotel_credentials():
                issues.append("Exotel credentials required in LIVE mode.")
            if not self.SARVAM_API_KEY:
                issues.append("SARVAM_API_KEY required in LIVE mode for Indian STT/TTS.")
            if not self.GEMINI_API_KEY:
                issues.append("GEMINI_API_KEY required in LIVE mode.")

        return {
            "valid": len(issues) == 0,
            "mode": self.APP_MODE,
            "issues": issues,
        }


@lru_cache()
def get_settings() -> Settings:
    return Settings()
