"""SafetyContextAgent: Read-only deterministic adapter over Phase 4 Safety Engine."""

import time
from typing import Any, Dict, List

from app.orchestration.contracts import BaseAgentWorker
from app.orchestration.models import (
    AgentRequest,
    AgentResponse,
    AgentSafetyClassification,
    AgentSpec,
    AgentTimeoutTier,
    AgentType,
)


class SafetyContextAgent(BaseAgentWorker):
    """Deterministic adapter extracting safety state and risk signals without modifying them."""

    def __init__(self):
        spec = AgentSpec(
            name="safety_context_agent",
            version="1.0.0",
            agent_type=AgentType.DETERMINISTIC_ADAPTER,
            capabilities=["safety_evaluation", "threat_detection", "risk_signals"],
            timeout_tier=AgentTimeoutTier.REALTIME_CRITICAL,
            max_latency_ms=25,
            safety_classification=AgentSafetyClassification.READ_ONLY_SAFETY,
            requires_human_review=False,
            is_realtime_capable=True,
            enabled=True,
        )
        super().__init__(spec)

    async def execute(self, request: AgentRequest) -> AgentResponse:
        start_time = time.perf_counter()
        ctx = request.relevant_context or {}

        # Read safety state from relevant context (passed from turn orchestrator or session)
        safety_eval = ctx.get("safety_evaluation") or {}
        safety_state = ctx.get("safety_state") or safety_eval.get("safety_state", "SAFE")
        highest_severity = ctx.get("highest_severity") or safety_eval.get("highest_severity", "NONE")
        action = ctx.get("action") or safety_eval.get("action", "CONTINUE")
        requires_intervention = ctx.get("requires_intervention") or safety_eval.get("requires_intervention", False)
        triggered_rules = ctx.get("triggered_rules") or safety_eval.get("triggered_rules", [])
        active_restrictions = ctx.get("active_restrictions") or safety_eval.get("active_restrictions", [])
        safe_words_detected = ctx.get("safe_words_detected") or safety_eval.get("safe_words_detected", [])

        # Evidence references
        evidence_refs: List[str] = []
        for rule in triggered_rules:
            if isinstance(rule, dict) and "rule_id" in rule:
                evidence_refs.append(f"rule:{rule['rule_id']}")
            elif isinstance(rule, str):
                evidence_refs.append(f"rule:{rule}")

        result: Dict[str, Any] = {
            "safety_state": safety_state,
            "highest_severity": highest_severity,
            "action": action,
            "requires_intervention": requires_intervention,
            "triggered_rules": triggered_rules,
            "active_restrictions": active_restrictions,
            "safe_words_detected": safe_words_detected,
            "is_authoritative": True,
        }

        latency_ms = (time.perf_counter() - start_time) * 1000
        return self.create_success_response(
            request=request,
            result=result,
            confidence=1.0,
            evidence_refs=evidence_refs,
            latency_ms=latency_ms,
        )
