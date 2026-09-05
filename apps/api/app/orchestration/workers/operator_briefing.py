"""OperatorBriefingAgent: Generates concise, high-density structured summaries for human operators."""

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


class OperatorBriefingAgent(BaseAgentWorker):
    """Summarizer/Formatter agent generating structured operator briefing cards."""

    def __init__(self):
        spec = AgentSpec(
            name="operator_briefing_agent",
            version="1.0.0",
            agent_type=AgentType.SUMMARIZER,
            capabilities=["operator_briefing", "summary_generation", "decision_support"],
            timeout_tier=AgentTimeoutTier.REALTIME_NORMAL,
            max_latency_ms=100,
            safety_classification=AgentSafetyClassification.ADVISORY,
            requires_human_review=True,
            is_realtime_capable=True,
            enabled=True,
        )
        super().__init__(spec)

    async def execute(self, request: AgentRequest) -> AgentResponse:
        start_time = time.perf_counter()
        ctx = request.relevant_context or {}

        # Synthesize from validated contexts or raw signals
        safety_data = ctx.get("safety_info") or ctx.get("safety_context_agent") or {}
        acoustic_data = ctx.get("acoustic_info") or ctx.get("acoustic_context_agent") or {}
        language_data = ctx.get("language_info") or ctx.get("language_context_agent") or {}
        conversation_data = ctx.get("facts") or ctx.get("conversation_context_agent") or {}
        svi_data = ctx.get("svi") or ctx.get("svi_evaluation") or {}
        adaptive_data = ctx.get("adaptive") or ctx.get("adaptive_recommendation") or {}

        # 1. Safety Summary
        safety_state = safety_data.get("safety_state", ctx.get("safety_state", "SAFE"))
        highest_severity = safety_data.get("highest_severity", "NONE")
        triggered_rules = safety_data.get("triggered_rules", [])
        if safety_state in ("CRITICAL", "HIGH_RISK"):
            safety_summary = f"ALERT: Caller state is {safety_state} ({highest_severity} severity). Immediate operator awareness required."
        elif safety_state == "SAFE_WORD_TRIGGERED":
            safety_summary = "CRITICAL: Duress / Safe-word triggered by caller. Discretionary protocol active."
        else:
            safety_summary = f"Safety status {safety_state}. Standard triage protocol in effect."

        # 2. SVI Summary
        svi_score = svi_data.get("svi_score", svi_data.get("score", 0.0))
        svi_tier = svi_data.get("tier", "LOW" if svi_score < 0.4 else "ELEVATED" if svi_score < 0.7 else "CRITICAL")
        svi_summary = f"SVI {svi_score:.2f} ({svi_tier} tier). Contributing indicators: {', '.join(svi_data.get('top_factors', ['baseline']))}."

        # 3. Acoustic Summary
        biomarkers = acoustic_data.get("operational_signals", [])
        snr = acoustic_data.get("snr_db", 0.0)
        distress_score = acoustic_data.get("distress_score", 0.0)
        if biomarkers:
            acoustic_summary = f"Vocal distress signals: {', '.join(biomarkers)} (Distress score: {distress_score:.2f}, SNR: {snr:.1f} dB)."
        else:
            acoustic_summary = f"Acoustic profile stable. SNR {snr:.1f} dB, distress score {distress_score:.2f}."

        # 4. Adaptive Recommendation
        recommended_action = adaptive_data.get("action") or adaptive_data.get("next_step") or "Continue active listening and confirm safety."
        pacing = adaptive_data.get("pacing", "standard")
        adaptive_rec = f"Action: {recommended_action} (Recommended pacing: {pacing})."

        # 5. Key Facts & Knowledge Grounding
        key_facts: List[str] = []
        if isinstance(conversation_data, dict):
            raw_facts = conversation_data.get("key_facts", [])
            if isinstance(raw_facts, list):
                key_facts.extend([str(f) for f in raw_facts[:5]])
        if not key_facts:
            transcript = ctx.get("transcript", "")
            if transcript:
                key_facts.append(f"Recent statement: {transcript[:80]}...")

        # Knowledge Context Integration (Phase 10)
        knowledge_data = ctx.get("knowledge_info") or ctx.get("knowledge_retrieval_agent") or {}
        if isinstance(knowledge_data, dict):
            citations = knowledge_data.get("citations", [])
            if citations and isinstance(citations, list) and len(citations) > 0:
                top_cit = citations[0]
                if isinstance(top_cit, dict):
                    doc_title = top_cit.get("document_title", "Policy Source")
                    sec = top_cit.get("section_page", "Guidance")
                    key_facts.append(f"Authoritative Policy [{doc_title} - {sec}] cited.")

        # Case Intelligence Integration (Phase 11)
        # Case Intelligence Integration (Phase 11)
        case_data = ctx.get("case_info") or ctx.get("case_graph_extraction_agent") or {}
        if isinstance(case_data, dict):
            num_entities = case_data.get("total_entities_extracted", 0)
            num_candidates = case_data.get("total_candidates_proposed", 0)
            if num_entities > 0 or num_candidates > 0:
                key_facts.append(
                    f"Case Intelligence: {num_entities} entities extracted, {num_candidates} relationships pending confirmation."
                )

        # Follow-up Continuity Integration (Phase 12)
        followup_data = ctx.get("followup_info") or ctx.get("followup_recommendation_agent") or {}
        if isinstance(followup_data, dict) and followup_data.get("has_recommendation"):
            sug_type = followup_data.get("suggested_type", "Follow-up")
            sug_prio = followup_data.get("suggested_priority", "NORMAL")
            key_facts.append(
                f"Follow-up Recommendation [{sug_prio}]: {sug_type} suggested for continuity."
            )

        # Evidence references
        evidence_refs: List[str] = [f"turn:{request.turn_id}"]
        if triggered_rules:
            evidence_refs.append("safety:triggered_rules")
        if biomarkers:
            evidence_refs.append("acoustic:biomarkers")
        if isinstance(knowledge_data, dict) and knowledge_data.get("citations"):
            evidence_refs.append("knowledge:citations")
        if isinstance(case_data, dict) and case_data.get("case_id"):
            evidence_refs.append(f"case:{case_data['case_id']}")
        if isinstance(followup_data, dict) and followup_data.get("has_recommendation"):
            evidence_refs.append("followup:recommendation")

        result: Dict[str, Any] = {
            "safety_summary": safety_summary,
            "svi_summary": svi_summary,
            "acoustic_summary": acoustic_summary,
            "adaptive_recommendation": adaptive_rec,
            "key_facts": key_facts,
            "evidence_refs": evidence_refs,
            "confidence": 0.95,
        }

        latency_ms = (time.perf_counter() - start_time) * 1000
        return self.create_success_response(
            request=request,
            result=result,
            confidence=0.95,
            evidence_refs=evidence_refs,
            latency_ms=latency_ms,
        )
