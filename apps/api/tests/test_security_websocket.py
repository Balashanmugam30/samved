"""SAMVED Phase 15: WebSocket Security & Frame Protection Tests.

Tests WebSocket connection authentication context, frame size constraints (64KB), and rate limiting.
"""

import json
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.realtime.operator_ws_router import MAX_WS_FRAME_BYTES


@pytest.fixture
def client():
    return TestClient(app)


def test_operator_ws_initial_snapshot_includes_role(client):
    """Verifies that connecting to /ws/operator includes security role context in initial snapshot."""
    with client.websocket_connect("/ws/operator?role=SUPERVISOR&user_id=sup-ws-1") as ws:
        msg = ws.receive_text()
        data = json.loads(msg)
        assert data["event_type"] == "OPERATOR_SNAPSHOT"
        assert data["payload"]["role"] == "SUPERVISOR"


def test_operator_ws_frame_size_protection(client):
    """Verifies that oversized frames (>64KB) are rejected with SECURITY_RATE_LIMITED event."""
    with client.websocket_connect("/ws/operator?user_id=oversize-test") as ws:
        # Consume initial snapshot
        ws.receive_text()

        # Generate payload larger than 64KB
        oversized = "A" * (MAX_WS_FRAME_BYTES + 1024)
        ws.send_text(oversized)

        err_msg = ws.receive_text()
        err_data = json.loads(err_msg)
        assert err_data["event_type"] == "SECURITY_RATE_LIMITED"
        assert err_data["payload"]["error"] == "FRAME_SIZE_EXCEEDED"


def test_operator_ws_rate_limiting(client):
    """Verifies that sending rapid frames in a tight loop triggers rate limiting."""
    with client.websocket_connect("/ws/operator?user_id=flooder-ws") as ws:
        ws.receive_text()  # Consume initial snapshot

        rate_limited = False
        # Send 15 messages quickly (limit is 10/sec)
        for i in range(15):
            ws.send_text(json.dumps({"action": "PING"}))
            resp = ws.receive_text()
            data = json.loads(resp)
            if data["event_type"] == "SECURITY_RATE_LIMITED":
                rate_limited = True
                assert data["payload"]["error"] == "RATE_LIMITED"
                break

        assert rate_limited is True
