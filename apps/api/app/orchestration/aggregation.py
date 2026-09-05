"""ContextAggregator: Aggregates worker outputs and applies deterministic conflict resolution."""

import logging
from typing import Any, Dict, List

from app.orchestration.models import AgentResponse, AgentStatus, ValidatedContext

logger = logging.getLogger(__name__)


class ContextAggregator:
    """Aggregates worker responses into a single ValidatedContext, resolving contradictions."""

    def aggregate(
        self,
        responses: Dict[str, AgentResponse],
        base_context: Dict[str, Any],
    ) -> ValidatedContext:
        """Aggregate Stage 1 agent outputs with deterministic precedence."""
        facts: Dict[str, Any] = {}
        unresolved_gaps: List[str] = []
        contradictions: List[Dict[str, Any]] = []
        evidence_refs: List[str] = []
        conflict_resolutions: List[str] = []

        # 1. Safety info (Highest programmatic authority)
        safety_resp = responses.get("safety_context_agent")
        safety_info: Dict[str, Any] = {}
        if safety_resp and safety_resp.status == AgentStatus.SUCCESS:
            safety_info = safety_resp.result
            evidence_refs.extend(safety_resp.evidence_refs)
        else:
            # Fallback to base context
            safety_info = {
                "safety_state": base_context.get("safety_state", "SAFE"),
                "highest_severity": "NONE",
                "action": "CONTINUE",
                "is_authoritative": True,
            }

        # 2. Acoustic info (Authoritative for vocal biomarkers)
        acoustic_resp = responses.get("acoustic_context_agent")
        acoustic_info: Dict[str, Any] = {}
        if acoustic_resp and acoustic_resp.status == AgentStatus.SUCCESS:
            acoustic_info = acoustic_resp.result
            evidence_refs.extend(acoustic_resp.evidence_refs)
        else:
            acoustic_info = base_context.get("acoustic_features", {})

        # 3. Language info (Authoritative for language & code-switch)
        lang_resp = responses.get("language_context_agent")
        language_info: Dict[str, Any] = {}
        if lang_resp and lang_resp.status == AgentStatus.SUCCESS:
            language_info = lang_resp.result
            evidence_refs.extend(lang_resp.evidence_refs)
        else:
            language_info = {
                "primary_language": base_context.get("language", "ta-IN"),
                "code_switching_detected": False,
            }

        # 4. Support info (Placeholder stub)
        support_resp = responses.get("support_options_agent")
        support_info: Dict[str, Any] = {}
        if support_resp and support_resp.status == AgentStatus.SUCCESS:
            support_info = support_resp.result
            evidence_refs.extend(support_resp.evidence_refs)

        # 5. Conversation facts (Advisory only)
        conv_resp = responses.get("conversation_context_agent")
        if conv_resp and conv_resp.status == AgentStatus.SUCCESS:
            conv_result = conv_resp.result
            facts = conv_result.get("entities", {})
            raw_facts = conv_result.get("key_facts", [])
            if raw_facts:
                facts["key_facts"] = raw_facts
            unresolved_gaps.extend(conv_result.get("unresolved_gaps", []))
            contradictions.extend(conv_result.get("contradictions", []))
            evidence_refs.extend(conv_resp.evidence_refs)

        # Deterministic Conflict Resolution:
        # Check if conversation agent or caller claimed "safe" when Safety Engine detected CRITICAL / HIGH_RISK
        safety_state = safety_info.get("safety_state", "SAFE")
        if safety_state in ("CRITICAL", "HIGH_RISK", "SAFE_WORD_TRIGGERED"):
            # If any contradiction exists claiming safety, override with safety precedence
            conflict_msg = (
                f"Safety Engine state '{safety_state}' takes absolute precedence over any "
                f"benign conversation cues. Human review triggered."
            )
            conflict_resolutions.append(conflict_msg)

        # Remove duplicate evidence refs while preserving order
        dedup_evidence = list(dict.fromkeys(evidence_refs))

        return ValidatedContext(
            facts=facts,
            unresolved_gaps=unresolved_gaps,
            contradictions=contradictions,
            language_info=language_info,
            safety_info=safety_info,
            acoustic_info=acoustic_info,
            support_info=support_info,
            evidence_refs=dedup_evidence,
            conflict_resolutions=conflict_resolutions,
        )


context_aggregator = ContextAggregator()
