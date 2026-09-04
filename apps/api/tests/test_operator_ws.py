import json
import uuid
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.realtime.connection_manager import manager
from app.realtime.session_manager import telephony_session_manager
from app.schemas.events import EventEnvelope, EventType


@pytest.fixture
def client():
    return TestClient(app)


def test_operator_ws_initial_snapshot_and_ping(client):
    """Verifies that connecting to /ws/operator sends an initial snapshot and responds to ping."""
    with client.websocket_connect("/ws/operator") as ws:
        # 1. Receive initial snapshot
        raw_msg = ws.receive_text()
        snapshot = json.loads(raw_msg)
        assert snapshot["event_type"] == "OPERATOR_SNAPSHOT"
        assert "active_calls" in snapshot["payload"]
        assert "recent_calls" in snapshot["payload"]
        assert "system_mode" in snapshot["payload"]

        # 2. Send PING action
        ws.send_text(json.dumps({"action": "PING"}))
        pong_msg = ws.receive_text()
        pong = json.loads(pong_msg)
        assert pong["event_type"] == "HEARTBEAT_PONG"
        assert pong["payload"]["status"] == "alive"


def test_operator_ws_malformed_json_resilience(client):
    """Verifies that sending malformed JSON does not crash or disconnect the operator socket."""
    with client.websocket_connect("/ws/operator") as ws:
        # Consume snapshot
        ws.receive_text()

        # Send invalid JSON
        ws.send_text("THIS IS NOT JSON {}}")
        err_msg = ws.receive_text()
        err_data = json.loads(err_msg)
        assert err_data["payload"]["error"] == "MALFORMED_JSON"

        # Connection is still alive - can ping
        ws.send_text(json.dumps({"action": "PING"}))
        pong = json.loads(ws.receive_text())
        assert pong["event_type"] == "HEARTBEAT_PONG"


@pytest.mark.asyncio
async def test_operator_subscription_and_cross_call_isolation(client):
    """Verifies that SUBSCRIBE_CALL isolates events so Operator B never sees Operator A's call events."""
    call_a = f"call-iso-a-{uuid.uuid4().hex[:6]}"
    call_b = f"call-iso-b-{uuid.uuid4().hex[:6]}"

    with client.websocket_connect(f"/ws/operator?call_id={call_a}") as ws_a:
        # Consume A's initial snapshot
        snap_a = json.loads(ws_a.receive_text())
        assert snap_a["event_type"] == "OPERATOR_SNAPSHOT"

        with client.websocket_connect(f"/ws/operator?call_id={call_b}") as ws_b:
            # Consume B's initial snapshot
            snap_b = json.loads(ws_b.receive_text())
            assert snap_b["event_type"] == "OPERATOR_SNAPSHOT"

            # Broadcast event targeted to Call A
            event_a = EventEnvelope(
                event_type=EventType.TRANSCRIPT_FINAL,
                session_id="session-a",
                call_id=call_a,
                payload={"text": "Hello from Call A", "speaker": "caller"},
            )
            await manager.broadcast_to_operators(event_a)

            # ws_a must receive event_a
            received_a = json.loads(ws_a.receive_text())
            assert received_a["call_id"] == call_a
            assert received_a["payload"]["text"] == "Hello from Call A"

            # Now send ping to ws_b to verify ws_b queue only has its own pong and didn't receive event_a
            ws_b.send_text(json.dumps({"action": "PING"}))
            received_b = json.loads(ws_b.receive_text())
            assert received_b["event_type"] == "HEARTBEAT_PONG"


@pytest.mark.asyncio
async def test_operator_dynamic_subscription_switch_and_all(client):
    """Verifies that an operator can switch from specific call to SUBSCRIBE_ALL dynamically."""
    call_x = f"call-x-{uuid.uuid4().hex[:6]}"
    call_y = f"call-y-{uuid.uuid4().hex[:6]}"

    with client.websocket_connect("/ws/operator") as ws:
        # Initial snapshot
        snap = json.loads(ws.receive_text())
        assert snap["event_type"] == "OPERATOR_SNAPSHOT"

        # 1. Subscribe specifically to call_x
        ws.send_text(json.dumps({"action": "SUBSCRIBE_CALL", "call_id": call_x}))
        ack = json.loads(ws.receive_text())
        assert ack["payload"]["action_ack"] == "SUBSCRIBE_CALL"
        assert ack["payload"]["subscribed_call_id"] == call_x

        # Broadcast event for call_y -> should not be received
        await manager.broadcast_to_operators(
            EventEnvelope(
                event_type=EventType.TRANSCRIPT_PARTIAL,
                session_id="sess-y",
                call_id=call_y,
                payload={"text": "Draft for Y"},
            )
        )

        # Broadcast event for call_x -> should be received
        await manager.broadcast_to_operators(
            EventEnvelope(
                event_type=EventType.TRANSCRIPT_PARTIAL,
                session_id="sess-x",
                call_id=call_x,
                payload={"text": "Draft for X"},
            )
        )
        msg_x = json.loads(ws.receive_text())
        assert msg_x["call_id"] == call_x
        assert msg_x["payload"]["text"] == "Draft for X"

        # 2. Switch to SUBSCRIBE_ALL
        ws.send_text(json.dumps({"action": "SUBSCRIBE_ALL"}))
        ack_all = json.loads(ws.receive_text())
        assert ack_all["payload"]["action_ack"] == "SUBSCRIBE_ALL"

        # Now broadcast for call_y -> should be received!
        await manager.broadcast_to_operators(
            EventEnvelope(
                event_type=EventType.TRANSCRIPT_FINAL,
                session_id="sess-y",
                call_id=call_y,
                payload={"text": "Final for Y"},
            )
        )
        msg_y = json.loads(ws.receive_text())
        assert msg_y["call_id"] == call_y
        assert msg_y["payload"]["text"] == "Final for Y"

