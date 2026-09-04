"""Integration tests for Operator Workstation REST API endpoints."""

import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.realtime.session_manager import telephony_session_manager


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
async def setup_call():
    session = await telephony_session_manager.create_session(
        session_id="api-test-op-sess",
        call_id="api-test-op-call",
        provider_call_id="exotel-test-op-1",
        caller_number="+919876543210",
        attach_ai=False,
    )
    yield session
    await telephony_session_manager.end_session("api-test-op-sess")


def test_operator_status_api(client):
    """GET /v1/operator/status returns subsystem health and active counts."""
    response = client.get("/v1/operator/status")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert len(data["subsystems"]) == 5
    assert any(s["name"] == "Safety Engine" for s in data["subsystems"])


@pytest.mark.asyncio
async def test_operator_call_endpoints(client, setup_call):
    """Full lifecycle of operator actions via REST API."""
    call_id = "api-test-op-call"

    # 1. GET /v1/operator/calls
    res = client.get("/v1/operator/calls")
    assert res.status_code == 200
    calls_data = res.json()
    assert calls_data["total_active"] >= 1

    # 2. GET /v1/operator/calls/{id}
    res = client.get(f"/v1/operator/calls/{call_id}")
    assert res.status_code == 200
    assert res.json()["call_id"] == call_id

    # 3. POST /v1/operator/calls/{id}/takeover
    res = client.post(f"/v1/operator/calls/{call_id}/takeover", json={"reason": "Test takeover", "operator_id": "op-42"})
    assert res.status_code == 200
    data = res.json()
    assert data["action"] == "TAKEOVER"
    assert data["ownership_state"] == "HUMAN_ACTIVE"

    # 4. POST /v1/operator/calls/{id}/pause
    res = client.post(f"/v1/operator/calls/{call_id}/pause", json={"reason": "Test pause", "operator_id": "op-42"})
    assert res.status_code == 200
    assert res.json()["action"] == "PAUSE_ADAPTIVE"

    # 5. POST /v1/operator/calls/{id}/resume
    res = client.post(f"/v1/operator/calls/{call_id}/resume", json={"reason": "Test resume", "operator_id": "op-42"})
    assert res.status_code == 200
    assert res.json()["action"] == "RESUME_ADAPTIVE"

    # 6. POST /v1/operator/calls/{id}/safety-check
    res = client.post(f"/v1/operator/calls/{call_id}/safety-check", json={"reason": "Urgent review", "operator_id": "op-42"})
    assert res.status_code == 200
    assert res.json()["status"] == "SAFETY_CHECK_REQUESTED"

    # 7. POST /v1/operator/calls/{id}/notes
    res = client.post(
        f"/v1/operator/calls/{call_id}/notes",
        json={"category": "SAFETY", "text": "Victim confirms door is barred", "operator_id": "op-42"},
    )
    assert res.status_code == 200
    note = res.json()
    assert note["category"] == "SAFETY"
    assert note["text"] == "Victim confirms door is barred"

    # 8. GET /v1/operator/calls/{id}/notes
    res = client.get(f"/v1/operator/calls/{call_id}/notes")
    assert res.status_code == 200
    notes_data = res.json()
    assert notes_data["total_notes"] >= 1

    # 9. GET /v1/operator/calls/{id}/timeline
    res = client.get(f"/v1/operator/calls/{call_id}/timeline")
    assert res.status_code == 200
    timeline = res.json()
    assert timeline["total_events"] >= 1

    # 10. POST /v1/operator/calls/{id}/handoff
    res = client.post(
        f"/v1/operator/calls/{call_id}/handoff",
        json={"target_department": "crisis_tier2", "notes": "High distress caller", "operator_id": "op-42"},
    )
    assert res.status_code == 200
    assert res.json()["handoff_status"] == "REQUESTED"

    # 11. POST /v1/operator/calls/{id}/handoff/confirm
    res = client.post(
        f"/v1/operator/calls/{call_id}/handoff/confirm",
        json={"transfer_confirmed_by": "supervisor-01", "target_agent": "counselor-meena"},
    )
    assert res.status_code == 200
    assert res.json()["handoff_status"] == "CONFIRMED"

    # 12. POST /v1/operator/calls/{id}/end
    res = client.post(f"/v1/operator/calls/{call_id}/end", json={"reason": "Handoff complete", "operator_id": "op-42"})
    assert res.status_code == 200
    assert res.json()["ownership_state"] == "ENDED"
