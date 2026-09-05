"""Base contracts and abstract worker interface for SAMVED Phase 9 Multi-Agent Orchestration."""

from abc import ABC, abstractmethod
from datetime import datetime, timezone
import logging
from typing import Any, Dict, List, Optional

from app.orchestration.models import (
    AgentRequest,
    AgentResponse,
    AgentSpec,
    AgentStatus,
)

logger = logging.getLogger(__name__)


class BaseAgentWorker(ABC):
    """Abstract base class for all specialized AI agent workers in SAMVED."""

    def __init__(self, spec: AgentSpec):
        self.spec = spec

    @property
    def name(self) -> str:
        return self.spec.name

    @property
    def capabilities(self) -> List[str]:
        return self.spec.capabilities

    @property
    def max_latency_ms(self) -> int:
        return self.spec.max_latency_ms

    @abstractmethod
    async def execute(self, request: AgentRequest) -> AgentResponse:
        """Execute the agent task asynchronously within the deadline.
        
        Must guarantee return within request deadline or raise an exception caught by executor.
        """
        pass

    def validate_output(self, response: AgentResponse) -> AgentResponse:
        """Validate agent output against expectations and safety constraints.
        
        Subclasses can override to add specific schema checks.
        """
        if not response.request_id or not response.call_id or not response.turn_id:
            response.status = AgentStatus.FAILED
            response.warnings.append("Missing required identifier in response")
        return response

    def create_fallback_response(
        self,
        request: AgentRequest,
        status: AgentStatus = AgentStatus.DEGRADED,
        error_msg: str = "",
        latency_ms: float = 0.0,
        result: Optional[Dict[str, Any]] = None,
    ) -> AgentResponse:
        """Create a safe fallback response when execution fails, times out, or cancels."""
        return AgentResponse(
            request_id=request.request_id,
            call_id=request.call_id,
            turn_id=request.turn_id,
            agent_name=self.spec.name,
            agent_version=self.spec.version,
            status=status,
            result=result or {},
            confidence=0.0 if status in (AgentStatus.FAILED, AgentStatus.TIMED_OUT, AgentStatus.CANCELLED) else 0.5,
            evidence_refs=[],
            latency_ms=latency_ms,
            warnings=[error_msg] if error_msg else [],
            produced_at=datetime.now(timezone.utc).isoformat(),
        )

    def create_success_response(
        self,
        request: AgentRequest,
        result: Dict[str, Any],
        confidence: float = 1.0,
        evidence_refs: Optional[List[str]] = None,
        latency_ms: float = 0.0,
        warnings: Optional[List[str]] = None,
    ) -> AgentResponse:
        """Create a standard successful response."""
        return AgentResponse(
            request_id=request.request_id,
            call_id=request.call_id,
            turn_id=request.turn_id,
            agent_name=self.spec.name,
            agent_version=self.spec.version,
            status=AgentStatus.SUCCESS,
            result=result,
            confidence=confidence,
            evidence_refs=evidence_refs or [],
            latency_ms=latency_ms,
            warnings=warnings or [],
            produced_at=datetime.now(timezone.utc).isoformat(),
        )
