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


def test_exotel_voicebot_get_resolver_success(client):
    """Exotel VoiceBot applet dynamic WSS resolver invokes GET and expects 200 {"url": "wss://..."}."""
    test_call_sid = f"get-exo-call-{uuid.uuid4().hex[:8]}"
    query_params = {
        "CallSid": test_call_sid,
        "CallFrom": "+919876543210",
        "CallTo": "08045678901",
        "Direction": "incoming",
        "From": "+919876543210",
        "To": "08045678901",
        "CurrentTime": "2026-09-13 14:20:00",
        "DialWhomNumber": "08045678901",
        "CallType": "trans",
        "Created": "2026-09-13 14:20:00",
    }

    response = client.get("/v1/telephony/exotel/inbound", params=query_params)
    assert response.status_code == 200
    assert "application/json" in response.headers.get("content-type", "")

    data = response.json()
    # Contract: response contains expected url contract
    assert "url" in data
    assert data["url"].startswith("ws://") or data["url"].startswith("wss://")

    # Session ID must be correctly represented in the stream URL path
    stream_url = data["url"]
    assert "/ws/telephony/exotel/SESS-" in stream_url
    session_id = stream_url.rstrip("/").split("/")[-1]
    assert session_id.startswith("SESS-")

    # Verify session was created and masked in session manager
    active_sessions = client.get("/v1/telephony/sessions").json()
    matched = [s for s in active_sessions if s["session_id"] == session_id]
    assert len(matched) == 1
    assert matched[0]["caller_masked_number"] == "+91******3210"
    assert matched[0]["state"] in {"RINGING", "CONNECTING"}


def test_exotel_voicebot_get_resolver_wss_scheme(client, monkeypatch):
    """Verifies that with Cloudflare Quick Tunnel / production configuration, the returned URL is wss://."""
    monkeypatch.setenv(
        "EXOTEL_STREAM_URL",
        "wss://cave-gras-treatments-supplied.trycloudflare.com/ws/telephony/exotel",
    )
    get_settings.cache_clear()

    test_call_sid = f"wss-test-{uuid.uuid4().hex[:8]}"
    query_params = {
        "CallSid": test_call_sid,
        "CallFrom": "+919876543210",
        "CallTo": "08045678901",
        "Direction": "incoming",
        "From": "+919876543210",
        "To": "08045678901",
    }

    response = client.get("/v1/telephony/exotel/inbound", params=query_params)
    assert response.status_code == 200
    assert "application/json" in response.headers.get("content-type", "")

    data = response.json()
    assert "url" in data
    # Must be explicitly wss://
    assert data["url"].startswith("wss://cave-gras-treatments-supplied.trycloudflare.com/ws/telephony/exotel/SESS-")

    # Clean up setting cache
    get_settings.cache_clear()


def test_exotel_voicebot_get_resolver_idempotency(client):
    """Repeated GET requests from Exotel for the same CallSid must return identical WSS URL without duplicating session."""
    test_call_sid = f"get-idempotent-{uuid.uuid4().hex[:8]}"
    query_params = {
        "CallSid": test_call_sid,
        "CallFrom": "+919123456789",
        "CallTo": "14566",
        "Direction": "inbound",
    }

    resp1 = client.get("/v1/telephony/exotel/inbound", params=query_params)
    assert resp1.status_code == 200
    data1 = resp1.json()

    resp2 = client.get("/v1/telephony/exotel/inbound", params=query_params)
    assert resp2.status_code == 200
    data2 = resp2.json()

    assert data1["url"] == data2["url"]


def test_exotel_voicebot_get_resolver_missing_call_sid(client):
    """GET without CallSid must return 400 Bad Request."""
    response = client.get("/v1/telephony/exotel/inbound", params={"CallFrom": "+919999999999"})
    assert response.status_code == 400
    data = response.json()
    assert "CallSid" in data["error"]["message"]


def test_exotel_get_and_post_cross_idempotency(client):
    """If Exotel invokes GET resolver first and then sends POST webhook, both must correlate to the same session."""
    test_call_sid = f"cross-idem-{uuid.uuid4().hex[:8]}"
    get_params = {
        "CallSid": test_call_sid,
        "CallFrom": "+919988776655",
        "CallTo": "14566",
    }
    get_resp = client.get("/v1/telephony/exotel/inbound", params=get_params)
    assert get_resp.status_code == 200
    get_data = get_resp.json()
    sess_from_get = get_data["url"].rstrip("/").split("/")[-1]

    post_payload = {
        "CallSid": test_call_sid,
        "From": "+919988776655",
        "To": "14566",
    }
    post_resp = client.post("/v1/telephony/exotel/inbound", json=post_payload)
    assert post_resp.status_code == 200
    post_data = post_resp.json()

    assert post_data["session_id"] == sess_from_get
    assert post_data["stream_url"] == get_data["url"]

