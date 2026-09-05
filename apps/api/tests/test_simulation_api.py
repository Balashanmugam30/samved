"""REST API integration tests for Phase 14 simulation endpoints."""

import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_simulation_status_endpoint():
    response = client.get("/v1/simulation/status")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["total_scenarios"] >= 20
    assert data["total_drills"] >= 4
    assert "hi-IN" in data["languages_supported"]


def test_list_scenarios_endpoint():
    response = client.get("/v1/simulation/scenarios")
    assert response.status_code == 200
    scenarios = response.json()
    assert isinstance(scenarios, list)
    assert len(scenarios) >= 20

    # Test filtering by band
    crit_resp = client.get("/v1/simulation/scenarios?band=CRITICAL")
    assert crit_resp.status_code == 200
    crit_list = crit_resp.json()
    assert all(s["expected_svi_band"] == "CRITICAL" for s in crit_list)


def test_get_scenario_by_id():
    response = client.get("/v1/simulation/scenarios/SCEN-CRIT-001")
    assert response.status_code == 200
    data = response.json()
    assert data["scenario_id"] == "SCEN-CRIT-001"
    assert data["expected_svi_band"] == "CRITICAL"
    assert len(data["synthetic_dialogue"]) >= 1

    # Not found
    nf = client.get("/v1/simulation/scenarios/SCEN-DOES-NOT-EXIST")
    assert nf.status_code == 404


def test_wer_evaluate_endpoint():
    payload = {
        "reference": "Hello I need immediate assistance",
        "hypothesis": "Hello I need assistance",
    }
    response = client.post("/v1/simulation/wer/evaluate", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "wer" in data
    assert "cer" in data
    assert data["deletions"] == 1
    assert data["hits"] == 4


def test_benchmark_run_trigger_and_retrieve():
    payload = {"suite": "SMOKE"}
    response = client.post("/v1/simulation/benchmark/run", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "COMPLETED"
    assert data["total_scenarios"] >= 8
    run_id = data["run_id"]

    # Retrieve by ID
    get_resp = client.get(f"/v1/simulation/benchmark/runs/{run_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["run_id"] == run_id

    # List runs
    list_resp = client.get("/v1/simulation/benchmark/runs")
    assert list_resp.status_code == 200
    assert len(list_resp.json()) >= 1


def test_training_drills_and_session_flow():
    drills_resp = client.get("/v1/simulation/training/drills")
    assert drills_resp.status_code == 200
    drills = drills_resp.json()
    assert len(drills) >= 4

    # Start session
    start_payload = {
        "drill_key": "DRILL-OVERDOSE-001",
        "trainee_id": "T-3001",
        "trainee_name": "Trainee Anand",
    }
    session_resp = client.post("/v1/simulation/training/session/start", json=start_payload)
    assert session_resp.status_code == 200
    session_data = session_resp.json()
    session_id = session_data["session_id"]
    assert session_data["status"] == "ACTIVE"

    # Submit turn
    turn_payload = {
        "trainee_input": "Stay calm, I am here with you. Please turn him on his side in recovery position immediately while I coordinate the emergency ambulance.",
    }
    turn_resp = client.post(f"/v1/simulation/training/session/{session_id}/turn", json=turn_payload)
    assert turn_resp.status_code == 200
    turn_data = turn_resp.json()
    assert turn_data["turn_number"] == 1
    assert turn_data["score"] >= 75.0
    assert len(turn_data["feedback_hints"]) >= 1

    # Get session
    get_sess = client.get(f"/v1/simulation/training/session/{session_id}")
    assert get_sess.status_code == 200
    assert get_sess.json()["session_id"] == session_id
