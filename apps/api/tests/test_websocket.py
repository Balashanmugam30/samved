import json
import uuid
from app.schemas.events import EventType


def test_websocket_connect_and_welcome(client):
    with client.websocket_connect("/ws?session_id=test-sess-001") as websocket:
        welcome_data = websocket.receive_json()
        assert welcome_data["event_type"] == EventType.CALL_CONNECTED.value
        assert welcome_data["session_id"] == "test-sess-001"
        assert welcome_data["schema_version"] == "1.0"
        assert welcome_data["payload"]["status"] == "connected"


def test_websocket_heartbeat_ping_pong(client):
    with client.websocket_connect("/ws?session_id=test-sess-ping") as websocket:
        # Read welcome message
        _ = websocket.receive_json()

        ping_event_id = str(uuid.uuid4())
        ping_payload = {
            "event_id": ping_event_id,
            "event_type": EventType.HEARTBEAT_PING.value,
            "schema_version": "1.0",
            "session_id": "test-sess-ping",
            "call_id": "call-ping-1",
            "payload": {},
        }
        websocket.send_text(json.dumps(ping_payload))

        pong_data = websocket.receive_json()
        assert pong_data["event_type"] == EventType.HEARTBEAT_PONG.value
        assert pong_data["session_id"] == "test-sess-ping"
        assert pong_data["payload"]["reply_to"] == ping_event_id


def test_websocket_malformed_json_handling(client):
    with client.websocket_connect("/ws?session_id=test-sess-malformed") as websocket:
        # Read welcome
        _ = websocket.receive_json()

        websocket.send_text("this is not valid json")
        err_data = websocket.receive_json()
        assert err_data["event_type"] == EventType.HUMAN_ALERT.value
        assert err_data["payload"]["error"] == "MALFORMED_JSON"


def test_websocket_invalid_schema_handling(client):
    with client.websocket_connect("/ws?session_id=test-sess-invalidschema") as websocket:
        # Read welcome
        _ = websocket.receive_json()

        # Missing required field event_type
        bad_envelope = {"session_id": "test-sess", "call_id": "call-1"}
        websocket.send_text(json.dumps(bad_envelope))

        err_data = websocket.receive_json()
        assert err_data["event_type"] == EventType.HUMAN_ALERT.value
        assert err_data["payload"]["error"] == "INVALID_SCHEMA"


def test_websocket_structured_event_echo(client):
    with client.websocket_connect("/ws?session_id=test-sess-event") as websocket:
        # Read welcome
        _ = websocket.receive_json()

        svi_event = {
            "event_id": str(uuid.uuid4()),
            "event_type": EventType.SVI_UPDATED.value,
            "schema_version": "1.0",
            "session_id": "test-sess-event",
            "call_id": "call-echo-1",
            "payload": {
                "score": 42,
                "band": "MODERATE",
                "confidence": 0.88,
                "is_clinical_diagnosis": False,
            },
        }
        websocket.send_text(json.dumps(svi_event))

        received_event = websocket.receive_json()
        assert received_event["event_type"] == EventType.SVI_UPDATED.value
        assert received_event["payload"]["score"] == 42
        assert received_event["payload"]["band"] == "MODERATE"
