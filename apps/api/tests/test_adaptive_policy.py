"""Unit tests for Phase 7 Adaptive Conversation Policy & Determinism."""

import time
from app.adaptive.models import (
    AdaptiveAction,
    AdaptivePlanRequest,
    AdaptivePriority,
    AdaptiveReasonCode,
    ConversationFact,
    FactPriority,
    OperatorOverride,
    OperatorOverrideAction,
)
from app.adaptive.planner import AdaptivePlanner
from app.adaptive.service import AdaptiveEngine


def test_policy_precedence_p0_critical_safety():
    """P0 Critical safety signals mandate SAFETY_CHECK or ASK_IMMEDIATE_DANGER regardless of SVI or audio."""
    # Critical safety + unknown immediate danger -> ASK_IMMEDIATE_DANGER (P0)
    strat1 = AdaptivePlanner.plan_strategy(
        call_id="call-p0-1",
        session_id="sess-p0-1",
        turn_index=1,
        language="en-IN",
        safety_state="CRITICAL",
        safety_signals=[{"severity": "CRITICAL", "signal_type": "ACTIVE_VIOLENCE"}],
        svi_score=85,
        svi_band="CRITICAL",
        svi_trend="RISING",
        acoustic_quality="POOR",  # Even if audio is poor, safety is P0!
        acoustic_signals=[],
        known_facts={},
        last_caller_utterance="He is hitting me with a stick!",
    )
    assert strat1.action == AdaptiveAction.ASK_IMMEDIATE_DANGER
    assert strat1.priority == AdaptivePriority.P0
    assert AdaptiveReasonCode.CRITICAL_SAFETY_PRIORITY in strat1.reason_codes

    # Critical safety + known immediate danger -> SAFETY_CHECK (P0)
    strat2 = AdaptivePlanner.plan_strategy(
        call_id="call-p0-2",
        session_id="sess-p0-2",
        turn_index=2,
        language="en-IN",
        safety_state="CRITICAL",
        safety_signals=[{"severity": "CRITICAL", "signal_type": "ACTIVE_VIOLENCE"}],
        svi_score=85,
        svi_band="CRITICAL",
        svi_trend="RISING",
        acoustic_quality="GOOD",
        acoustic_signals=[],
        known_facts={"immediate_danger": True},
        last_caller_utterance="Yes, I am in danger right now.",
    )
    assert strat2.action == AdaptiveAction.SAFETY_CHECK
    assert strat2.priority == AdaptivePriority.P0


def test_policy_precedence_p1_elevated_safety():
    """P1 Elevated safety prompts focused safety clarification (immediate danger -> safe to continue -> location)."""
    # 1. Missing immediate danger
    strat1 = AdaptivePlanner.plan_strategy(
        call_id="call-p1-1",
        session_id="sess-p1-1",
        turn_index=1,
        language="ta-IN",
        safety_state="ELEVATED",
        safety_signals=[{"severity": "HIGH", "signal_type": "ONGOING_THREAT"}],
        svi_score=60,
        svi_band="HIGH",
        svi_trend="INITIAL",
        acoustic_quality="GOOD",
        acoustic_signals=[],
        known_facts={},
        last_caller_utterance="Romba bayama irukku.",
    )
    assert strat1.action == AdaptiveAction.ASK_IMMEDIATE_DANGER
    assert strat1.priority == AdaptivePriority.P1

    # 2. Known immediate danger, missing safe_now
    strat2 = AdaptivePlanner.plan_strategy(
        call_id="call-p1-2",
        session_id="sess-p1-2",
        turn_index=2,
        language="ta-IN",
        safety_state="ELEVATED",
        safety_signals=[],
        svi_score=60,
        svi_band="HIGH",
        svi_trend="INITIAL",
        acoustic_quality="GOOD",
        acoustic_signals=[],
        known_facts={"immediate_danger": False},
        last_caller_utterance="No immediate danger.",
    )
    assert strat2.action == AdaptiveAction.ASK_SAFE_TO_CONTINUE
    assert strat2.priority == AdaptivePriority.P1

    # 3. Known immediate danger & safe_now, missing location
    strat3 = AdaptivePlanner.plan_strategy(
        call_id="call-p1-3",
        session_id="sess-p1-3",
        turn_index=3,
        language="ta-IN",
        safety_state="ELEVATED",
        safety_signals=[],
        svi_score=60,
        svi_band="HIGH",
        svi_trend="INITIAL",
        acoustic_quality="GOOD",
        acoustic_signals=[],
        known_facts={"immediate_danger": False, "safe_now": True},
        last_caller_utterance="I can talk privately.",
    )
    assert strat3.action == AdaptiveAction.ASK_LOCATION
    assert strat3.priority == AdaptivePriority.P1


