import time
import pytest
from app.services.safety_engine import safety_engine
from app.schemas.safety import SafetySeverity, SafetyState, SafetySignalType


def test_safety_engine_initialization():
    """Verify safety engine loaded rule catalog successfully and is ready."""
    assert safety_engine.is_ready is True
    assert len(safety_engine.rules) >= 6
    assert "active_threats" in safety_engine.rules
    assert "weapons" in safety_engine.rules
    assert "self_harm" in safety_engine.rules
    assert "confinement" in safety_engine.rules
    assert "medical_emergency" in safety_engine.rules
    assert "stalking" in safety_engine.rules


def test_normalization_and_unicode_handling():
    """Verify unicode NFC normalization, lowercase, and script preservation."""
    raw = "  He is   BREAKING into the house!!  \n"
    norm = safety_engine.normalize(raw)
    assert norm == "he is breaking into the house!!"

    tamil_raw = "  அவர் என்னை   அடிக்கிறார்  "
    norm_ta = safety_engine.normalize(tamil_raw)
    assert "அவர் என்னை அடிக்கிறார்" in norm_ta


def test_negation_detection():
    """Verify negation detection prevents false positives across languages."""
    # English negation
    assert safety_engine.is_negated("he does not have a knife", "knife") is True
    assert safety_engine.is_negated("no weapon involved here", "weapon") is True
    assert safety_engine.is_negated("he is hitting me with a knife", "knife") is False

    # Tamil negation
    assert safety_engine.is_negated("அவரிடம் கத்தி இல்லை", "கத்தி") is True
    assert safety_engine.is_negated("அவரிடம் கத்தி இருக்கிறது", "கத்தி") is False

    # Hindi negation
    assert safety_engine.is_negated("uske paas koi hathiyar nahi hai", "hathiyar") is True
    assert safety_engine.is_negated("uske paas hathiyar hai", "hathiyar") is False


def test_temporal_classification():
    """Verify classification into PRESENT, PAST, and HYPOTHETICAL."""
    # Past
    assert safety_engine.classify_temporal("He hit me two years ago") == "PAST"
    assert safety_engine.classify_temporal("This happened last year in my village") == "PAST"
    assert safety_engine.classify_temporal("munbu nadanthathu") == "PAST"

    # Hypothetical
    assert safety_engine.classify_temporal("What if he comes back?") == "HYPOTHETICAL"
    assert safety_engine.classify_temporal("Suppose someone tries to break in") == "HYPOTHETICAL"

    # Present
    assert safety_engine.classify_temporal("He is trying to break into the door right now") == "PRESENT"
    assert safety_engine.classify_temporal("ennai adikkirar") == "PRESENT"


def test_active_threat_english():
    """Verify active physical threat in English triggers HIGH/CRITICAL signal."""
    text = "Please help, he is breaking into my door and trying to hit me!"
    assessment = safety_engine.evaluate_turn(text, language="en-IN", call_id="call-1", session_id="sess-1")

    assert assessment.highest_severity in (SafetySeverity.HIGH, SafetySeverity.CRITICAL)
    assert assessment.requires_human_review is True
    assert any(s.signal_type in (SafetySignalType.ACTIVE_THREAT, SafetySignalType.ONGOING_THREAT) for s in assessment.signals)
    assert assessment.signals[0].evidence.temporal_context == "PRESENT"


def test_active_threat_tamil():
    """Verify active physical threat in Tamil triggers explainable safety signal."""
    # Tamil script
    text = "தயவுசெய்து உதவுங்கள், அவர் என்னை அடிக்கிறார்!"
    assessment = safety_engine.evaluate_turn(text, language="ta-IN", call_id="call-2", session_id="sess-2")

    assert assessment.highest_severity in (SafetySeverity.HIGH, SafetySeverity.CRITICAL)
    assert assessment.requires_human_review is True
    assert any(s.signal_type in (SafetySignalType.ACTIVE_THREAT, SafetySignalType.ONGOING_THREAT) for s in assessment.signals)


def test_active_threat_hindi():
    """Verify active threat in Hindi (Devanagari and transliteration) triggers safety signal."""
    text = "madad karo, wo mujhe maar raha hai aur darwaza tod raha hai"
    assessment = safety_engine.evaluate_turn(text, language="hi-IN", call_id="call-3", session_id="sess-3")

    assert assessment.highest_severity in (SafetySeverity.HIGH, SafetySeverity.CRITICAL)
    assert assessment.requires_human_review is True
    assert any(s.signal_type in (SafetySignalType.ACTIVE_THREAT, SafetySignalType.ONGOING_THREAT) for s in assessment.signals)


