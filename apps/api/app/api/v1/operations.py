"""SAMVED Phase 16: Operations & Reliability Telemetry API.

Provides operational observability for SIH evaluators, infrastructure engineers, and operations managers.
Exposes real-time circuit breaker controls, dependency telemetry, and subsystem health.
"""

import time
from datetime import datetime, timezone
from typing import Any, Dict, List
from fastapi import APIRouter, HTTPException, status

from app.core.config import get_settings
from app.core.circuit import (
    get_circuit_breaker,
    list_circuit_breakers,
    reset_all_circuit_breakers,
)
from app.realtime.connection_manager import manager
from app.realtime.session_manager import telephony_session_manager
from app.security.service import get_security_service

operations_router = APIRouter(tags=["Operations & Observability"])

_STARTUP_TIMESTAMP = time.time()


@operations_router.get("/status")
async def get_operations_status() -> Dict[str, Any]:
    """Retrieve comprehensive real-time operational status, uptime, and component telemetry."""
    settings = get_settings()
    sec_service = get_security_service()
    sec_summary = sec_service.get_security_summary()

    uptime_seconds = round(time.time() - _STARTUP_TIMESTAMP, 1)

    return {
        "service": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "environment": settings.APP_ENV,
        "mode": settings.APP_MODE,
        "uptime_seconds": uptime_seconds,
        "uptime_formatted": f"{int(uptime_seconds // 3600)}h {int((uptime_seconds % 3600) // 60)}m {int(uptime_seconds % 60)}s",
        "telephony": {
            "active_calls": telephony_session_manager.active_calls_count,
            "provider": "Exotel" if settings.is_live() else "MockTelephony",
        },
        "realtime_websockets": {
            "connected_operators": manager.total_operators,
            "gateway_status": "OPERATIONAL",
        },
        "security_governance": {
            "posture": sec_summary.get("overall_posture", "HEALTHY"),
            "active_controls": sec_summary.get("controls_count", 11),
            "audit_chain_valid": sec_summary.get("audit_chain", {}).get("is_valid", True),
        },
        "circuit_breakers": list_circuit_breakers(),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@operations_router.get("/circuits", response_model=List[Dict[str, Any]])
async def get_circuits() -> List[Dict[str, Any]]:
    """List all registered circuit breakers and their real-time trip states."""
    return list_circuit_breakers()


@operations_router.post("/circuits/{name}/reset")
async def reset_circuit(name: str) -> Dict[str, Any]:
    """Manually reset a specific circuit breaker to CLOSED (operational) state."""
    breaker = get_circuit_breaker(name)
    breaker.reset()
    return {
        "message": f"Circuit breaker '{name}' has been manually reset.",
        "circuit": breaker.get_status(),
    }


@operations_router.post("/circuits/reset-all")
async def reset_all_circuits() -> Dict[str, Any]:
    """Reset all active circuit breakers across all providers."""
    reset_all_circuit_breakers()
    return {
        "message": "All circuit breakers reset to operational CLOSED state.",
        "circuits": list_circuit_breakers(),
    }
