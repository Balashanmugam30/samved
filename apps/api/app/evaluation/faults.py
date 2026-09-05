"""
SAMVED Phase 14: Deterministic Fault Injection Module
Simulates bounded system faults during evaluation replays without risking production systems.
"""

from typing import Any, Dict
from app.evaluation.models import FaultType


class FaultInjectionInterceptor:
    """
    Applies deterministic faults to pipeline stages based on scenario or turn configuration.
    """

    @staticmethod
    def intercept_stt(fault: FaultType, transcript: str) -> Dict[str, Any]:
        if fault == FaultType.STT_UNAVAILABLE:
            return {"error": "STT_SERVICE_UNAVAILABLE", "transcript": None, "degraded": True}
        elif fault == FaultType.MALFORMED_EVENT:
            return {"error": "CORRUPT_PAYLOAD", "transcript": "\x00\x01\x02", "degraded": True}
        return {"transcript": transcript, "degraded": False}

    @staticmethod
    def intercept_orchestration(fault: FaultType, agents_to_execute: list) -> Dict[str, Any]:
        if fault == FaultType.ORCHESTRATION_TIMEOUT:
            return {
                "timeout": True,
                "completed_agents": ["safety_context_agent"],
                "failed_agents": ["operator_briefing_agent"],
                "fallback_briefing": "Downstream timeout: Safety Engine authority preserved.",
            }
        elif fault == FaultType.STALE_AGENT_RESULT:
            return {
                "stale_rejected": True,
                "warning": "Stale agent result rejected by DAG executor.",
                "completed_agents": ["safety_context_agent"],
            }
        elif fault == FaultType.PARTIAL_STAGE_FAILURE:
            return {
                "partial_failure": True,
                "failed_agents": ["support_options_agent"],
                "fallback_briefing": "Partial worker failure: Core triage completed.",
            }
        return {"timeout": False, "completed_agents": agents_to_execute}

    @staticmethod
    def intercept_rag(fault: FaultType) -> Dict[str, Any]:
        if fault == FaultType.KNOWLEDGE_TIMEOUT:
            return {
                "timeout": True,
                "citations": [],
                "fallback": "Legal/scheme retrieval timed out. Tele-counselor consultation advised.",
            }
        return {"timeout": False}
