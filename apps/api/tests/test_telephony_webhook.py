import uuid
import pytest
from app.core.config import get_settings
from app.realtime.session_manager import telephony_session_manager


def test_exotel_inbound_webhook_success(client):
    test_call_sid = f"test-exo-call-{uuid.uuid4().hex[:8]}"
    payload = {
        "CallSid": test_call_sid,
        "From": "+919876543210",
        "To": "14566",
        "Direction": "inbound",
    }

    response = client.post("/v1/telephony/exotel/inbound", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["action"] == "stream"
    assert "stream_url" in data
    assert "session_id" in data
    assert data["format"] == "pcm_8000_16bit_mono"

    # Verify session was created and masked in session manager
    sid = data["session_id"]
    active_sessions = client.get("/v1/telephony/sessions").json()
    matched = [s for s in active_sessions if s["session_id"] == sid]
    assert len(matched) == 1
    assert matched[0]["caller_masked_number"] == "+91******3210"
    assert matched[0]["state"] in {"RINGING", "CONNECTING"}


def test_exotel_inbound_webhook_idempotency(client):
    test_call_sid = f"idempotent-exo-{uuid.uuid4().hex[:8]}"
    payload = {
        "CallSid": test_call_sid,
        "From": "+919123456789",
        "To": "14566",
    }

    # First call
    resp1 = client.post("/v1/telephony/exotel/inbound", json=payload)
    assert resp1.status_code == 200
    data1 = resp1.json()

    # Second call with identical CallSid
    resp2 = client.post("/v1/telephony/exotel/inbound", json=payload)
    assert resp2.status_code == 200
    data2 = resp2.json()

    # Must return identical session and stream instruction without duplicating
    assert data1["session_id"] == data2["session_id"]
    assert data1["stream_url"] == data2["stream_url"]


def test_exotel_inbound_missing_call_sid(client):
    response = client.post("/v1/telephony/exotel/inbound", json={"From": "+919999999999"})
    assert response.status_code == 400
    data = response.json()
    assert "CallSid" in data["error"]["message"]


def test_exotel_doctor_endpoint(client):
    response = client.get("/v1/telephony/doctor")
    assert response.status_code == 200
    data = response.json()
    assert data["telephony_provider"] == "Exotel"
    assert "exotel_credentials_present" in data
    assert "live_mode_safe_to_start" in data
    assert "public_webhook_base_url" in data
    assert "public_ws_base_url" in data
    # Ensure no secrets leaked
    assert "api_key" not in data
    assert "api_token" not in data


def test_simulation_call_endpoint(client):
    sim_payload = {
        "caller_phone": "+919811122233",
        "duration_frames": 5,
        "frame_interval_ms": 10,
    }
    response = client.post("/v1/telephony/simulate", json=sim_payload)
    assert response.status_code == 201
    data = response.json()
    assert data["status"] == "simulation_started"
    assert data["call_id"].startswith("SIM-")
    assert data["session_id"].startswith("SESS-")
    assert data["masked_caller_number"] == "+91******2233"
    assert data["frames_scheduled"] == 5