def test_weapon_compound_escalation():
    """Verify weapon mention + active threat elevates severity to CRITICAL."""
    # Threat with weapon
    text = "He has a knife and he is breaking in right now!"
    assessment = safety_engine.evaluate_turn(text, language="en-IN", call_id="call-4", session_id="sess-4")

    assert assessment.highest_severity == SafetySeverity.CRITICAL
    assert assessment.current_state == SafetyState.CRITICAL
    assert assessment.requires_human_review is True
    assert any(s.signal_type in (SafetySignalType.WEAPON_THREAT, SafetySignalType.WEAPON_MENTION) for s in assessment.signals)


def test_weapon_incidental_mention():
    """Verify incidental weapon mention without threat does NOT trigger CRITICAL."""
    text = "I was in the kitchen cutting vegetables with a knife for dinner."
    assessment = safety_engine.evaluate_turn(text, language="en-IN", call_id="call-5", session_id="sess-5")

    # Should NOT be CRITICAL
    assert assessment.highest_severity != SafetySeverity.CRITICAL
    assert assessment.current_state != SafetyState.CRITICAL


def test_self_harm_trigger():
    """Verify explicit self-harm statement triggers HIGH safety signal."""
    text = "I cannot take this anymore, I want to end my life"
    assessment = safety_engine.evaluate_turn(text, language="en-IN", call_id="call-6", session_id="sess-6")

    assert assessment.highest_severity in (SafetySeverity.HIGH, SafetySeverity.CRITICAL)
    assert assessment.requires_human_review is True
    assert any(s.signal_type == SafetySignalType.SELF_HARM for s in assessment.signals)


def test_forced_confinement():
    """Verify forced confinement trigger produces CONFINEMENT signal."""
    text = "They locked me inside the room and won't let me out"
    assessment = safety_engine.evaluate_turn(text, language="en-IN", call_id="call-7", session_id="sess-7")

    assert assessment.highest_severity in (SafetySeverity.HIGH, SafetySeverity.CRITICAL)
    assert assessment.requires_human_review is True
    assert any(s.signal_type == SafetySignalType.CONFINEMENT for s in assessment.signals)


def test_medical_emergency():
    """Verify acute medical distress triggers MEDICAL_EMERGENCY signal."""
    text = "She is bleeding heavily and cannot breathe, please call ambulance"
    assessment = safety_engine.evaluate_turn(text, language="en-IN", call_id="call-8", session_id="sess-8")

    assert assessment.highest_severity in (SafetySeverity.HIGH, SafetySeverity.CRITICAL)
    assert assessment.requires_human_review is True
    assert any(s.signal_type == SafetySignalType.MEDICAL_EMERGENCY for s in assessment.signals)


def test_benign_conversation_produces_none():
    """Verify normal benign intake produces NONE safety state."""
    text = "Hello, I am calling to inquire about the counseling services offered by NHAA."
    assessment = safety_engine.evaluate_turn(text, language="en-IN", call_id="call-9", session_id="sess-9")

    assert assessment.highest_severity == SafetySeverity.NONE
    assert assessment.current_state == SafetyState.NONE
    assert assessment.requires_human_review is False
    assert len(assessment.signals) == 0


def test_signal_deduplication():
    """Verify repeating identical threat in subsequent turns does not spawn duplicate signals."""
    previously_fired = []
    text = "He is hitting me right now!"

    # Turn 1
    a1 = safety_engine.evaluate_turn(text, language="en-IN", call_id="call-10", session_id="sess-10", previously_fired_signals=previously_fired)
    assert len(a1.signals) > 0
    previously_fired.extend([s.model_dump() for s in a1.signals])

    # Turn 2 with identical text
    a2 = safety_engine.evaluate_turn(text, language="en-IN", call_id="call-10", session_id="sess-10", previously_fired_signals=previously_fired)
    assert len(a2.signals) == 0  # Deduplicated!
    assert a2.current_state in (SafetyState.HIGH, SafetyState.CRITICAL)


def test_determinism_and_performance():
    """Verify 100 evaluations run identically and each executes in < 5ms."""
    text = "He has a knife and is breaking the door right now!"
    results = []

    start = time.perf_counter()
    for _ in range(100):
        assessment = safety_engine.evaluate_turn(text, language="en-IN", call_id="call-perf", session_id="sess-perf")
        results.append(assessment)
    elapsed = time.perf_counter() - start

    avg_ms = (elapsed / 100) * 1000
    assert avg_ms < 5.0, f"Average execution time was {avg_ms:.2f}ms (expected < 5ms)"

    # Check determinism: all outputs have identical severities and signal types
    for res in results:
        assert res.highest_severity == SafetySeverity.CRITICAL
        assert res.current_state == SafetyState.CRITICAL
        assert res.requires_human_review is True
        assert len(res.signals) == len(results[0].signals)
