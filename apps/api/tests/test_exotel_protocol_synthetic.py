import base64
import hashlib
import hmac
import json
import uuid
import pytest
from starlette.websockets import WebSocketDisconnect

from app.core.config import Settings, get_settings
from app.providers.exotel import ExotelTelephonyProvider


def test_exotel_inbound_post_and_get_lifecycle(client):
    """Test full inbound webhook lifecycle: POST, idempotency, and GET resolver."""
    call_sid = f"test-proto-call-{uuid.uuid4().hex[:8]}"
    post_payload = {
        "CallSid": call_sid,
        "From": "+919876543210",
        "To": "14566",
        "Direction": "inbound",
    }

    # 1. POST webhook
    resp = client.post("/v1/telephony/exotel/inbound", json=post_payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["action"] == "stream"
    assert data["format"] == "pcm_8000_16bit_mono"
    session_id = data["session_id"]
    stream_url = data["stream_url"]

    # 2. Idempotent repeated POST
    resp_repeat = client.post("/v1/telephony/exotel/inbound", json=post_payload)
    assert resp_repeat.status_code == 200
    assert resp_repeat.json()["session_id"] == session_id
    assert resp_repeat.json()["stream_url"] == stream_url

    # 3. GET VoiceBot dynamic resolver
    get_params = {
        "CallSid": call_sid,
        "CallFrom": "+919876543210",
        "CallTo": "14566",
        "Direction": "incoming",
    }
    resp_get = client.get("/v1/telephony/exotel/inbound", params=get_params)
    assert resp_get.status_code == 200
    assert resp_get.json()["url"] == stream_url


def test_exotel_webhook_hmac_signature_verification(client, monkeypatch):
    """Verifies HMAC signature validation: valid signatures accepted, invalid rejected."""
    from app.api.v1.telephony import exotel_provider

    secret = "test-exotel-secret-key-12345"
    monkeypatch.setattr(exotel_provider.settings, "EXOTEL_VERIFY_SIGNATURE", True)
    monkeypatch.setattr(exotel_provider.settings, "EXOTEL_WEBHOOK_SECRET", secret)

    call_sid = f"sig-test-{uuid.uuid4().hex[:8]}"
    payload = json.dumps({"CallSid": call_sid, "From": "+919876543210", "To": "14566"}).encode("utf-8")

    # Valid signature
    valid_sig = hmac.new(secret.encode("utf-8"), payload, hashlib.sha256).hexdigest()
    resp_valid = client.post(
        "/v1/telephony/exotel/inbound",
        content=payload,
        headers={"Content-Type": "application/json", "X-Exotel-Signature": valid_sig},
    )
    assert resp_valid.status_code == 200

    # Invalid signature
    resp_invalid = client.post(
        "/v1/telephony/exotel/inbound",
        content=payload,
        headers={"Content-Type": "application/json", "X-Exotel-Signature": "invalid-sig"},
    )
    assert resp_invalid.status_code == 403

    # Monkeypatch handles teardown automatically


def test_exotel_websocket_full_protocol_synthetic(client):
    """Tests complete bidirectional Exotel WebSocket protocol: connected, start, media, mark, clear, stop."""
    call_sid = f"ws-proto-{uuid.uuid4().hex[:8]}"
    inbound_resp = client.post(
        "/v1/telephony/exotel/inbound",
        json={"CallSid": call_sid, "From": "+919876543210", "To": "14566"},
    )
    assert inbound_resp.status_code == 200
    session_id = inbound_resp.json()["session_id"]
    stream_sid = f"stream-{session_id}"

    with client.websocket_connect(f"/ws/telephony/exotel/{session_id}") as ws:
        # 1. Connected event
        ws.send_text(json.dumps({"event": "connected"}))

        # 2. Start event
        ws.send_text(
            json.dumps({
                "event": "start",
                "streamSid": stream_sid,
                "start": {
                    "streamSid": stream_sid,
                    "accountSid": "ACtest",
                    "callSid": call_sid,
                    "tracks": ["inbound", "outbound"],
                },
            })
        )

        # 3. Stream 5 media frames (20ms / 320 bytes each @ 8kHz mono 16-bit PCM)
        dummy_pcm = b"\x00\x04" * 160
        b64_payload = base64.b64encode(dummy_pcm).decode("utf-8")

        for seq in range(1, 6):
            ws.send_text(
                json.dumps({
                    "event": "media",
                    "sequenceNumber": seq,
                    "streamSid": stream_sid,
                    "media": {
                        "track": "inbound",
                        "chunk": str(seq),
                        "timestamp": str(seq * 20),
                        "payload": b64_payload,
                    },
                })
            )

        # 4. Clear event (barge-in interruption)
        ws.send_text(json.dumps({"event": "clear", "streamSid": stream_sid}))

        # 5. Mark event received from Exotel
        ws.send_text(
            json.dumps({
                "event": "mark",
                "streamSid": stream_sid,
                "mark": {"name": "test_mark"},
            })
        )

        # 6. Stop event
        ws.send_text(json.dumps({"event": "stop", "streamSid": stream_sid}))

    # Verify session cleaned up
    remaining = client.get("/v1/telephony/sessions").json()
    assert not any(s["session_id"] == session_id for s in remaining)


def test_exotel_websocket_malformed_inputs(client):
    """Verifies that malformed JSON, missing session, and bad payloads do not crash the server."""
    # 1. Nonexistent session ID -> 4004
    with client.websocket_connect("/ws/telephony/exotel/nonexistent-session") as ws:
        with pytest.raises(WebSocketDisconnect) as exc:
            ws.receive_text()
        assert exc.value.code == 4004

    # 2. Valid session with malformed messages
    call_sid = f"malform-{uuid.uuid4().hex[:8]}"
    inbound_resp = client.post(
        "/v1/telephony/exotel/inbound",
        json={"CallSid": call_sid, "From": "+919876543210", "To": "14566"},
    )
    session_id = inbound_resp.json()["session_id"]

    with client.websocket_connect(f"/ws/telephony/exotel/{session_id}") as ws:
        # Send raw invalid non-JSON string
        ws.send_text("THIS IS NOT JSON")

        # Send media event with invalid base64
        ws.send_text(json.dumps({"event": "media", "media": {"payload": "not-valid-base64!!!"}}))

        # Send empty media event
        ws.send_text(json.dumps({"event": "media"}))

        # Send valid stop event to close cleanly
        ws.send_text(json.dumps({"event": "stop"}))
