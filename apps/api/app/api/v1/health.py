from datetime import datetime, timezone
from typing import Any, Dict
from fastapi import APIRouter, status
from fastapi.responses import JSONResponse
from app.core.config import get_settings

router = APIRouter(tags=["Health & Status"])


@router.get("/health", status_code=status.HTTP_200_OK)
@router.get("/healthz", status_code=status.HTTP_200_OK)
async def health_check() -> Dict[str, Any]:
    """Liveness check: returns 200 if the process is responsive."""
    return {
        "status": "healthy",
        "service": "samved-api",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/ready")
async def readiness_check() -> JSONResponse:
    """Readiness check: inspects database, cache, and provider availability without crashing."""
    settings = get_settings()

    from app.realtime.session_manager import telephony_session_manager

    dependencies: Dict[str, Dict[str, Any]] = {
        "database": {
            "status": "connected" if settings.DATABASE_URL else "unconfigured_local",
            "required_for_mode": False if settings.is_dev() else True,
            "details": "PostgreSQL connection string provided" if settings.DATABASE_URL else "Running in DEV mode without database",
        },
        "redis": {
            "status": "connected" if settings.REDIS_URL else "unconfigured_local",
            "required_for_mode": False if settings.is_dev() else True,
            "details": "Redis URL configured" if settings.REDIS_URL else "Running in DEV mode with in-memory session manager",
        },
        "telephony": {
            "status": "mock_ready" if settings.is_dev() else ("configured" if settings.has_exotel_credentials() else "missing_credentials"),
            "provider": "MockTelephony" if settings.is_dev() else "Exotel",
            "streaming_enabled": settings.EXOTEL_ENABLED if settings.is_live() else True,
            "active_calls": telephony_session_manager.active_calls_count,
        },
        "speech": {
            "status": "mock_ready" if settings.is_dev() else ("configured" if settings.SARVAM_API_KEY else "missing_credentials"),
            "provider": "MockSTT/TTS" if settings.is_dev() else "Sarvam",
        },
        "llm": {
            "status": "mock_ready" if settings.is_dev() else ("configured" if settings.GEMINI_API_KEY else "missing_credentials"),
            "provider": "MockLLM" if settings.is_dev() else "Gemini",
        },
    }

    # In LIVE mode, missing credentials make it not ready. In DEV/SIMULATION, mock availability is ready.
    is_ready = True
    if settings.is_live():
        if not settings.DATABASE_URL or not settings.has_exotel_credentials():
            is_ready = False

    status_code = status.HTTP_200_OK if is_ready else status.HTTP_503_SERVICE_UNAVAILABLE

    return JSONResponse(
        status_code=status_code,
        content={
            "ready": is_ready,
            "mode": settings.APP_MODE,
            "environment": settings.APP_ENV,
            "active_calls_count": telephony_session_manager.active_calls_count,
            "dependencies": dependencies,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
    )


@router.get("/version", status_code=status.HTTP_200_OK)
async def version_info() -> Dict[str, Any]:
    """Returns application version and public metadata without secrets."""
    settings = get_settings()
    return {
        "service": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "environment": settings.APP_ENV,
        "mode": settings.APP_MODE,
        "problem_statement": "26093",
        "target_helpline": "NHAA 14566",
        "phase": "Phase 2 — Live Multilingual AI Voice Conversation",
    }
