import base64
import json
import uuid
import pytest
from starlette.websockets import WebSocketDisconnect
from app.realtime.session_manager import telephony_session_manager


def test_telephony_media_ws_unknown_session(client):
    with client.websocket_connect("/ws/telephony/exotel/nonexistent-session-id") as ws:
        with pytest.raises(WebSocketDisconnect) as exc:
            ws.receive_text()
        assert exc.value.code == 4004


def test_telephony_media_ws_lifecycle_and_frames(client):
    # 1. Provision session via webhook
    call_sid = f"ws-test-exo-{uuid.uuid4().hex[:8]}"
    inbound_resp = client.post(
        "/v1/telephony/exotel/inbound",
        json={"CallSid": call_sid, "From": "+919844455566", "To": "14566"},
    )
    assert inbound_resp.status_code == 200
    session_id = inbound_resp.json()["session_id"]

    # 2. Connect Exotel Media WebSocket
    with client.websocket_connect(f"/ws/telephony/exotel/{session_id}") as ws:
        # Send Exotel 'connected' event
        ws.send_text(json.dumps({"event": "connected"}))

        # Send Exotel 'start' event
        start_msg = {
            "event": "start",
            "streamSid": f"stream-{session_id}",
            "start": {
                "streamSid": f"stream-{session_id}",
                "accountSid": "ACtest",
                "callSid": call_sid,
                "tracks": ["inbound", "outbound"],
            },
        }
        ws.send_text(json.dumps(start_msg))

        # Send 3 valid media frames (8kHz mono 16-bit PCM = 320 bytes per 20ms)
        dummy_pcm = b"\x00\x02" * 160
        b64_pcm = base64.b64encode(dummy_pcm).decode("utf-8")

        for seq in [1, 2, 3]:
            media_msg = {
                "event": "media",
                "sequenceNumber": seq,
                "streamSid": f"stream-{session_id}",
                "media": {
                    "track": "inbound",
                    "chunk": str(seq),
                    "timestamp": str(seq * 20),
                    "payload": b64_pcm,
                },
            }
            ws.send_text(json.dumps(media_msg))

        # Send intentional sequence gap (skip seq 4, send seq 5)
        gap_media_msg = {
            "event": "media",
            "sequenceNumber": 5,
            "streamSid": f"stream-{session_id}",
            "media": {
                "track": "inbound",
                "chunk": "5",
                "timestamp": "100",
                "payload": b64_pcm,
            },
        }
        ws.send_text(json.dumps(gap_media_msg))

        # Send Exotel 'stop' event to conclude call cleanly
        ws.send_text(json.dumps({"event": "stop", "streamSid": f"stream-{session_id}"}))

    # Verify session was ended and cleaned up
    remaining = client.get("/v1/telephony/sessions").json()
    assert not any(s["session_id"] == session_id for s in remaining)
