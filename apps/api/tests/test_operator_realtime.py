"""Realtime WebSocket and event broadcast tests for Operator Workstation."""

import json
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.operator.models import OperatorNoteCategory
from app.operator.service import operator_service
from app.realtime.session_manager import telephony_session_manager


@pytest.fixture
def client():
    return TestClient(app)


def test_operator_websocket_snapshot(client):
    """Connecting to /ws/operator delivers immediate initial snapshot with system metadata."""
    with client.websocket_connect("/ws/operator") as ws:
        data = ws.receive_json()
        assert data["event_type"] == "OPERATOR_SNAPSHOT"
        payload = data["payload"]
        assert "system_mode" in payload
        assert "active_calls" in payload
        assert "recent_calls" in payload


@pytest.mark.asyncio
async def test_operator_action_realtime_broadcast():
    """Operator action triggers event broadcast through operator service."""
    call_id = "realtime-op-call"
    session = await telephony_session_manager.create_session(
        session_id="realtime-op-sess",
        call_id=call_id,
        provider_call_id="exotel-rt-1",
        caller_number="+919876543210",
        attach_ai=False,
    )

    try:
        # Take over call
        state = await operator_service.takeover(call_id, operator_id="op-test", reason="Supervision")
        assert state.ownership_state.value == "HUMAN_ACTIVE"

        # Check session recorded the event
        sess = await telephony_session_manager.get_by_call_id(call_id)
        assert sess is not None
        assert sess.operator_ownership_state == "HUMAN_ACTIVE"

        # Add note
        note = await operator_service.add_note(call_id, "op-test", OperatorNoteCategory.SAFETY, "Realtime test note")
        assert sess.operator_notes_count >= 1

        # Pause adaptive
        await operator_service.pause_adaptive(call_id, "op-test", "Realtime pause")
        assert sess.adaptive_paused is True

    finally:
        await telephony_session_manager.end_session(session.session_id)
