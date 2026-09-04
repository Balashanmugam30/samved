"""Deterministic Information-Gap Planner and Policy Engine (Phase 7).

Computes the bounded next conversational action following strict precedence:
P0 (Critical Safety) > P1 (Elevated Safety) > P2 (High SVI) > P3 (Operational Gaps) > P4 (Clarification/Support) > P5 (Closure).
"""

from datetime import datetime, timezone
import re
from typing import Any, Dict, List, Optional

from app.adaptive.evidence import EvidenceExtractor
from app.adaptive.models import (
    AdaptiveAction,
    AdaptivePlanRequest,
    AdaptivePolicyRuleItem,
    AdaptivePriority,
    AdaptiveReasonCode,
    ConversationFact,
    ConversationStrategy,
    OperatorOverride,
    OperatorOverrideAction,
)


class AdaptivePlanner:
    """Deterministic policy planner selecting next conversational action."""

    VERSION = "v1.0.0"

    @classmethod
    def get_policy_rules(cls) -> List[AdaptivePolicyRuleItem]:
        """Returns full catalog of deterministic policy rules."""
        return [
            AdaptivePolicyRuleItem(
                condition="Operator forced human handoff",
                strategy=AdaptiveAction.HUMAN_HANDOFF,
                priority=AdaptivePriority.P0,
                primary_reason=AdaptiveReasonCode.OPERATOR_REQUESTED_HUMAN,
                description="Operator executed manual warm transfer override.",
            ),
            AdaptivePolicyRuleItem(
                condition="Caller explicitly requests a person/human",
                strategy=AdaptiveAction.HUMAN_HANDOFF,
                priority=AdaptivePriority.P0,
                primary_reason=AdaptiveReasonCode.CALLER_REQUESTED_HUMAN,
                description="Caller asked to speak to a human or officer directly.",
            ),
            AdaptivePolicyRuleItem(
                condition="Critical safety signal reported",
                strategy=AdaptiveAction.SAFETY_CHECK,
                priority=AdaptivePriority.P0,
                primary_reason=AdaptiveReasonCode.CRITICAL_SAFETY_PRIORITY,
                description="Deterministic safety engine flagged immediate danger or weapon.",
            ),
            AdaptivePolicyRuleItem(
                condition="Elevated safety and immediate danger is unknown",
                strategy=AdaptiveAction.ASK_IMMEDIATE_DANGER,
                priority=AdaptivePriority.P1,
                primary_reason=AdaptiveReasonCode.SAFETY_UNKNOWN,
                description="Safety is elevated but immediate active threat is unresolved.",
            ),
            AdaptivePolicyRuleItem(
                condition="Elevated safety and safe to speak is unknown",
                strategy=AdaptiveAction.ASK_SAFE_TO_CONTINUE,
                priority=AdaptivePriority.P1,
                primary_reason=AdaptiveReasonCode.SAFETY_UNKNOWN,
                description="Safety is elevated; verify caller can safely continue speaking.",
            ),
            AdaptivePolicyRuleItem(
                condition="Elevated safety and location is unknown",
                strategy=AdaptiveAction.ASK_LOCATION,
                priority=AdaptivePriority.P1,
                primary_reason=AdaptiveReasonCode.LOCATION_REQUIRED,
                description="Elevated safety requires city or district for operator intervention.",
            ),
            AdaptivePolicyRuleItem(
                condition="High or rising SVI vulnerability score (>= 51)",
                strategy=AdaptiveAction.ASK_SUPPORT,
                priority=AdaptivePriority.P2,
                primary_reason=AdaptiveReasonCode.HIGH_SVI_FOCUS,
                description="Caller exhibits high distress/vulnerability; inquire about nearby trusted support.",
            ),
            AdaptivePolicyRuleItem(
                condition="Repeated ambiguity after 2 attempts",
                strategy=AdaptiveAction.HUMAN_HANDOFF,
                priority=AdaptivePriority.P1,
                primary_reason=AdaptiveReasonCode.REPEATED_AMBIGUITY,
                description="Strategy failed to resolve target information after maximum bounded attempts.",
            ),
            AdaptivePolicyRuleItem(
                condition="Caller explicitly refuses answering question",
                strategy=AdaptiveAction.PAUSE_ADAPTIVE_QUESTIONS,
                priority=AdaptivePriority.P3,
                primary_reason=AdaptiveReasonCode.CALLER_REFUSAL_HONORED,
                description="Honor caller boundary without interrogation or pressure.",
            ),
            AdaptivePolicyRuleItem(
                condition="Severe acoustic degradation or poor line signal",
                strategy=AdaptiveAction.CLARIFY_AUDIO,
                priority=AdaptivePriority.P4,
                primary_reason=AdaptiveReasonCode.AUDIO_QUALITY_DEGRADED,
                description="Acoustic engine reports poor telephony quality or high clipping.",
            ),
            AdaptivePolicyRuleItem(
                condition="Prolonged silence observed (>= 4000ms)",
                strategy=AdaptiveAction.ALLOW_SILENCE,
                priority=AdaptivePriority.P4,
                primary_reason=AdaptiveReasonCode.PROLONGED_SILENCE_HANDLING,
                description="Acoustic engine reports extended pause; provide patient space.",
            ),
            AdaptivePolicyRuleItem(
                condition="Recency timeline information missing",
                strategy=AdaptiveAction.ASK_RECENCY,
                priority=AdaptivePriority.P3,
                primary_reason=AdaptiveReasonCode.RECENCY_UNCLEAR,
                description="Operational gap: determine whether incident is acute or ongoing.",
            ),
            AdaptivePolicyRuleItem(
                condition="Support preference unstated",
                strategy=AdaptiveAction.ASK_PREFERENCE,
                priority=AdaptivePriority.P3,
                primary_reason=AdaptiveReasonCode.CALLER_REQUEST_UNCLEAR,
                description="Operational gap: determine preferred helpline service track.",
            ),
            AdaptivePolicyRuleItem(
                condition="Preferred next step unstated",
                strategy=AdaptiveAction.ASK_NEXT_STEP,
                priority=AdaptivePriority.P3,
                primary_reason=AdaptiveReasonCode.NORMAL_SUPPORT_FLOW,
                description="Operational gap: ask what immediate next step caller envisions.",
            ),
            AdaptivePolicyRuleItem(
                condition="Unclear caller utterance",
                strategy=AdaptiveAction.CLARIFY,
                priority=AdaptivePriority.P4,
                primary_reason=AdaptiveReasonCode.CALLER_REQUEST_UNCLEAR,
                description="General conversational clarification turn.",
            ),
            AdaptivePolicyRuleItem(
                condition="Normal support dialogue",
                strategy=AdaptiveAction.PROVIDE_BRIEF_GUIDANCE,
                priority=AdaptivePriority.P4,
                primary_reason=AdaptiveReasonCode.NORMAL_SUPPORT_FLOW,
                description="Statutory helpline information and empathetic presence.",
            ),
            AdaptivePolicyRuleItem(
                condition="All critical information resolved and caller closing",
                strategy=AdaptiveAction.END_GRACEFULLY,
                priority=AdaptivePriority.P5,
                primary_reason=AdaptiveReasonCode.CLOSURE_READY,
                description="No active safety concerns, caller expresses satisfaction or goodbye.",
            ),
        ]

    @classmethod
    def plan_strategy(
        cls,
        call_id: str,
        session_id: str,
        turn_index: int,
        language: str,
        safety_state: str,
        safety_signals: List[Dict[str, Any]],
        svi_score: int,
        svi_band: str,
        svi_trend: str,
        acoustic_quality: str,
        acoustic_signals: List[Dict[str, Any]],
        known_facts: Dict[str, Any],
        last_caller_utterance: str,
        strategy_attempt_counts: Optional[Dict[str, int]] = None,
        active_override: Optional[OperatorOverride] = None,
    ) -> ConversationStrategy:
        """Deterministically evaluates conversation state and returns next strategy."""
        attempt_counts = strategy_attempt_counts or {}
        now_iso = datetime.now(timezone.utc).isoformat()
        clean_utterance = last_caller_utterance.strip().lower()

        # Extract caller explicit intents
        intents = EvidenceExtractor.extract_caller_intent(last_caller_utterance)

        # -------------------------------------------------------------
        # STEP 1: Operator Overrides (Highest Authority)
        # -------------------------------------------------------------
        if active_override and active_override.is_active:
            if active_override.action == OperatorOverrideAction.FORCE_HUMAN:
                return ConversationStrategy(
                    call_id=call_id,
                    session_id=session_id,
                    turn_index=turn_index,
                    action=AdaptiveAction.HUMAN_HANDOFF,
                    priority=AdaptivePriority.P0,
                    target_information="human_handoff",
                    reason_codes=[AdaptiveReasonCode.OPERATOR_REQUESTED_HUMAN, AdaptiveReasonCode.OPERATOR_OVERRIDE_ACTIVE],
                    evidence_refs=[f"operator_override={active_override.reason}"],
                    language=language,
                    requires_human_review=True,
                    operator_override_active=True,
                    evaluated_at=now_iso,
                )
            elif active_override.action == OperatorOverrideAction.PAUSE_ADAPTIVE:
                return ConversationStrategy(
                    call_id=call_id,
                    session_id=session_id,
                    turn_index=turn_index,
                    action=AdaptiveAction.PAUSE_ADAPTIVE_QUESTIONS,
                    priority=AdaptivePriority.P1,
                    target_information="pause",
                    reason_codes=[AdaptiveReasonCode.OPERATOR_OVERRIDE_ACTIVE],
                    evidence_refs=[f"operator_override={active_override.reason}"],
                    language=language,
                    operator_override_active=True,
                    evaluated_at=now_iso,
                )
            elif active_override.action == OperatorOverrideAction.REQUEST_SAFETY_CHECK:
                return ConversationStrategy(
                    call_id=call_id,
                    session_id=session_id,
                    turn_index=turn_index,
                    action=AdaptiveAction.SAFETY_CHECK,
                    priority=AdaptivePriority.P0,
                    target_information="physical_safety",
                    reason_codes=[AdaptiveReasonCode.OPERATOR_OVERRIDE_ACTIVE, AdaptiveReasonCode.CRITICAL_SAFETY_PRIORITY],
                    evidence_refs=[f"operator_override={active_override.reason}"],
                    language=language,
                    requires_human_review=True,
                    operator_override_active=True,
                    evaluated_at=now_iso,
                )
            elif active_override.action == OperatorOverrideAction.END_SESSION:
                return ConversationStrategy(
                    call_id=call_id,
                    session_id=session_id,
                    turn_index=turn_index,
                    action=AdaptiveAction.END_GRACEFULLY,
                    priority=AdaptivePriority.P5,
                    target_information="call_closure",
                    reason_codes=[AdaptiveReasonCode.OPERATOR_OVERRIDE_ACTIVE, AdaptiveReasonCode.CLOSURE_READY],
                    evidence_refs=[f"operator_override={active_override.reason}"],
                    language=language,
                    operator_override_active=True,
                    evaluated_at=now_iso,
                )

        # -------------------------------------------------------------
        # STEP 2: Caller Explicit Intent (Human Request / Refusal)
        # -------------------------------------------------------------
        if intents["requests_human"] or known_facts.get("requests_human") is True:
            return ConversationStrategy(
                call_id=call_id,
                session_id=session_id,
                turn_index=turn_index,
                action=AdaptiveAction.HUMAN_HANDOFF,
                priority=AdaptivePriority.P0,
                target_information="human_handoff",
                reason_codes=[AdaptiveReasonCode.CALLER_REQUESTED_HUMAN],
                evidence_refs=["caller_explicit_human_request=True"],
                language=language,
                requires_human_review=True,
                evaluated_at=now_iso,
            )

        if intents["refuses_question"] or known_facts.get("caller_refusal") is True:
            return ConversationStrategy(
                call_id=call_id,
                session_id=session_id,
                turn_index=turn_index,
                action=AdaptiveAction.PAUSE_ADAPTIVE_QUESTIONS,
                priority=AdaptivePriority.P3,
                target_information="boundary_acknowledgment",
                reason_codes=[AdaptiveReasonCode.CALLER_REFUSAL_HONORED],
                evidence_refs=["caller_refusal_observed=True"],
                language=language,
                constraints=["do_not_re-ask_refused_item"],
                evaluated_at=now_iso,
            )

        # -------------------------------------------------------------
        # STEP 3: Repeated Ambiguity / Failure Bound
        # -------------------------------------------------------------
        # If any strategy has been attempted >= 2 times with low progress, transition to human handoff
        clarify_attempts = attempt_counts.get(AdaptiveAction.CLARIFY.value, 0)
        audio_clarify_attempts = attempt_counts.get(AdaptiveAction.CLARIFY_AUDIO.value, 0)
        if clarify_attempts >= 2 or audio_clarify_attempts >= 2:
            return ConversationStrategy(
                call_id=call_id,
                session_id=session_id,
                turn_index=turn_index,
                action=AdaptiveAction.HUMAN_HANDOFF,
                priority=AdaptivePriority.P1,
                target_information="human_handoff",
                reason_codes=[AdaptiveReasonCode.REPEATED_AMBIGUITY],
                evidence_refs=[f"attempts_exceeded: clarify={clarify_attempts}, audio={audio_clarify_attempts}"],
                language=language,
                requires_human_review=True,
                evaluated_at=now_iso,
            )

        # -------------------------------------------------------------
        # STEP 4: P0 — Critical Immediate Safety Precedence
        # -------------------------------------------------------------
        has_critical_signal = any(
            s.get("severity") == "CRITICAL"
            for s in safety_signals
        )
        is_safety_critical = safety_state == "CRITICAL" or has_critical_signal

        if is_safety_critical:
            immediate_danger_known = "immediate_danger" in known_facts
            if not immediate_danger_known:
                return ConversationStrategy(
                    call_id=call_id,
                    session_id=session_id,
                    turn_index=turn_index,
                    action=AdaptiveAction.ASK_IMMEDIATE_DANGER,
                    priority=AdaptivePriority.P0,
                    target_information="immediate_danger",
                    reason_codes=[AdaptiveReasonCode.CRITICAL_SAFETY_PRIORITY, AdaptiveReasonCode.SAFETY_UNKNOWN],
                    evidence_refs=[f"safety_state={safety_state}", "immediate_danger=UNKNOWN"],
                    language=language,
                    requires_human_review=True,
                    constraints=["one_concise_question", "no_delay"],
                    evaluated_at=now_iso,
                )
            else:
                return ConversationStrategy(
                    call_id=call_id,
                    session_id=session_id,
                    turn_index=turn_index,
                    action=AdaptiveAction.SAFETY_CHECK,
                    priority=AdaptivePriority.P0,
                    target_information="physical_safety",
                    reason_codes=[AdaptiveReasonCode.CRITICAL_SAFETY_PRIORITY],
                    evidence_refs=[f"safety_state={safety_state}", f"immediate_danger={known_facts.get('immediate_danger')}"],
                    language=language,
                    requires_human_review=True,
                    constraints=["calm_grounding", "safety_first"],
                    evaluated_at=now_iso,
                )

        # -------------------------------------------------------------
        # STEP 5: P1 — Elevated Safety / Safety Uncertainty
        # -------------------------------------------------------------
        if safety_state in ("ELEVATED", "HIGH", "WATCH"):
            if "immediate_danger" not in known_facts:
                return ConversationStrategy(
                    call_id=call_id,
                    session_id=session_id,
                    turn_index=turn_index,
                    action=AdaptiveAction.ASK_IMMEDIATE_DANGER,
                    priority=AdaptivePriority.P1,
                    target_information="immediate_danger",
                    reason_codes=[AdaptiveReasonCode.SAFETY_UNKNOWN],
                    evidence_refs=[f"safety_state={safety_state}", "immediate_danger=UNKNOWN"],
                    language=language,
                    requires_human_review=True,
                    constraints=["one_question_only"],
                    evaluated_at=now_iso,
                )
            if "safe_now" not in known_facts:
                return ConversationStrategy(
                    call_id=call_id,
                    session_id=session_id,
                    turn_index=turn_index,
                    action=AdaptiveAction.ASK_SAFE_TO_CONTINUE,
                    priority=AdaptivePriority.P1,
                    target_information="safe_to_continue",
                    reason_codes=[AdaptiveReasonCode.SAFETY_UNKNOWN],
                    evidence_refs=[f"safety_state={safety_state}", "safe_now=UNKNOWN"],
                    language=language,
                    requires_human_review=True,
                    constraints=["one_question_only"],
                    evaluated_at=now_iso,
                )
            if "location" not in known_facts:
                return ConversationStrategy(
                    call_id=call_id,
                    session_id=session_id,
                    turn_index=turn_index,
                    action=AdaptiveAction.ASK_LOCATION,
                    priority=AdaptivePriority.P1,
                    target_information="location",
                    reason_codes=[AdaptiveReasonCode.LOCATION_REQUIRED],
                    evidence_refs=[f"safety_state={safety_state}", "location=UNKNOWN"],
                    language=language,
                    requires_human_review=True,
                    constraints=["general_city_only"],
                    evaluated_at=now_iso,
                )

        # -------------------------------------------------------------
        # STEP 6: Supportive Acoustic Degradation Check
        # -------------------------------------------------------------
        # Poor audio or high clipping triggers clarify_audio
        has_degraded_acoustic = (
            acoustic_quality in ("POOR", "DEGRADED")
            or any(s.get("code") in ("AUDIO_QUALITY_DEGRADED", "AUDIO_QUALITY_LOW") for s in acoustic_signals)
        )
        if has_degraded_acoustic and audio_clarify_attempts < 2:
            return ConversationStrategy(
                call_id=call_id,
                session_id=session_id,
                turn_index=turn_index,
                action=AdaptiveAction.CLARIFY_AUDIO,
                priority=AdaptivePriority.P4,
                target_information="audio_repetition",
                reason_codes=[AdaptiveReasonCode.AUDIO_QUALITY_DEGRADED],
                evidence_refs=[f"acoustic_quality={acoustic_quality}"],
                language=language,
                constraints=["polite_repetition_request"],
                evaluated_at=now_iso,
            )

        # Prolonged silence
        has_prolonged_silence = any(s.get("code") == "PROLONGED_SILENCE_OBSERVED" for s in acoustic_signals)
        if has_prolonged_silence and not clean_utterance:
            return ConversationStrategy(
                call_id=call_id,
                session_id=session_id,
                turn_index=turn_index,
                action=AdaptiveAction.ALLOW_SILENCE,
                priority=AdaptivePriority.P4,
                target_information="pause_space",
                reason_codes=[AdaptiveReasonCode.PROLONGED_SILENCE_HANDLING],
                evidence_refs=["prolonged_silence_observed=True"],
                language=language,
                constraints=["no_pressure", "patient"],
                evaluated_at=now_iso,
            )

        # -------------------------------------------------------------
        # STEP 7: P2 — High SVI / Severe Vulnerability
        # -------------------------------------------------------------
        if svi_band in ("HIGH", "CRITICAL") or svi_score >= 51 or svi_trend == "RISING":
            if "support_person" not in known_facts:
                return ConversationStrategy(
                    call_id=call_id,
                    session_id=session_id,
                    turn_index=turn_index,
                    action=AdaptiveAction.ASK_SUPPORT,
                    priority=AdaptivePriority.P2,
                    target_information="support_person",
                    reason_codes=[
                        AdaptiveReasonCode.HIGH_SVI_FOCUS,
                        AdaptiveReasonCode.SUPPORT_CONTEXT_MISSING,
                    ],
                    evidence_refs=[f"svi_score={svi_score}", f"svi_band={svi_band}", "support_person=UNKNOWN"],
                    language=language,
                    constraints=["gentle_tone", "reduce_cognitive_burden"],
                    evaluated_at=now_iso,
                )
            else:
                return ConversationStrategy(
                    call_id=call_id,
                    session_id=session_id,
                    turn_index=turn_index,
                    action=AdaptiveAction.OFFER_OPTIONS,
                    priority=AdaptivePriority.P2,
                    target_information="preferred_support_track",
                    reason_codes=[AdaptiveReasonCode.HIGH_SVI_FOCUS],
                    evidence_refs=[f"svi_score={svi_score}", f"svi_band={svi_band}"],
                    language=language,
                    constraints=["structured_options", "calm"],
                    evaluated_at=now_iso,
                )

        # -------------------------------------------------------------
        # STEP 8: P5 — Closure Check
        # -------------------------------------------------------------
        # If caller indicates intent to finish and safety is NONE:
        is_closing_intent = any(
            w in clean_utterance
            for w in [
                "thank you", "thanks", "bye", "goodbye", "that is all", "that helps", "okay bye",
                "நன்றி", "போதும்", "வரேன்", "धन्यवाद", "अलविदा", "ठीक है बस", "बहुत मदद मिली"
            ]
        )
        if is_closing_intent and safety_state == "NONE":
            return ConversationStrategy(
                call_id=call_id,
                session_id=session_id,
                turn_index=turn_index,
                action=AdaptiveAction.END_GRACEFULLY,
                priority=AdaptivePriority.P5,
                target_information="call_closure",
                reason_codes=[AdaptiveReasonCode.CLOSURE_READY],
                evidence_refs=["caller_closure_intent=True", "safety_state=NONE"],
                language=language,
                constraints=["courteous_closing", "no_false_promises"],
                evaluated_at=now_iso,
            )

        # -------------------------------------------------------------
        # STEP 9: P3 — Operational Information Gaps
        # -------------------------------------------------------------
        if "recency" not in known_facts:
            return ConversationStrategy(
                call_id=call_id,
                session_id=session_id,
                turn_index=turn_index,
                action=AdaptiveAction.ASK_RECENCY,
                priority=AdaptivePriority.P3,
                target_information="recency",
                reason_codes=[AdaptiveReasonCode.RECENCY_UNCLEAR],
                evidence_refs=["recency=UNKNOWN"],
                language=language,
                constraints=["one_question_only"],
                evaluated_at=now_iso,
            )

        if "preference" not in known_facts:
            return ConversationStrategy(
                call_id=call_id,
                session_id=session_id,
                turn_index=turn_index,
                action=AdaptiveAction.ASK_PREFERENCE,
                priority=AdaptivePriority.P3,
                target_information="preference",
                reason_codes=[AdaptiveReasonCode.CALLER_REQUEST_UNCLEAR],
                evidence_refs=["preference=UNKNOWN"],
                language=language,
                constraints=["one_question_only"],
                evaluated_at=now_iso,
            )

        if "next_step" not in known_facts:
            return ConversationStrategy(
                call_id=call_id,
                session_id=session_id,
                turn_index=turn_index,
                action=AdaptiveAction.ASK_NEXT_STEP,
                priority=AdaptivePriority.P3,
                target_information="next_step",
                reason_codes=[AdaptiveReasonCode.NORMAL_SUPPORT_FLOW],
                evidence_refs=["next_step=UNKNOWN"],
                language=language,
                constraints=["one_question_only"],
                evaluated_at=now_iso,
            )

        # -------------------------------------------------------------
        # STEP 10: P4 — General Clarification / Guidance Fallback
        # -------------------------------------------------------------
        if len(clean_utterance.split()) <= 2 and clean_utterance not in ("yes", "no", "ஆம்", "இல்லை", "हाँ", "नहीं"):
            return ConversationStrategy(
                call_id=call_id,
                session_id=session_id,
                turn_index=turn_index,
                action=AdaptiveAction.CLARIFY,
                priority=AdaptivePriority.P4,
                target_information="caller_context",
                reason_codes=[AdaptiveReasonCode.CALLER_REQUEST_UNCLEAR],
                evidence_refs=["short_unclear_utterance"],
                language=language,
                constraints=["open_ended"],
                evaluated_at=now_iso,
            )

        return ConversationStrategy(
            call_id=call_id,
            session_id=session_id,
            turn_index=turn_index,
            action=AdaptiveAction.PROVIDE_BRIEF_GUIDANCE,
            priority=AdaptivePriority.P4,
            target_information="statutory_guidance",
            reason_codes=[AdaptiveReasonCode.NORMAL_SUPPORT_FLOW],
            evidence_refs=["standard_flow"],
            language=language,
            constraints=["statutory_14566_info"],
            evaluated_at=now_iso,
        )

    @classmethod
    def evaluate_request(cls, req: AdaptivePlanRequest) -> ConversationStrategy:
        """Convenience method to evaluate a standalone AdaptivePlanRequest."""
        override = None
        if req.override_action:
            try:
                act = OperatorOverrideAction(req.override_action)
                override = OperatorOverride(
                    action=act,
                    reason=f"Simulation override: {req.override_action}",
                )
            except Exception:
                pass

        return cls.plan_strategy(
            call_id=req.call_id,
            session_id=req.session_id,
            turn_index=req.turn_index,
            language=req.language,
            safety_state=req.safety_state,
            safety_signals=req.safety_signals,
            svi_score=req.svi_score,
            svi_band=req.svi_band,
            svi_trend=req.svi_trend,
            acoustic_quality=req.acoustic_quality,
            acoustic_signals=req.acoustic_signals,
            known_facts=req.known_facts,
            last_caller_utterance=req.last_caller_utterance,
            active_override=override,
        )
