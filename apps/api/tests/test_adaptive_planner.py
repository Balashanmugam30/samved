"""Unit tests for Adaptive Information-Gap Planner and Response Validator."""

from app.adaptive.models import (
    AdaptiveAction,
    AdaptivePlanRequest,
    AdaptivePriority,
    AdaptiveReasonCode,
    ConversationStrategy,
)
from app.adaptive.planner import AdaptivePlanner
from app.adaptive.templates import get_template
from app.adaptive.validator import ResponseValidator


def test_multilingual_templates():
    """Verifies that versioned templates are available across Tamil, Hindi, and English."""
    for action in [
        AdaptiveAction.SAFETY_CHECK,
        AdaptiveAction.ASK_IMMEDIATE_DANGER,
        AdaptiveAction.HUMAN_HANDOFF,
        AdaptiveAction.CLARIFY_AUDIO,
        AdaptiveAction.END_GRACEFULLY,
    ]:
        en = get_template(action, "en-IN")
        ta = get_template(action, "ta-IN")
        hi = get_template(action, "hi-IN")

        assert len(en) > 10
        assert len(ta) > 10
        assert len(hi) > 10
        assert en != ta
        assert en != hi


def test_acoustic_supportive_degradation():
    """Poor line quality triggers CLARIFY_AUDIO as supportive action."""
    req = AdaptivePlanRequest(
        call_id="call-ac-deg",
        session_id="sess-ac-deg",
        turn_index=1,
        language="en-IN",
        safety_state="NONE",
        safety_signals=[],
        svi_score=20,
        svi_band="LOW",
        svi_trend="INITIAL",
        acoustic_quality="POOR",
        acoustic_signals=[{"code": "AUDIO_QUALITY_DEGRADED", "evidence": "clipping > 0.05"}],
        known_facts={"recency": "today"},
        last_caller_utterance="Krrrk... crzzt... hello?",
    )
    strat = AdaptivePlanner.evaluate_request(req)
    assert strat.action == AdaptiveAction.CLARIFY_AUDIO
    assert AdaptiveReasonCode.AUDIO_QUALITY_DEGRADED in strat.reason_codes


def test_acoustic_prolonged_silence():
    """Prolonged silence with no speech triggers ALLOW_SILENCE."""
    req = AdaptivePlanRequest(
        call_id="call-ac-sil",
        session_id="sess-ac-sil",
        turn_index=1,
        language="en-IN",
        safety_state="NONE",
        safety_signals=[],
        svi_score=20,
        svi_band="LOW",
        svi_trend="INITIAL",
        acoustic_quality="GOOD",
        acoustic_signals=[{"code": "PROLONGED_SILENCE_OBSERVED", "evidence": "pause >= 4000ms"}],
        known_facts={"recency": "today"},
        last_caller_utterance="",
    )
    strat = AdaptivePlanner.evaluate_request(req)
    assert strat.action == AdaptiveAction.ALLOW_SILENCE
    assert AdaptiveReasonCode.PROLONGED_SILENCE_HANDLING in strat.reason_codes


def test_information_gap_sequencing():
    """Planner resolves information gaps in order: recency -> preference -> next_step."""
    # 1. Missing recency
    s1 = AdaptivePlanner.plan_strategy(
        call_id="c-gap", session_id="s-gap", turn_index=1, language="en-IN",
        safety_state="NONE", safety_signals=[], svi_score=20, svi_band="LOW",
        svi_trend="INITIAL", acoustic_quality="GOOD", acoustic_signals=[],
        known_facts={}, last_caller_utterance="I want some help.",
    )
    assert s1.action == AdaptiveAction.ASK_RECENCY

    # 2. Known recency, missing preference
    s2 = AdaptivePlanner.plan_strategy(
        call_id="c-gap", session_id="s-gap", turn_index=2, language="en-IN",
        safety_state="NONE", safety_signals=[], svi_score=20, svi_band="LOW",
        svi_trend="INITIAL", acoustic_quality="GOOD", acoustic_signals=[],
        known_facts={"recency": "today"}, last_caller_utterance="This happened today.",
    )
    assert s2.action == AdaptiveAction.ASK_PREFERENCE

    # 3. Known recency & preference, missing next_step
    s3 = AdaptivePlanner.plan_strategy(
        call_id="c-gap", session_id="s-gap", turn_index=3, language="en-IN",
        safety_state="NONE", safety_signals=[], svi_score=20, svi_band="LOW",
        svi_trend="INITIAL", acoustic_quality="GOOD", acoustic_signals=[],
        known_facts={"recency": "today", "preference": "counseling"},
        last_caller_utterance="I want counseling.",
    )
    assert s3.action == AdaptiveAction.ASK_NEXT_STEP


def test_response_validator_prohibitions():
    """Validator rejects police dispatch, medical diagnoses, and lie accusations."""
    strat = ConversationStrategy(
        call_id="c-val", session_id="s-val", turn_index=1,
        action=AdaptiveAction.SAFETY_CHECK, priority=AdaptivePriority.P0,
        target_information="physical_safety", language="en-IN",
    )

    # 1. Police dispatch prohibited
    bad_text_1 = "Stay calm, the police is dispatched and coming to your address."
    is_valid, reason, final_text = ResponseValidator.validate_response(bad_text_1, strat)
    assert not is_valid
    assert "prohibited claim" in reason
    assert final_text == get_template(AdaptiveAction.SAFETY_CHECK, "en-IN")

    # 2. Medical diagnosis prohibited
    bad_text_2 = "You have clinical addiction and severe psychiatric disorders."
    is_valid, reason, final_text = ResponseValidator.validate_response(bad_text_2, strat)
    assert not is_valid
    assert "prohibited claim" in reason

    # 3. Empty text rejected
    is_valid, reason, final_text = ResponseValidator.validate_response("", strat)
    assert not is_valid
    assert "empty" in reason

    # 4. Exceeding max words (> 45 words)
    long_text = "word " * 50
    is_valid, reason, final_text = ResponseValidator.validate_response(long_text, strat)
    assert not is_valid
    assert "length" in reason

    # 5. Compliant response passes
    good_text = "Please stay in a safe room right now. Are you in immediate danger?"
    is_valid, reason, final_text = ResponseValidator.validate_response(good_text, strat)
    assert is_valid
    assert final_text == good_text
