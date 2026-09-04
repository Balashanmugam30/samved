import math
import struct
import time
import pytest
from app.schemas.acoustic import (
    AcousticAssessment,
    AcousticEvaluationRequest,
    AcousticOperationalSignal,
    AcousticQuality,
    OperationalSignalCode,
)
from app.services.acoustic_engine import AcousticEngine, acoustic_engine
from app.services.svi_engine import svi_engine


def generate_pcm_frame(amplitude: int = 1000, num_samples: int = 160) -> bytes:
    """Generates 160 samples (20ms at 8kHz) 16-bit signed LE PCM bytes."""
    samples = [int(amplitude * math.sin(2 * math.pi * 200 * (i / 8000.0))) for i in range(num_samples)]
    return struct.pack(f"<{num_samples}h", *samples)


def generate_silent_frame(amplitude: int = 10, num_samples: int = 160) -> bytes:
    """Generates silent PCM frame under VAD threshold."""
    samples = [amplitude] * num_samples
    return struct.pack(f"<{num_samples}h", *samples)


def test_frame_feature_extraction_normal_speech():
    engine = AcousticEngine()
    frame_bytes = generate_pcm_frame(amplitude=1500)
    features = engine.extract_frame_features(frame_bytes)

    assert features.is_speech is True
    assert features.energy_rms > 500.0
    assert features.is_clipping is False
    assert features.zero_crossing_rate > 0.0
    assert features.f0_hz is not None
    assert 80.0 <= features.f0_hz <= 350.0


def test_frame_feature_extraction_silence():
    engine = AcousticEngine()
    frame_bytes = generate_silent_frame(amplitude=20)
    features = engine.extract_frame_features(frame_bytes)

    assert features.is_speech is False
    assert features.energy_rms < 100.0
    assert features.is_clipping is False
    assert features.f0_hz is None


def test_frame_feature_extraction_clipping():
    engine = AcousticEngine()
    clipped_bytes = struct.pack("<160h", *([32500] * 160))
    features = engine.extract_frame_features(clipped_bytes)

    assert features.is_clipping is True
    assert features.energy_rms >= 32000.0


def test_insufficient_signal_evaluation():
    engine = AcousticEngine()
    assessment = engine.evaluate_window(
        call_id="call-insufficient",
        session_id="sess-insufficient",
        window_frames=[],
    )

    assert assessment.quality == AcousticQuality.INSUFFICIENT
    assert len(assessment.operational_signals) == 1
    assert assessment.operational_signals[0].code == OperationalSignalCode.SIGNAL_INSUFFICIENT
    assert assessment.confidence < 0.5


def test_prolonged_silence_detection():
    engine = AcousticEngine()
    session_id = "sess-silence"

    # Feed 150 silent frames (3000ms)
    for _ in range(160):
        engine.ingest_frame(session_id, "call-1", generate_silent_frame())

    assessment = engine.evaluate_window("call-1", session_id)
    assert assessment.pause_metrics.longest_pause_ms >= 3000
    signal_codes = [s.code for s in assessment.operational_signals]
    assert OperationalSignalCode.PROLONGED_SILENCE_OBSERVED in signal_codes


def test_frequent_interruption_detection():
    engine = AcousticEngine()
    session_id = "sess-interrupt"

    # Ingest speech frames and 2 interruptions
    for _ in range(50):
        engine.ingest_frame(session_id, "call-2", generate_pcm_frame(amplitude=1200))
    engine.record_interruption(session_id)
    engine.record_interruption(session_id)

    assessment = engine.evaluate_window("call-2", session_id)
    assert assessment.interruption_metrics.interruption_count >= 2
    assert assessment.interruption_metrics.rapid_interruption_detected is True
    signal_codes = [s.code for s in assessment.operational_signals]
    assert OperationalSignalCode.FREQUENT_INTERRUPTION_PATTERN in signal_codes


def test_high_and_low_speech_activity_detection():
    engine = AcousticEngine()

    # High speech activity: 100 speech frames (2000ms continuous)
    high_req = AcousticEvaluationRequest(
        call_id="call-high",
        session_id="sess-high",
        audio_duration_ms=3000,
        speech_ratio=0.90,
        mean_rms=800.0,
    )
    high_assessment = engine.evaluate_synthetic(high_req)
    high_codes = [s.code for s in high_assessment.operational_signals]
    assert OperationalSignalCode.HIGH_SPEECH_ACTIVITY in high_codes

    # Low speech activity: 10% speech
    low_req = AcousticEvaluationRequest(
        call_id="call-low",
        session_id="sess-low",
        audio_duration_ms=3000,
        speech_ratio=0.10,
        mean_rms=800.0,
    )
    low_assessment = engine.evaluate_synthetic(low_req)
    low_codes = [s.code for s in low_assessment.operational_signals]
    assert OperationalSignalCode.LOW_VOICE_ACTIVITY in low_codes


