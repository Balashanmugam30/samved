import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.realtime.session_manager import telephony_session_manager


@pytest.fixture
def client():
    return TestClient(app)


def test_get_svi_status(client):
    response = client.get("/v1/svi/status")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ready"
    assert data["engine_version"] == "v1"
    assert data["deterministic"] is True
    assert data["llm_independent"] is True
    assert data["acoustic_evidence_available"] is False
    assert "Phase 6 deferred" in data["acoustic_evidence_note"]
    assert "NOT a clinical" in data["disclaimer"]


def test_get_svi_rules(client):
    response = client.get("/v1/svi/rules")
    assert response.status_code == 200
    data = response.json()
    assert data["version"] == "v1"
    assert "categories" in data
    assert "immediate_safety" in data["categories"]
    assert "coercion_control" in data["categories"]
    assert "distress_overwhelm" in data["categories"]


def test_post_svi_evaluate_standalone(client):
    payload = {
        "call_id": "test-call-api",
        "session_id": "test-sess-api",
        "turn_index": 2,
        "turns": [
            {"speaker": "caller", "text": "He locked me inside the room and took my phone.", "language": "en-IN"},
            {"speaker": "caller", "text": "I am panicking and extremely scared, no one to help.", "language": "en-IN"},
        ],
        "previous_score": 10,
    }
    response = client.post("/v1/svi/evaluate", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert 0 <= data["score"] <= 100
    assert data["score"] > 25
    assert data["band"] in ("MODERATE", "HIGH", "CRITICAL")
    assert data["trend"] == "RISING"
    assert data["delta"] > 0
    assert len(data["features"]) >= 2
    assert len(data["top_contributors"]) >= 1
    assert data["acoustic_evidence_available"] is False
    assert "Phase 6 deferred" in data["acoustic_evidence_note"]


@pytest.mark.asyncio
async def test_svi_call_endpoints(client):
    # Test 404 for unknown call
    resp_404 = client.get("/v1/svi/calls/non-existent-call")
    assert resp_404.status_code == 404

    resp_hist_404 = client.get("/v1/svi/calls/non-existent-call/history")
    assert resp_hist_404.status_code == 404

    # Create active session and record SVI
    session = await telephony_session_manager.create_session(
        session_id="sess-svi-test-01",
        call_id="call-svi-test-01",
        provider_call_id="exotel-svi-01",
        caller_number="+919876543210",
        attach_ai=False,
    )
    from app.schemas.svi import SVIAssessment, SVIBand, SVITrend
    assessment = SVIAssessment(
        call_id="call-svi-test-01",
        session_id=session.session_id,
        turn_index=1,
        score=65,
        band=SVIBand.HIGH,
        trend=SVITrend.RISING,
        delta=15,
        assessment_completeness=0.6,
        requires_human_review=True,
    )
    session.record_svi_assessment(assessment)

    # Test GET /v1/svi/calls/{call_id}
    resp_get = client.get(f"/v1/svi/calls/{session.call_id}")
    assert resp_get.status_code == 200
    data_get = resp_get.json()
    assert data_get["score"] == 65
    assert data_get["band"] == "HIGH"
    assert data_get["requires_human_review"] is True

    # Test GET /v1/svi/calls/{call_id}/history
    resp_hist = client.get(f"/v1/svi/calls/{session.call_id}/history")
    assert resp_hist.status_code == 200
    data_hist = resp_hist.json()
    assert data_hist["total_assessments"] == 1
    assert data_hist["latest_assessment"]["score"] == 65