def test_policy_precedence_p2_high_svi():
    """P2 High SVI without critical threat reduces burden and asks for support or offers options."""
    strat = AdaptivePlanner.plan_strategy(
        call_id="call-p2-1",
        session_id="sess-p2-1",
        turn_index=1,
        language="en-IN",
        safety_state="NONE",
        safety_signals=[],
        svi_score=68,
        svi_band="HIGH",
        svi_trend="RISING",
        acoustic_quality="GOOD",
        acoustic_signals=[],
        known_facts={},
        last_caller_utterance="I feel so overwhelmed and I cannot sleep.",
    )
    assert strat.action == AdaptiveAction.ASK_SUPPORT
    assert strat.priority == AdaptivePriority.P2
    assert AdaptiveReasonCode.HIGH_SVI_FOCUS in strat.reason_codes


def test_determinism_reproducibility():
    """Same state + same input history = exactly identical strategy and reason codes."""
    req = AdaptivePlanRequest(
        call_id="call-det-1",
        session_id="sess-det-1",
        turn_index=2,
        language="hi-IN",
        safety_state="NONE",
        safety_signals=[],
        svi_score=35,
        svi_band="MODERATE",
        svi_trend="STABLE",
        acoustic_quality="GOOD",
        acoustic_signals=[],
        known_facts={"recency": "today"},
        last_caller_utterance="मुझे मदद चाहिए।",
    )

    strat1 = AdaptivePlanner.evaluate_request(req)
    strat2 = AdaptivePlanner.evaluate_request(req)

    assert strat1.action == strat2.action
    assert strat1.priority == strat2.priority
    assert strat1.target_information == strat2.target_information
    assert [r.value for r in strat1.reason_codes] == [r.value for r in strat2.reason_codes]
    assert strat1.confidence == strat2.confidence


def test_caller_refusal_honored():
    """Caller refusal is honored without repeated interrogation."""
    strat = AdaptivePlanner.plan_strategy(
        call_id="call-refuse",
        session_id="sess-refuse",
        turn_index=3,
        language="en-IN",
        safety_state="NONE",
        safety_signals=[],
        svi_score=25,
        svi_band="LOW",
        svi_trend="INITIAL",
        acoustic_quality="GOOD",
        acoustic_signals=[],
        known_facts={},
        last_caller_utterance="I don't want to answer that question.",
    )
    assert strat.action == AdaptiveAction.PAUSE_ADAPTIVE_QUESTIONS
    assert AdaptiveReasonCode.CALLER_REFUSAL_HONORED in strat.reason_codes
    assert "do_not_re-ask_refused_item" in strat.constraints


def test_repeated_ambiguity_triggers_human_handoff():
    """If clarification was attempted >= 2 times, transitions deterministically to HUMAN_HANDOFF."""
    strat = AdaptivePlanner.plan_strategy(
        call_id="call-ambig",
        session_id="sess-ambig",
        turn_index=4,
        language="en-IN",
        safety_state="NONE",
        safety_signals=[],
        svi_score=30,
        svi_band="MODERATE",
        svi_trend="INITIAL",
        acoustic_quality="GOOD",
        acoustic_signals=[],
        known_facts={},
        last_caller_utterance="...",
        strategy_attempt_counts={"CLARIFY": 2},
    )
    assert strat.action == AdaptiveAction.HUMAN_HANDOFF
    assert AdaptiveReasonCode.REPEATED_AMBIGUITY in strat.reason_codes
    assert strat.requires_human_review is True


