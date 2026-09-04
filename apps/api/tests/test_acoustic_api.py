import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.realtime.session_manager import telephony_session_manager


@pytest.fixture
def client():
    return TestClient(app)


def test_get_acoustic_status(client):
    response = client.get("/v1/acoustic/status")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ready"
    assert data["engine_version"] == "v1.0.0"
    assert data["canonical_sample_rate_hz"] == 8000
    assert data["frame_duration_ms"] == 20
    assert data["is_operational_support_only"] is True
    assert "not a clinical" in data["disclaimer"].lower()


def test_get_acoustic_rules(client):
    response = client.get("/v1/acoustic/rules")
    assert response.status_code == 200
    data = response.json()
    assert data["rules_count"] >= 8
    signal_codes = [r["signal_code"] for r in data["rules"]]
    assert "PROLONGED_SILENCE_OBSERVED" in signal_codes
    assert "FREQUENT_INTERRUPTION_PATTERN" in signal_codes
    assert "HIGH_SPEECH_ACTIVITY" in signal_codes
    assert "LOW_VOICE_ACTIVITY" in signal_codes
    assert "ELEVATED_ENERGY_VARIABILITY" in signal_codes
    assert "AUDIO_QUALITY_LOW" in signal_codes
    assert "AUDIO_QUALITY_DEGRADED" in signal_codes
    assert "SIGNAL_INSUFFICIENT" in signal_codes


def test_post_acoustic_evaluate_synthetic(client):
    payload = {
        "call_id": "test-call-ac-api",
        "session_id": "test-sess-ac-api",
        "audio_duration_ms": 6000,
        "speech_ratio": 0.30,
        "max_silence_ms": 3200,
        "interruptions": 2,
        "mean_rms": 700.0,
        "energy_variability": 0.55,
        "clipping_ratio": 0.0,
    }
    response = client.post("/v1/acoustic/evaluate", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["call_id"] == "test-call-ac-api"
    assert data["session_id"] == "test-sess-ac-api"
    assert data["quality"] in ("GOOD", "EXCELLENT")
    assert data["confidence"] > 0.5
    assert data["pause_metrics"]["longest_pause_ms"] >= 3000
    assert data["interruption_metrics"]["interruption_count"] == 2
    assert "not a clinical" in data["disclaimer"].lower()

    signals = [s["code"] for s in data["operational_signals"]]
    assert "PROLONGED_SILENCE_OBSERVED" in signals
    assert "FREQUENT_INTERRUPTION_PATTERN" in signals
    assert "ELEVATED_ENERGY_VARIABILITY" in signals


@pytest.mark.asyncio
async def test_get_call_acoustic_not_found(client):
    response = client.get("/v1/acoustic/calls/non-existent-call-id")
    assert response.status_code == 404
    data = response.json()
    msg = data.get("error", {}).get("message", "") or data.get("detail", "")
    assert "not found" in msg.lower()


@pytest.mark.asyncio
async def test_get_call_acoustic_history_not_found(client):
    response = client.get("/v1/acoustic/calls/non-existent-call-id/history")
    assert response.status_code == 404
    data = response.json()
    msg = data.get("error", {}).get("message", "") or data.get("detail", "")
    assert "not found" in msg.lower()


@pytest.mark.asyncio
async def test_get_call_acoustic_existing_session(client):
    # Create an active telephony session
    session = await telephony_session_manager.create_session(
        session_id="test-session-ac-1",
        call_id="test-call-ac-1",
        provider_call_id="prov-ac-1",
        caller_number="+919876543210",
        attach_ai=False,
    )

    # Ingest synthetic evaluation directly
    from app.services.acoustic_engine import acoustic_engine
    eval_req = {
        "call_id": "test-call-ac-1",
        "session_id": "test-session-ac-1",
        "audio_duration_ms": 2500,
        "speech_ratio": 0.75,
    }
    client.post("/v1/acoustic/evaluate", json=eval_req)
    assessment = acoustic_engine.get_latest_assessment("test-session-ac-1")
    if assessment:
        session.record_acoustic_assessment(assessment)

    # Query call acoustic endpoint
    res = client.get("/v1/acoustic/calls/test-call-ac-1")
    assert res.status_code == 200
    data = res.json()
    assert data["call_id"] == "test-call-ac-1"
    assert data["quality"] in ("GOOD", "EXCELLENT")

    # Query history endpoint
    hist_res = client.get("/v1/acoustic/calls/test-call-ac-1/history")
    assert hist_res.status_code == 200
    hist_data = hist_res.json()
    assert hist_data["assessments_count"] >= 1

    # Cleanup session
    await telephony_session_manager.end_session("test-session-ac-1")
