import time
import pytest
from app.schemas.safety import SafetyEvidence, SafetySeverity, SafetySignal, SafetySignalType
from app.schemas.svi import SVIBand, SVIFeatureCategory, SVITrend
from app.services.svi_engine import SVIEngine


@pytest.fixture
def engine():
    return SVIEngine()


def test_svi_boundaries(engine):
    """Verifies that SVI score is always clamped between 0 and 100."""
    # Empty turns
    assessment_empty = engine.evaluate_session(
        call_id="call-empty",
        session_id="sess-empty",
        turns=[],
    )
    assert 0 <= assessment_empty.score <= 100
    assert assessment_empty.score == 0
    assert assessment_empty.band == SVIBand.LOW
    assert assessment_empty.assessment_completeness == 0.0

    # Overwhelming cues (would exceed 100 if uncapped)
    extreme_turns = [
        {"speaker": "caller", "text": "locked me inside and won't let me go, took my phone"},
        {"speaker": "caller", "text": "no one to help all alone nobody here isolated"},
        {"speaker": "caller", "text": "cannot breathe panicking extremely scared crying non stop"},
        {"speaker": "caller", "text": "cannot leave no money to travel nowhere to go"},
    ]
    critical_signals = [
        SafetySignal(
            signal_type=SafetySignalType.ACTIVE_VIOLENCE,
            severity=SafetySeverity.CRITICAL,
            evidence=SafetyEvidence(
                rule_id="active_threats",
                matched_category="violence",
                matched_phrase="hitting me",
                reason="Active violence detected",
            ),
            rule_id="active_threats",
            call_id="call-ext",
            session_id="sess-ext",
        )
    ]
    assessment_extreme = engine.evaluate_session(
        call_id="call-ext",
        session_id="sess-ext",
        turns=extreme_turns,
        safety_signals=critical_signals,
    )
    assert 0 <= assessment_extreme.score <= 100
    assert assessment_extreme.score >= 76
    assert assessment_extreme.band == SVIBand.CRITICAL
    assert assessment_extreme.critical_override_applied is True
    assert assessment_extreme.requires_human_review is True


def test_svi_determinism(engine):
    """Verifies that 100 evaluations on the identical input yield bitwise identical output."""
    turns = [
        {"speaker": "caller", "text": "I feel so afraid, he locked me inside the room.", "language": "en-IN"},
    ]
    first = engine.evaluate_session("c1", "s1", turns=turns, previous_score=20)
    
    for _ in range(100):
        repeat = engine.evaluate_session("c1", "s1", turns=turns, previous_score=20)
        assert repeat.score == first.score
        assert repeat.band == first.band
        assert repeat.trend == first.trend
        assert repeat.delta == first.delta
        assert repeat.assessment_completeness == first.assessment_completeness
        assert len(repeat.features) == len(first.features)
        assert repeat.top_contributors == first.top_contributors


def test_svi_monotonicity(engine):
    """Adding risk cues should strictly increase or maintain the score."""
    turns_baseline = [
        {"speaker": "caller", "text": "Hello, I want some information.", "language": "en-IN"},
    ]
    turns_distress = [
        {"speaker": "caller", "text": "Hello, I want some information.", "language": "en-IN"},
        {"speaker": "caller", "text": "I am panicking and extremely scared.", "language": "en-IN"},
    ]
    turns_coercion = [
        {"speaker": "caller", "text": "Hello, I want some information.", "language": "en-IN"},
        {"speaker": "caller", "text": "I am panicking and extremely scared.", "language": "en-IN"},
        {"speaker": "caller", "text": "He locked me in room and took my phone.", "language": "en-IN"},
    ]

    score_base = engine.evaluate_session("c", "s", turns=turns_baseline).score
    score_distress = engine.evaluate_session("c", "s", turns=turns_distress).score
    score_coercion = engine.evaluate_session("c", "s", turns=turns_coercion).score

    assert score_distress >= score_base
    assert score_coercion >= score_distress


def test_critical_safety_floor_override(engine):
    """Critical safety signal enforces minimum score of 76 regardless of protective factors."""
    protective_turns = [
        {"speaker": "caller", "text": "I am in a safe place now, neighbor is here and mother is with me.", "language": "en-IN"},
    ]
    critical_signal = SafetySignal(
        signal_type=SafetySignalType.WEAPON_THREAT,
        severity=SafetySeverity.CRITICAL,
        evidence=SafetyEvidence(
            rule_id="weapons",
            matched_category="weapon",
            matched_phrase="knife",
            reason="Lethal weapon threat",
        ),
        rule_id="weapons",
        call_id="c-crit",
        session_id="s-crit",
    )

    assessment = engine.evaluate_session(
        call_id="c-crit",
        session_id="s-crit",
        turns=protective_turns,
        safety_signals=[critical_signal],
    )
    assert assessment.score >= 76
    assert assessment.band == SVIBand.CRITICAL
    assert assessment.critical_override_applied is True
    assert assessment.requires_human_review is True
    assert assessment.protective_factor_reduction > 0