def test_operator_override():
    """Manual operator overrides take highest precedence."""
    override = OperatorOverride(
        action=OperatorOverrideAction.FORCE_HUMAN,
        reason="Caller is crying silently, tele-counselor intervening",
        operator_id="counselor_42",
    )
    strat = AdaptivePlanner.plan_strategy(
        call_id="call-override",
        session_id="sess-override",
        turn_index=2,
        language="en-IN",
        safety_state="NONE",
        safety_signals=[],
        svi_score=20,
        svi_band="LOW",
        svi_trend="INITIAL",
        acoustic_quality="GOOD",
        acoustic_signals=[],
        known_facts={},
        last_caller_utterance="Hello",
        active_override=override,
    )
    assert strat.action == AdaptiveAction.HUMAN_HANDOFF
    assert strat.operator_override_active is True
    assert AdaptiveReasonCode.OPERATOR_REQUESTED_HUMAN in strat.reason_codes


def test_closure_policy():
    """Graceful closure only when safety is NONE and caller expresses completion."""
    strat = AdaptivePlanner.plan_strategy(
        call_id="call-close",
        session_id="sess-close",
        turn_index=6,
        language="en-IN",
        safety_state="NONE",
        safety_signals=[],
        svi_score=15,
        svi_band="LOW",
        svi_trend="FALLING",
        acoustic_quality="GOOD",
        acoustic_signals=[],
        known_facts={"immediate_danger": False, "safe_now": True},
        last_caller_utterance="Thank you so much, that helps. Goodbye.",
    )
    assert strat.action == AdaptiveAction.END_GRACEFULLY
    assert strat.priority == AdaptivePriority.P5
    assert AdaptiveReasonCode.CLOSURE_READY in strat.reason_codes


def test_contradiction_handling_in_engine():
    """New explicit evidence supersedes older contradictory assumption and notes contradiction."""
    engine = AdaptiveEngine()

    # Turn 1: Caller says they are safe
    s1 = engine.evaluate_turn(
        call_id="c-contra",
        session_id="s-contra",
        turn_index=1,
        utterance_text="I am safe now at home.",
        language="en-IN",
    )
    assert "safe_now" in engine._session_states["s-contra"]["facts"]
    assert engine._session_states["s-contra"]["facts"]["safe_now"].value is True

    # Turn 2: Caller says someone is outside threatening them
    s2 = engine.evaluate_turn(
        call_id="c-contra",
        session_id="s-contra",
        turn_index=2,
        utterance_text="Wait, he is outside threatening me with a knife!",
        language="en-IN",
        safety_assessment=None,
    )
    # The older safe_now fact must be superseded
    assert engine._session_states["s-contra"]["facts"]["safe_now"].superseded is True
    assert engine._session_states["s-contra"]["facts"]["immediate_danger"].value is True
    assert AdaptiveReasonCode.CONTRADICTION_RESOLVED in s2.reason_codes


def test_performance_sub_5ms_benchmark():
    """Planning 100 consecutive turns finishes in < 5ms (target: < 50ms)."""
    req = AdaptivePlanRequest(
        call_id="call-bench",
        session_id="sess-bench",
        turn_index=1,
        language="en-IN",
        safety_state="ELEVATED",
        safety_signals=[{"severity": "HIGH", "signal_type": "ONGOING_THREAT"}],
        svi_score=60,
        svi_band="HIGH",
        svi_trend="RISING",
        acoustic_quality="GOOD",
        acoustic_signals=[],
        known_facts={"recency": "today"},
        last_caller_utterance="He threatened me earlier.",
    )

    start = time.perf_counter()
    iterations = 100
    for _ in range(iterations):
        AdaptivePlanner.evaluate_request(req)
    total_ms = (time.perf_counter() - start) * 1000
    avg_ms = total_ms / iterations

    assert avg_ms < 5.0, f"Average planning latency was {avg_ms:.3f}ms, expected < 5.0ms"
