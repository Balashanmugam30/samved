"""KnowledgeRetrievalAgent: Deterministic citation-first legal/policy retrieval worker."""

import time
from typing import Any, Dict, List

from app.knowledge.models import KnowledgeJurisdiction, KnowledgeQuery, TopicCategory
from app.knowledge.service import knowledge_service
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


class KnowledgeRetrievalAgent(BaseAgentWorker):
    """Worker agent retrieving authoritative legal and policy provisions for SAMVED callers.
    
    Advisory worker with zero authority to mutate safety state, SVI, or make legal decisions.
    Produces citation-backed guidance with provenance metadata.
    """

    def __init__(self):
        spec = AgentSpec(
            name="knowledge_retrieval_agent",
            version="1.0.0",
            agent_type=AgentType.DETERMINISTIC_ADAPTER,
            capabilities=["legal_policy_retrieval", "citation_generation", "shelter_guidelines"],
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

        # Determine query and jurisdiction from request context
        query_text = ""
        if request.last_caller_utterance:
            query_text = request.last_caller_utterance
        elif request.transcript_history:
            # Last caller transcript
            for u in reversed(request.transcript_history):
                if u.get("speaker") == "caller":
                    query_text = u.get("text", "")
                    break

        if not query_text:
            query_text = "emergency victim support shelter guidelines"

        # Map language/context to jurisdiction if known
        jurisdiction = KnowledgeJurisdiction.INDIA.value
        if request.language == "ta-IN":
            jurisdiction = KnowledgeJurisdiction.TAMIL_NADU.value

        query = KnowledgeQuery(
            query=query_text,
            language=request.language,
            jurisdiction=jurisdiction,
            topic=TopicCategory.PROTECTION,
            effective_only=True,
            max_results=3,
            call_id=request.call_id,
        )

        search_result = await knowledge_service.search(query)

        evidence_refs: List[str] = [
            f"citation:{c.citation_id}" for c in search_result.citations
        ]

        warnings: List[str] = []
        if search_result.conflict_detected:
            warnings.append("Contradictory policy directives detected among applicable sources.")
        if search_result.requires_human_review:
            warnings.append("Human counselor review recommended for consequential action.")

        latency_ms = (time.perf_counter() - start_time) * 1000

        return self.create_success_response(
            request=request,
            result=search_result.model_dump(),
            confidence=0.95 if search_result.status == "COMPLETED" else 0.5,
            evidence_refs=evidence_refs,
            latency_ms=latency_ms,
            warnings=warnings,
        )

    def generate_fallback_result(self, request: AgentRequest) -> Dict[str, Any]:
        return {
            "status": "DEGRADED",
            "query": request.last_caller_utterance or "support",
            "total_found": 0,
            "results": [],
            "citations": [],
            "ai_summary": "Knowledge retrieval temporarily degraded. Operator manual review required.",
            "requires_human_review": True,
            "review_reasons": ["FALLBACK_ACTIVATED"],
            "conflict_detected": False,
        }