def test_protective_factor_bounds(engine):
    """Protective factors reduce score by at most 15 points and cannot override high threats."""
    moderate_turns = [
        {"speaker": "caller", "text": "He locked me inside and took my phone.", "language": "en-IN"},
    ]
    assessment_no_prot = engine.evaluate_session("c", "s", turns=moderate_turns)

    protected_turns = [
        {"speaker": "caller", "text": "He locked me inside and took my phone.", "language": "en-IN"},
        {"speaker": "caller", "text": "My mother is with me and neighbor is here, door is locked safely.", "language": "en-IN"},
    ]
    assessment_prot = engine.evaluate_session("c", "s", turns=protected_turns)

    assert assessment_prot.protective_factor_reduction <= 15
    assert assessment_prot.protective_factor_reduction > 0
    assert assessment_prot.score < assessment_no_prot.score


def test_recency_decay(engine):
    """PRESENT cues have weight 1.0, RECENT has 0.75, HISTORICAL has 0.35."""
    present_turn = [{"speaker": "caller", "text": "He locked me inside right now.", "language": "en-IN"}]
    recent_turn = [{"speaker": "caller", "text": "He locked me inside earlier today.", "language": "en-IN"}]
    historical_turn = [{"speaker": "caller", "text": "He locked me inside last year previously.", "language": "en-IN"}]

    score_present = engine.evaluate_session("c", "s", turns=present_turn).score
    score_recent = engine.evaluate_session("c", "s", turns=recent_turn).score
    score_historical = engine.evaluate_session("c", "s", turns=historical_turn).score

    assert score_present > score_recent
    assert score_recent > score_historical


def test_negation_handling(engine):
    """Negated distress/coercion statements should not inflate SVI risk."""
    negated_turn = [{"speaker": "caller", "text": "I am not panicking and I am not locked inside.", "language": "en-IN"}]
    assessment = engine.evaluate_session("c", "s", turns=negated_turn)

    assert assessment.score == 0
    assert assessment.band == SVIBand.LOW
    assert len(assessment.features) == 0


def test_multilingual_lexicons(engine):
    """Verifies SVI matches Tamil and Hindi distress and coercion keywords."""
    # Tamil coercion & distress
    tamil_turns = [
        {"speaker": "caller", "text": "என்னை பூட்டி வச்சிருக்காங்க, ரொம்ப பயமா இருக்கு", "language": "ta-IN"},
    ]
    assessment_ta = engine.evaluate_session("c-ta", "s-ta", turns=tamil_turns)
    assert assessment_ta.score > 15
    assert any("பூட்டி" in f.matched_phrase or "பயமா" in f.matched_phrase for f in assessment_ta.features)

    # Hindi coercion & distress
    hindi_turns = [
        {"speaker": "caller", "text": "मुझे कमरे में बंद कर दिया है, बहुत डर लग रहा है", "language": "hi-IN"},
    ]
    assessment_hi = engine.evaluate_session("c-hi", "s-hi", turns=hindi_turns)
    assert assessment_hi.score > 15
    assert any("बंद" in f.matched_phrase or "डर" in f.matched_phrase for f in assessment_hi.features)


def test_trend_calculation(engine):
    """Verifies trend computation (INITIAL, RISING, FALLING, STABLE)."""
    turns_high = [
        {"speaker": "caller", "text": "extremely scared panicking locked inside cannot leave", "language": "en-IN"}
    ]
    # Initial
    a_init = engine.evaluate_session("c", "s", turns=turns_high, previous_score=None)
    assert a_init.trend == SVITrend.INITIAL
    assert a_init.delta == 0

    # Rising (prior score was 10)
    a_rising = engine.evaluate_session("c", "s", turns=turns_high, previous_score=10)
    assert a_rising.trend == SVITrend.RISING
    assert a_rising.delta > 5

    # Falling (prior score was 90)
    turns_low = [{"speaker": "caller", "text": "safe now mother is with me", "language": "en-IN"}]
    a_falling = engine.evaluate_session("c", "s", turns=turns_low, previous_score=90)
    assert a_falling.trend == SVITrend.FALLING
    assert a_falling.delta < -5

    # Stable (prior score was identical)
    a_stable = engine.evaluate_session("c", "s", turns=turns_high, previous_score=a_rising.score)
    assert a_stable.trend == SVITrend.STABLE
    assert a_stable.delta == 0


def test_performance_benchmark(engine):
    """Sub-5ms deterministic benchmark across 100 session evaluations."""
    turns = [
        {"speaker": "caller", "text": "He locked me in room and I cannot leave.", "language": "en-IN"},
        {"speaker": "caller", "text": "I am panicking and extremely scared.", "language": "en-IN"},
    ]
    start = time.perf_counter()
    iterations = 100
    for _ in range(iterations):
        engine.evaluate_session("c-bench", "s-bench", turns=turns, previous_score=25)
    total_elapsed = time.perf_counter() - start
    avg_ms = (total_elapsed / iterations) * 1000.0

    assert avg_ms < 5.0, f"Average execution took {avg_ms:.2f}ms, target is < 5ms"


def test_acoustic_deferral_notice(engine):
    """Verifies Phase 6 acoustic deferral notice is explicitly returned."""
    assessment = engine.evaluate_session("c", "s", turns=[])
    assert assessment.acoustic_evidence_available is False
    assert "Phase 6 deferred" in assessment.acoustic_evidence_note
    assert "NOT a clinical" in assessment.disclaimer
