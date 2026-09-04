import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.realtime.session_manager import telephony_session_manager


@pytest.fixture
def client():
    return TestClient(app)


def test_safety_status_endpoint(client):
    """Verify /v1/safety/status returns operational readiness and metadata."""
    res = client.get("/v1/safety/status")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ready"
    assert data["engine_version"] == "v1"
    assert data["rules_loaded_count"] >= 6
    assert data["deterministic"] is True
    assert data["llm_independent"] is True
    assert "ethical_boundary" in data


def test_safety_rules_catalog_endpoint(client):
    """Verify /v1/safety/rules returns full versioned rule catalog with negative examples."""
    res = client.get("/v1/safety/rules")
    assert res.status_code == 200
    data = res.json()
    assert data["rules_version"] == "v1"
    assert data["total_rules"] >= 6
    rules = data["rules"]
    assert any("active_threat" in r["rule_id"].lower() for r in rules)
    assert any("weapon" in r["rule_id"].lower() for r in rules)
    # Check that negative examples exist for explainability
    for r in rules:
        assert "negative_examples" in r
        assert "default_severity" in r


def test_safety_evaluate_endpoint_threat(client):
    """Verify /v1/safety/evaluate produces explicit signals on acute threats."""
    payload = {
        "utterance_text": "He is breaking the door and threatening to kill me right now!",
        "language": "en-IN",
        "call_id": "test-call-threat",
    }
    res = client.post("/v1/safety/evaluate", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["highest_severity"] in ("HIGH", "CRITICAL")
    assert data["requires_human_review"] is True
    assert len(data["signals"]) > 0
    assert any("active_threat" in s["rule_id"].lower() for s in data["signals"])
    assert data["signals"][0]["requires_human_review"] is True
    assert "door" in data["signals"][0]["evidence"]["matched_phrase"] or "breaking" in data["signals"][0]["evidence"]["matched_phrase"]


def test_safety_evaluate_endpoint_negation(client):
    """Verify /v1/safety/evaluate correctly honors negation to avoid false positive."""
    payload = {
        "utterance_text": "There is no weapon here, he does not have a knife",
        "language": "en-IN",
        "call_id": "test-call-negated",
    }
    res = client.post("/v1/safety/evaluate", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["highest_severity"] == "NONE"
    assert data["requires_human_review"] is False
    assert len(data["signals"]) == 0


@pytest.mark.asyncio
async def test_safety_calls_and_acknowledge_flow(client):
    """Verify call safety status retrieval and operator human-in-the-loop acknowledgment."""
    # 1. Create a session in telephony_session_manager
    session = await telephony_session_manager.create_session(
        session_id="sess-ack-test",
        call_id="call-ack-test-123",
        provider_call_id="prov-ack-test-123",
        caller_number="+919876543210",
        provider="exotel",
        attach_ai=False,
    )
    call_id = session.call_id

    # 2. Ingest an utterance that triggers a safety signal
    from app.schemas.events import EventEnvelope, EventType
    sig_id = "sig-test-999"
    signal_event = EventEnvelope(
        event_type=EventType.SAFETY_SIGNAL,
        call_id=call_id,
        session_id=session.session_id,
        payload={
            "call_id": call_id,
            "session_id": session.session_id,
            "signal_id": sig_id,
            "signal_type": "ACTIVE_THREAT",
            "severity": "HIGH",
            "rule_id": "active_threats",
            "rule_version": "v1",
            "reason": "Active physical threat detected",
            "matched_phrase": "hitting me",
            "requires_human_review": True,
            "acknowledged": False,
        },
    )
    session.record_event(signal_event)

    # 3. Retrieve safety info via GET /v1/safety/calls/{call_id}
    res = client.get(f"/v1/safety/calls/{call_id}")
    assert res.status_code == 200
    data = res.json()
    assert data["call_id"] == call_id
    assert data["safety_signals_count"] == 1
    assert data["safety_signals"][0]["signal_id"] == sig_id
    assert data["safety_signals"][0].get("acknowledged") is False

    # 4. Acknowledge the signal via POST /v1/safety/calls/{call_id}/acknowledge
    ack_res = client.post(
        f"/v1/safety/calls/{call_id}/acknowledge",
        json={"signal_id": sig_id, "acknowledged_by": "operator_sita"},
    )
    assert ack_res.status_code == 200
    ack_data = ack_res.json()
    assert ack_data["status"] == "acknowledged"
    assert ack_data["signal"]["acknowledged"] is True
    assert ack_data["signal"]["acknowledged_by"] == "operator_sita"
    assert "acknowledged_at" in ack_data["signal"]

    # 5. Clean up session
    await telephony_session_manager.end_session(session.session_id)


def test_safety_call_not_found(client):
    """Verify 404 on non-existent call."""
    res = client.get("/v1/safety/calls/non-existent-call-id")
    assert res.status_code == 404