def test_energy_variability_signal():
    engine = AcousticEngine()
    req = AcousticEvaluationRequest(
        call_id="call-energy",
        session_id="sess-energy",
        audio_duration_ms=3000,
        speech_ratio=0.70,
        mean_rms=600.0,
        energy_variability=0.65,
    )
    assessment = engine.evaluate_synthetic(req)
    assert assessment.energy_metrics.energy_variability >= 0.50
    codes = [s.code for s in assessment.operational_signals]
    assert OperationalSignalCode.ELEVATED_ENERGY_VARIABILITY in codes


def test_audio_quality_classification():
    engine = AcousticEngine()

    # Low quality via clipping
    poor_req = AcousticEvaluationRequest(
        call_id="call-poor",
        session_id="sess-poor",
        audio_duration_ms=2000,
        speech_ratio=0.50,
        clipping_ratio=0.15,
    )
    poor_assessment = engine.evaluate_synthetic(poor_req)
    assert poor_assessment.quality == AcousticQuality.POOR
    poor_codes = [s.code for s in poor_assessment.operational_signals]
    assert OperationalSignalCode.AUDIO_QUALITY_LOW in poor_codes

    # Degraded quality
    deg_req = AcousticEvaluationRequest(
        call_id="call-deg",
        session_id="sess-deg",
        audio_duration_ms=2000,
        speech_ratio=0.50,
        clipping_ratio=0.06,
    )
    deg_assessment = engine.evaluate_synthetic(deg_req)
    assert deg_assessment.quality == AcousticQuality.DEGRADED
    deg_codes = [s.code for s in deg_assessment.operational_signals]
    assert OperationalSignalCode.AUDIO_QUALITY_DEGRADED in deg_codes


def test_determinism():
    """Exact same acoustic parameters produce 100% identical assessment."""
    engine = AcousticEngine()
    req = AcousticEvaluationRequest(
        call_id="call-det",
        session_id="sess-det",
        audio_duration_ms=4000,
        speech_ratio=0.65,
        max_silence_ms=2500,
        interruptions=2,
        mean_rms=750.0,
        energy_variability=0.35,
    )
    res1 = engine.evaluate_synthetic(req)
    res2 = engine.evaluate_synthetic(req)

    assert res1.quality == res2.quality
    assert res1.confidence == res2.confidence
    assert res1.voice_activity.speech_activity_ratio == res2.voice_activity.speech_activity_ratio
    assert res1.pause_metrics.longest_pause_ms == res2.pause_metrics.longest_pause_ms
    assert len(res1.operational_signals) == len(res2.operational_signals)
    assert [s.code for s in res1.operational_signals] == [s.code for s in res2.operational_signals]


def test_performance_benchmark():
    """1000 frames (20 seconds of audio) evaluate within < 15ms (telephony budget < 50ms)."""
    engine = AcousticEngine()
    frame = generate_pcm_frame(amplitude=1200)

    # Ingest 1000 frames
    for i in range(1000):
        engine.ingest_frame("sess-bench", "call-bench", frame)

    # Measure average latency across 10 evaluations
    start = time.perf_counter()
    iterations = 10
    for _ in range(iterations):
        assessment = engine.evaluate_window("call-bench", "sess-bench")
    avg_latency_ms = ((time.perf_counter() - start) / iterations) * 1000

    assert avg_latency_ms < 15.0, f"Average evaluation took {avg_latency_ms:.2f}ms, expected < 15.0ms"
    assert assessment.quality in (AcousticQuality.GOOD, AcousticQuality.EXCELLENT)


def test_svi_acoustic_evidence_integration():
    """Verify SVI Engine incorporates acoustic assessment into evidence without changing formula."""
    engine = AcousticEngine()
    req = AcousticEvaluationRequest(
        call_id="call-svi-ac",
        session_id="sess-svi-ac",
        audio_duration_ms=5000,
        speech_ratio=0.30,
        interruptions=2,
        max_silence_ms=3200,
    )
    acoustic_ass = engine.evaluate_synthetic(req)

    turns = [
        {"speaker": "caller", "text": "He locked the door and took away my phone.", "language": "en-IN"}
    ]
    svi_ass = svi_engine.evaluate_session(
        call_id="call-svi-ac",
        session_id="sess-svi-ac",
        turns=turns,
        safety_signals=[],
        acoustic_assessment=acoustic_ass,
    )

    assert svi_ass.acoustic_evidence_available is True
    assert "quality=" in svi_ass.acoustic_evidence_note
    assert "FREQUENT_INTERRUPTION_PATTERN" in svi_ass.acoustic_evidence_note
    assert "NOT a clinical" in svi_ass.disclaimer
    assert acoustic_ass.is_supporting_signal is True

