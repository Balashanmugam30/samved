"""Adaptive Conversation Engine Service (Phase 7).

Coordinates session state, evidence aggregation, information-gap planning,
operator overrides, and strategy history persistence.
"""

from collections import defaultdict
from datetime import datetime, timezone
import logging
from typing import Any, Dict, List, Optional

from app.adaptive.evidence import EvidenceExtractor
from app.adaptive.models import (
    AdaptiveAction,
    AdaptiveHistoryResponse,
    AdaptivePolicyResponse,
    AdaptivePriority,
    AdaptiveReasonCode,
    AdaptiveStatusResponse,
    ConversationFact,
    ConversationStrategy,
    OperatorOverride,
    OperatorOverrideAction,
)
from app.adaptive.planner import AdaptivePlanner

logger = logging.getLogger("samved.adaptive.engine")


class AdaptiveEngine:
    """Singleton service for adaptive conversation orchestration."""

    def __init__(self):
        # session_id -> { "facts": Dict[str, ConversationFact], "attempt_counts": Dict[str, int] }
        self._session_states: Dict[str, Dict[str, Any]] = defaultdict(lambda: {
            "facts": {},
            "attempt_counts": defaultdict(int),
        })
        # call_id -> List[ConversationStrategy]
        self._call_strategies: Dict[str, List[ConversationStrategy]] = defaultdict(list)
        # call_id -> OperatorOverride
        self._active_overrides: Dict[str, OperatorOverride] = {}

    def get_status(self) -> AdaptiveStatusResponse:
        """Returns engine operational status and ethical guardrails."""
        return AdaptiveStatusResponse(
            status="ready",
            engine_version=AdaptivePlanner.VERSION,
            is_operational_planning_only=True,
            safety_precedence_inviolable=True,
            active_policies_count=len(AdaptivePlanner.get_policy_rules()),
            supported_languages=["ta-IN", "hi-IN", "en-IN"],
            disclaimer=(
                "Adaptive Conversation is an operational conversational planning layer. It is not a clinical, "
                "medical, diagnostic, legal, credibility, lie-detection, or autonomous emergency-dispatch system."
            ),
        )

    def get_policy_catalog(self) -> AdaptivePolicyResponse:
        """Returns the full rule catalog of conversational strategies."""
        rules = AdaptivePlanner.get_policy_rules()
        return AdaptivePolicyResponse(
            engine_version=AdaptivePlanner.VERSION,
            policy_rules=rules,
            total_actions=len(AdaptiveAction),
            actions=[a.value for a in AdaptiveAction],
        )

    def apply_operator_override(
        self,
        call_id: str,
        action: OperatorOverrideAction,
        reason: str,
        operator_id: str = "operator_1",
    ) -> OperatorOverride:
        """Applies a manual human operator override to an active call."""
        override = OperatorOverride(
            action=action,
            reason=reason,
            operator_id=operator_id,
            applied_at=datetime.now(timezone.utc).isoformat(),
            is_active=True,
        )
        self._active_overrides[call_id] = override
        logger.info(f"Operator override applied to call {call_id}: {action.value} ({reason})")
        return override

    def clear_operator_override(self, call_id: str) -> None:
        """Clears any active operator override for a call."""
        self._active_overrides.pop(call_id, None)

    def get_operator_override(self, call_id: str) -> Optional[OperatorOverride]:
        """Retrieves active operator override for a call if present."""
        return self._active_overrides.get(call_id)

    def evaluate_turn(
        self,
        call_id: str,
        session_id: str,
        turn_index: int,
        utterance_text: str,
        language: str = "en-IN",
        safety_assessment: Optional[Any] = None,
        svi_assessment: Optional[Any] = None,
        acoustic_assessment: Optional[Any] = None,
    ) -> ConversationStrategy:
        """Evaluates conversation turn and produces next deterministic strategy."""
        session_data = self._session_states[session_id]
        facts_map: Dict[str, ConversationFact] = session_data["facts"]
        attempt_counts: Dict[str, int] = session_data["attempt_counts"]

        # 1. Extract new facts and detect contradictions from caller utterance
        new_facts, contradiction_detected = EvidenceExtractor.extract_facts_from_turn(
            text=utterance_text,
            turn_id=f"turn-{turn_index}",
            turn_index=turn_index,
            existing_facts=facts_map,
        )
        for f in new_facts:
            facts_map[f.key] = f

        # Format simple key-value dict of non-superseded facts for planner
        known_facts_dict = {
            k: v.value for k, v in facts_map.items() if not v.superseded
        }

        # 2. Extract Safety state & signals
        safety_state = "NONE"
        safety_signals_list: List[Dict[str, Any]] = []
        if safety_assessment:
            if hasattr(safety_assessment, "current_state"):
                safety_state = (
                    safety_assessment.current_state.value
                    if hasattr(safety_assessment.current_state, "value")
                    else str(safety_assessment.current_state)
                )
            if hasattr(safety_assessment, "signals"):
                for sig in safety_assessment.signals:
                    sig_dict = {
                        "severity": sig.severity.value if hasattr(sig.severity, "value") else str(sig.severity),
                        "signal_type": sig.signal_type.value if hasattr(sig.signal_type, "value") else str(sig.signal_type),
                        "reason": sig.evidence.reason if hasattr(sig, "evidence") else "",
                    }
                    safety_signals_list.append(sig_dict)

        # 3. Extract SVI state
        svi_score = 20
        svi_band = "LOW"
        svi_trend = "INITIAL"
        if svi_assessment:
            svi_score = getattr(svi_assessment, "score", 20)
            if hasattr(svi_assessment, "band"):
                svi_band = (
                    svi_assessment.band.value
                    if hasattr(svi_assessment.band, "value")
                    else str(svi_assessment.band)
                )
            if hasattr(svi_assessment, "trend"):
                svi_trend = (
                    svi_assessment.trend.value
                    if hasattr(svi_assessment.trend, "value")
                    else str(svi_assessment.trend)
                )

        # 4. Extract Acoustic state
        acoustic_quality = "GOOD"
        acoustic_signals_list: List[Dict[str, Any]] = []
        if acoustic_assessment:
            if hasattr(acoustic_assessment, "quality"):
                acoustic_quality = (
                    acoustic_assessment.quality.value
                    if hasattr(acoustic_assessment.quality, "value")
                    else str(acoustic_assessment.quality)
                )
            if hasattr(acoustic_assessment, "operational_signals"):
                for sig in acoustic_assessment.operational_signals:
                    sig_dict = {
                        "code": sig.code.value if hasattr(sig.code, "value") else str(sig.code),
                        "evidence": getattr(sig, "evidence", ""),
                    }
                    acoustic_signals_list.append(sig_dict)

        # 5. Get active override if any
        active_override = self._active_overrides.get(call_id)

        # 6. Execute Deterministic Planning
        strategy = AdaptivePlanner.plan_strategy(
            call_id=call_id,
            session_id=session_id,
            turn_index=turn_index,
            language=language,
            safety_state=safety_state,
            safety_signals=safety_signals_list,
            svi_score=svi_score,
            svi_band=svi_band,
            svi_trend=svi_trend,
            acoustic_quality=acoustic_quality,
            acoustic_signals=acoustic_signals_list,
            known_facts=known_facts_dict,
            last_caller_utterance=utterance_text,
            strategy_attempt_counts=dict(attempt_counts),
            active_override=active_override,
        )

        # If contradiction was resolved in this turn, append reason code
        if contradiction_detected and AdaptiveReasonCode.CONTRADICTION_RESOLVED not in strategy.reason_codes:
            strategy.reason_codes.append(AdaptiveReasonCode.CONTRADICTION_RESOLVED)
            strategy.evidence_refs.append("contradiction_resolved_with_new_evidence")

        # Increment attempt count for chosen action
        attempt_counts[strategy.action.value] += 1

        # Persist strategy in bounded call history
        self._call_strategies[call_id].append(strategy)

        return strategy

    def get_latest_strategy(self, call_id: str) -> Optional[ConversationStrategy]:
        """Returns latest planned strategy for a call."""
        history = self._call_strategies.get(call_id, [])
        return history[-1] if history else None

    def get_call_history(self, call_id: str) -> AdaptiveHistoryResponse:
        """Returns turn-by-turn strategy history for a call."""
        strategies = self._call_strategies.get(call_id, [])
        override = self._active_overrides.get(call_id)
        return AdaptiveHistoryResponse(
            call_id=call_id,
            total_strategies=len(strategies),
            strategies=strategies,
            active_override=override,
        )

    def reset(self) -> None:
        """Clears all session states, strategies, and overrides (for test isolation)."""
        self._session_states.clear()
        self._call_strategies.clear()
        self._active_overrides.clear()


# Global singleton instance
adaptive_engine = AdaptiveEngine()
