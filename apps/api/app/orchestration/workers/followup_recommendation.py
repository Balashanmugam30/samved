"""FollowupRecommendationAgent: Non-autonomous continuity and follow-up recommendation worker."""

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
from app.schemas.events import FollowupPriority, FollowupType


class FollowupRecommendationAgent(BaseAgentWorker):
    """Worker agent analyzing dialogue context to recommend bounded follow-up tasks.

    Absolute Safety Mandates:
    - Never initiates autonomous outbound calling or messaging.
    - Follow-up recommendations are purely advisory for the human tele-counselor.
    - Requires explicit operator authorization, consent confirmation, and safe window validation.
    """

    def __init__(self):
        spec = AgentSpec(
            name="followup_recommendation_agent",
            version="1.0.0",
            agent_type=AgentType.DETERMINISTIC_ADAPTER,
            capabilities=[
                "followup_recommendation",
                "continuity_planning",
                "consent_review",
            ],
            timeout_tier=AgentTimeoutTier.REALTIME_NORMAL,
            max_latency_ms=100,
            safety_classification=AgentSafetyClassification.OPERATIONAL,
            requires_human_review=True,
            is_realtime_capable=True,
            enabled=True,
        )
        super().__init__(spec)

    async def execute(self, request: AgentRequest) -> AgentResponse:
        start_time = time.perf_counter()

        query_text = ""
        if request.last_caller_utterance:
            query_text = request.last_caller_utterance.lower()
        elif request.transcript_history:
            for u in reversed(request.transcript_history):
                if u.get("speaker") == "caller":
                    query_text = u.get("text", "").lower()
                    break

        recommendation_needed = False
        suggested_type = FollowupType.HUMAN_CALLBACK
        suggested_priority = FollowupPriority.NORMAL
        suggested_purpose = "Human callback to verify caller well-being and referred support."
        rationale = "General continuity review suggested."

        # Detect explicit callback / check-in requests in dialogue
        callback_keywords = ["call me back", "check on me", "reach out", "follow up", "call tomorrow", "call later"]
        resource_keywords = ["shelter", "hospital", "police", "legal aid", "scheme", "welfare"]

        if any(kw in query_text for kw in callback_keywords):
            recommendation_needed = True
            suggested_type = FollowupType.HUMAN_CALLBACK
            suggested_priority = FollowupPriority.HIGH
            suggested_purpose = "Operator requested callback as caller indicated desire for continued contact."
            rationale = "Caller explicitly mentioned callback or follow-up in dialogue."
        elif any(kw in query_text for kw in resource_keywords):
            recommendation_needed = True
            suggested_type = FollowupType.RESOURCE_FOLLOW_UP
            suggested_priority = FollowupPriority.NORMAL
            suggested_purpose = "Verify whether caller was able to access referred assistance resource."
            rationale = "Dialogue involved support resources or welfare services."

        result: Dict[str, Any] = {
            "has_recommendation": recommendation_needed,
            "suggested_type": suggested_type.value if recommendation_needed else None,
            "suggested_priority": suggested_priority.value if recommendation_needed else None,
            "suggested_purpose": suggested_purpose if recommendation_needed else None,
            "rationale": rationale if recommendation_needed else None,
            "requires_operator_confirmation": True,
            "no_autonomous_contact": True,
        }

        evidence_refs: List[str] = [f"turn:{request.turn_id}"]
        latency_ms = (time.perf_counter() - start_time) * 1000

        return self.create_success_response(
            request=request,
            result=result,
            confidence=0.90 if recommendation_needed else 0.50,
            evidence_refs=evidence_refs,
            latency_ms=latency_ms,
        )
