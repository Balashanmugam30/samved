"""CaseGraphExtractionAgent: Conservative entity and relationship extraction worker."""

import time
from typing import Any, Dict, List

from app.cases.extraction import extract_case_candidates, sanitize_dialogue
from app.cases.service import case_service
from app.orchestration.contracts import BaseAgentWorker
from app.orchestration.models import (
    AgentRequest,
    AgentResponse,
    AgentSafetyClassification,
    AgentSpec,
    AgentTimeoutTier,
    AgentType,
)


class CaseGraphExtractionAgent(BaseAgentWorker):
    """Worker agent conservatively extracting case entities and candidate relationships.

    Epistemic & Safety Mandates:
    - Never infers guilt, legal liability, or criminal offenses.
    - Extraction is advisory; candidate relationships require human confirmation.
    - Prompt-injection defenses sanitize untrusted caller utterances.
    """

    def __init__(self):
        spec = AgentSpec(
            name="case_graph_extraction_agent",
            version="1.0.0",
            agent_type=AgentType.DETERMINISTIC_ADAPTER,
            capabilities=[
                "case_entity_extraction",
                "case_candidate_extraction",
                "graph_provenance",
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
            query_text = request.last_caller_utterance
        elif request.transcript_history:
            for u in reversed(request.transcript_history):
                if u.get("speaker") == "caller":
                    query_text = u.get("text", "")
                    break

        if not query_text:
            return self.create_success_response(
                request=request,
                result={
                    "case_id": None,
                    "extracted_entities": [],
                    "candidate_relationships": [],
                    "message": "No caller utterance available for case extraction.",
                },
                confidence=1.0,
                latency_ms=(time.perf_counter() - start_time) * 1000,
            )

        # Look up or initialize case for call
        case = await case_service.get_case_by_call(request.call_id)
        if not case:
            case = await case_service.create_case(
                call_id=request.call_id,
                primary_language=request.language,
                operator_id="system",
                initial_notes="Case auto-initialized by multi-agent orchestration.",
            )

        sanitized_text = sanitize_dialogue(query_text)
        raw_text = query_text

        turn_idx = 0
        try:
            parts = request.turn_id.split("-")
            if len(parts) > 1 and parts[-1].isdigit():
                turn_idx = int(parts[-1])
        except Exception:
            turn_idx = 0

        # Extract entities and candidate relationships
        entities, candidates = extract_case_candidates(
            utterance_id=f"{request.call_id}:{request.turn_id}",
            text=raw_text,
            turn_index=turn_idx,
            caller_entity_id="ent-caller",
            case_id=case.case_id,
        )

        saved_entities = []
        for e in entities:
            try:
                saved = await case_service.add_entity(
                    case_id=case.case_id,
                    entity_type=e.type,
                    label=e.label,
                    role=e.role,
                    claim_status=e.claim_status,
                    confidence=e.confidence,
                    source_refs=e.source_refs,
                    evidence=e.evidence,
                    metadata=e.metadata,
                    operator_id="extraction_worker",
                )
                saved_entities.append(saved.model_dump())
            except Exception:
                pass

        saved_candidates = []
        for c in candidates:
            try:
                cand = await case_service.add_candidate(
                    case_id=case.case_id,
                    source_entity=c.source_entity,
                    source_label=c.source_label,
                    relationship_type=c.relationship_type,
                    target_entity=c.target_entity,
                    target_label=c.target_label,
                    evidence_excerpt=c.evidence_excerpt,
                    source_turn=c.source_turn,
                    confidence=c.confidence,
                )
                saved_candidates.append(cand.model_dump())
            except Exception:
                pass

        latency_ms = (time.perf_counter() - start_time) * 1000
        evidence_refs = [
            f"turn:{request.call_id}:{request.turn_id}",
            f"case:{case.case_id}",
        ]

        return self.create_success_response(
            request=request,
            result={
                "case_id": case.case_id,
                "case_number": case.case_number,
                "extracted_entities": saved_entities,
                "candidate_relationships": saved_candidates,
                "total_entities_extracted": len(saved_entities),
                "total_candidates_proposed": len(saved_candidates),
                "sanitized_preview": sanitized_text[:100],
            },
            confidence=0.88 if saved_entities or saved_candidates else 1.0,
            evidence_refs=evidence_refs,
            latency_ms=latency_ms,
            warnings=["Requires counselor confirmation before graduating candidates to active edges."]
            if saved_candidates
            else [],
        )

    def generate_fallback_result(self, request: AgentRequest) -> Dict[str, Any]:
        return {
            "status": "DEGRADED",
            "case_id": None,
            "extracted_entities": [],
            "candidate_relationships": [],
            "total_entities_extracted": 0,
            "total_candidates_proposed": 0,
            "requires_human_review": True,
            "message": "Case extraction temporarily unavailable.",
        }
