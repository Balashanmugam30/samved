"""Tests for Orchestration REST API endpoints in SAMVED Phase 9."""

import uuid
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.realtime.session_manager import telephony_session_manager


@pytest.fixture
def client():
    return TestClient(app)


def test_get_orchestration_status(client):
    res = client.get("/v1/orchestration/status")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "healthy"
    assert data["registered_agents_count"] >= 6
    assert data["human_supervision_active"] is True
    assert data["deterministic_safety_authoritative"] is True


def test_list_agents(client):
    res = client.get("/v1/orchestration/agents")
    assert res.status_code == 200
    agents = res.json()
    assert isinstance(agents, list)
    assert len(agents) >= 6
    agent_names = [a["name"] for a in agents]
    assert "safety_context_agent" in agent_names
    assert "operator_briefing_agent" in agent_names


def test_plan_orchestration(client):
    res = client.post("/v1/orchestration/plan", json={"task_type": "turn_triage", "safety_state": "CRITICAL"})
    assert res.status_code == 200
    plan = res.json()
    assert "stage_1" in plan
    assert "stage_2" in plan
    assert "safety_context_agent" in plan["stage_1"]
    assert "operator_briefing_agent" in plan["stage_2"]


@pytest.mark.asyncio
async def test_call_orchestration_refresh_and_history(client):
    call_id = f"test-call-orch-{uuid.uuid4().hex[:6]}"
    session_id = f"test-sess-orch-{uuid.uuid4().hex[:6]}"

    # Create active session
    await telephony_session_manager.create_session(
        session_id=session_id,
        call_id=call_id,
        provider_call_id="exo-123",
        caller_number="+919876543210",
        provider="mock",
    )

    # 1. Check initial call get (404 before any run)
    res = client.get(f"/v1/orchestration/calls/{call_id}")
    assert res.status_code == 404

    # 2. Trigger manual refresh
    res_refresh = client.post(f"/v1/orchestration/calls/{call_id}/refresh")
    assert res_refresh.status_code == 200
    orch_data = res_refresh.json()
    assert orch_data["call_id"] == call_id
    assert orch_data["state"] in ("COMPLETED", "DEGRADED")
    assert orch_data["briefing"] is not None

    # 3. Check get latest call orchestration (now 200)
    res_get = client.get(f"/v1/orchestration/calls/{call_id}")
    assert res_get.status_code == 200
    assert res_get.json()["call_id"] == call_id

    # 4. Check get history
    res_hist = client.get(f"/v1/orchestration/calls/{call_id}/history")
    assert res_hist.status_code == 200
    history = res_hist.json()
    assert len(history) >= 1
    assert history[0]["call_id"] == call_id
