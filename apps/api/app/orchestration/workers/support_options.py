"""SupportOptionsAgent: Structured placeholder stub for future Phase 10 Legal/Policy RAG."""

import time
from typing import Any, Dict

from app.orchestration.contracts import BaseAgentWorker
from app.orchestration.models import (
    AgentRequest,
    AgentResponse,
    AgentSafetyClassification,
    AgentSpec,
    AgentStatus,
    AgentTimeoutTier,
    AgentType,
)


class SupportOptionsAgent(BaseAgentWorker):
    """Interface stub for Phase 10 Legal/Policy RAG.
    
    Explicitly returns NOT_AVAILABLE / NEEDS_KNOWLEDGE_BASE until Phase 10 is implemented.
    This guarantees zero premature ungrounded LLM hallucination of legal or shelter resources.
    """

    def __init__(self):
        spec = AgentSpec(
            name="support_options_agent",
            version="1.0.0",
            agent_type=AgentType.INTERFACE_STUB,
            capabilities=["support_options_retrieval", "policy_guidelines", "shelter_referrals"],
            timeout_tier=AgentTimeoutTier.REALTIME_CRITICAL,
            max_latency_ms=25,
            safety_classification=AgentSafetyClassification.PLACEHOLDER,
            requires_human_review=True,
            is_realtime_capable=True,
            enabled=True,
        )
        super().__init__(spec)

    async def execute(self, request: AgentRequest) -> AgentResponse:
        start_time = time.perf_counter()

        result: Dict[str, Any] = {
            "status": "NOT_AVAILABLE",
            "reason": "NEEDS_KNOWLEDGE_BASE",
            "phase_target": "Phase 10 (Legal & Policy RAG)",
            "options": [],
            "message": "Specialized support options knowledge base will be integrated in Phase 10. No ungrounded advice generated.",
        }

        latency_ms = (time.perf_counter() - start_time) * 1000
        return self.create_success_response(
            request=request,
            result=result,
            confidence=1.0,
            evidence_refs=["system:phase_boundary_guard"],
            latency_ms=latency_ms,
            warnings=["Support options retrieval is disabled until Phase 10 RAG milestone."],
        )
