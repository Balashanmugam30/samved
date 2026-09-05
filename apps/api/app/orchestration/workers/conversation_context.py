"""ConversationContextAgent: Facts, timeline reconstruction, gap analysis, and contradiction detection."""

import re
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


class ConversationContextAgent(BaseAgentWorker):
    """Context worker extracting structured call facts, gaps, and timeline cues."""

    # Simple regex patterns for entity extraction (location, relation, time)
    LOCATION_KEYWORDS = ["chennai", "coimbatore", "madurai", "salem", "trichy", "delhi", "mumbai", "house", "home", "room", "outside", "station"]
    RELATION_KEYWORDS = ["husband", "father", "mother", "in-laws", "brother", "neighbor", "landlord", "employer", "partner"]
    TIMING_KEYWORDS = ["yesterday", "today", "morning", "night", "last week", "now", "hours ago"]

    def __init__(self):
        spec = AgentSpec(
            name="conversation_context_agent",
            version="1.0.0",
            agent_type=AgentType.LLM_WORKER,
            capabilities=["fact_extraction", "timeline_reconstruction", "gap_analysis", "contradiction_detection"],
            timeout_tier=AgentTimeoutTier.REALTIME_NORMAL,
            max_latency_ms=150,
            safety_classification=AgentSafetyClassification.ADVISORY,
            requires_human_review=False,
            is_realtime_capable=True,
            enabled=True,
        )
        super().__init__(spec)

    async def execute(self, request: AgentRequest) -> AgentResponse:
        start_time = time.perf_counter()
        ctx = request.relevant_context or {}
        transcript = ctx.get("transcript") or ctx.get("text") or ""
        history = ctx.get("history") or []

        # Combine transcripts for factual analysis
        combined_text = " ".join([h.get("text", "") for h in history if isinstance(h, dict)] + [transcript]).lower()

        # Extract entities
        found_locations = [loc for loc in self.LOCATION_KEYWORDS if loc in combined_text]
        found_relations = [rel for rel in self.RELATION_KEYWORDS if rel in combined_text]
        found_timing = [t for t in self.TIMING_KEYWORDS if t in combined_text]

        key_facts: List[str] = []
        if found_locations:
            key_facts.append(f"Location cues: {', '.join(found_locations)}")
        if found_relations:
            key_facts.append(f"Involved parties: {', '.join(found_relations)}")
        if found_timing:
            key_facts.append(f"Temporal cues: {', '.join(found_timing)}")

        if not key_facts and transcript:
            key_facts.append(f"Current statement: {transcript[:100]}")

        # Gap analysis
        unresolved_gaps: List[str] = []
        if not found_locations:
            unresolved_gaps.append("Exact physical location not confirmed")
        safe_status_known = any("safe" in text for text in [combined_text])
        if not safe_status_known:
            unresolved_gaps.append("Caller immediate safety/privacy not confirmed")

        # Contradiction detection (simple check e.g. safe vs danger words)
        contradictions: List[Dict[str, Any]] = []
        has_safe = "safe" in combined_text or "fine" in combined_text
        has_danger = "danger" in combined_text or "help" in combined_text or "attack" in combined_text
        if has_safe and has_danger:
            contradictions.append({
                "type": "safety_ambivalence",
                "detail": "Caller indicated both safety and danger cues in same conversation",
                "severity": "MEDIUM",
            })

        evidence_refs = [f"turn:{request.turn_id}"]
        if found_locations:
            evidence_refs.append(f"entity:location:{found_locations[0]}")

        result: Dict[str, Any] = {
            "key_facts": key_facts,
            "entities": {
                "locations": found_locations,
                "relations": found_relations,
                "timing": found_timing,
            },
            "unresolved_gaps": unresolved_gaps,
            "contradictions": contradictions,
            "turn_fact_count": len(key_facts),
        }

        latency_ms = (time.perf_counter() - start_time) * 1000
        return self.create_success_response(
            request=request,
            result=result,
            confidence=0.85,
            evidence_refs=evidence_refs,
            latency_ms=latency_ms,
        )
