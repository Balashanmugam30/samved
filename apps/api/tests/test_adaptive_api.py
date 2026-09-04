"""Integration tests for Adaptive Conversation REST API endpoints."""

import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.adaptive.service import adaptive_engine
from app.realtime.session_manager import telephony_session_manager


@pytest.fixture
def client():
    return TestClient(app)


def test_get_adaptive_status(client):
    """GET /v1/adaptive/status returns status, version, and safety boundaries."""
    response = client.get("/v1/adaptive/status")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ready"
    assert data["engine_version"] == "v1.0.0"
    assert data["is_operational_planning_only"] is True
    assert data["safety_precedence_inviolable"] is True
    assert "not a clinical" in data["disclaimer"].lower()


def test_get_adaptive_policy(client):
    """GET /v1/adaptive/policy returns full strategy action catalog and priority rules."""
    response = client.get("/v1/adaptive/policy")
    assert response.status_code == 200
    data = response.json()
    assert data["total_actions"] >= 15
    assert "SAFETY_CHECK" in data["actions"]
    assert "ASK_IMMEDIATE_DANGER" in data["actions"]
    assert "HUMAN_HANDOFF" in data["actions"]
    assert len(data["policy_rules"]) >= 10


def test_post_adaptive_plan(client):
    """POST /v1/adaptive/plan evaluates standalone planning request."""
    payload = {
        "call_id": "api-plan-call",
        "session_id": "api-plan-sess",
        "turn_index": 1,
        "language": "ta-IN",
        "safety_state": "CRITICAL",
        "safety_signals": [{"severity": "CRITICAL", "signal_type": "ACTIVE_VIOLENCE"}],
        "svi_score": 80,
        "svi_band": "CRITICAL",
        "svi_trend": "RISING",
        "acoustic_quality": "GOOD",
        "known_facts": {},
        "last_caller_utterance": "அவன் கத்தியோடு இருக்கிறான்!",
    }
    response = client.post("/v1/adaptive/plan", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["action"] == "ASK_IMMEDIATE_DANGER"
    assert data["priority"] == "P0"
    assert "CRITICAL_SAFETY_PRIORITY" in data["reason_codes"]
    assert data["requires_human_review"] is True


def test_get_call_strategy_not_found(client):
    """GET /v1/adaptive/calls/{call_id} returns 404 for unknown call."""
    response = client.get("/v1/adaptive/calls/non-existent-call-999")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_get_call_strategy_lifecycle(client):
    """Simulates active call, plans strategy, records it, queries /calls/{id} and /history."""
    call_id = "test-ad-call-101"
    session_id = "test-ad-sess-101"

    # Create session
    sess = await telephony_session_manager.create_session(
        session_id=session_id,
        call_id=call_id,
        caller_number="+919876543210",
        provider_call_id="prov-101",
    )

    # Evaluate turn
    strat = adaptive_engine.evaluate_turn(
        call_id=call_id,
        session_id=session_id,
        turn_index=1,
        utterance_text="I need some help with my situation.",
        language="en-IN",
    )
    sess.record_adaptive_strategy(strat)

    # 1. Query latest strategy
    resp_latest = client.get(f"/v1/adaptive/calls/{call_id}")
    assert resp_latest.status_code == 200
    data_latest = resp_latest.json()
    assert data_latest["call_id"] == call_id
    assert data_latest["action"] == strat.action.value

    # 2. Query history
    resp_hist = client.get(f"/v1/adaptive/calls/{call_id}/history")
    assert resp_hist.status_code == 200
    data_hist = resp_hist.json()
    assert data_hist["total_strategies"] >= 1
    assert data_hist["strategies"][0]["action"] == strat.action.value

    # 3. Apply operator override
    override_payload = {
        "action": "operator_force_human",
        "reason": "Counselor manual transfer intervention",
        "operator_id": "operator_lead_5",
    }
    resp_override = client.post(f"/v1/adaptive/calls/{call_id}/override", json=override_payload)
    assert resp_override.status_code == 200
    data_override = resp_override.json()
    assert data_override["action"] == "operator_force_human"
    assert data_override["is_active"] is True
