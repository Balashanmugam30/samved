"""
Integration tests for the SAMVED Phase 14 Evaluation Lab REST API.
"""

import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_api_evaluation_status():
    res = client.get("/v1/evaluation/status")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ready"
    assert data["scenarios_count"] >= 17
    assert "SYNTHETIC EVALUATION ENVIRONMENT" in data["disclaimer"]


def test_api_list_scenarios():
    res = client.get("/v1/evaluation/scenarios")
    assert res.status_code == 200
    data = res.json()
    assert data["total"] >= 17
    assert len(data["scenarios"]) >= 17


def test_api_get_scenario_by_id():
    res = client.get("/v1/evaluation/scenarios/SCEN-GEN-001")
    assert res.status_code == 200
    data = res.json()
    assert data["scenario_id"] == "SCEN-GEN-001"
    assert len(data["turns"]) >= 2
    assert "expected" in data


def test_api_trigger_run():
    payload = {
        "scenario_id": "SCEN-GEN-001",
        "mode": "OFFLINE",
        "seed": 42,
    }
    res = client.post("/v1/evaluation/runs", json=payload)
    assert res.status_code == 201
    run_data = res.json()
    assert run_data["scenario_id"] == "SCEN-GEN-001"
    assert "run_id" in run_data
    assert "metrics" in run_data
    assert "assertions" in run_data

    run_id = run_data["run_id"]
    get_res = client.get(f"/v1/evaluation/runs/{run_id}")
    assert get_res.status_code == 200
    assert get_res.json()["run_id"] == run_id


def test_api_cancel_run():
    payload = {"scenario_id": "SCEN-GEN-001", "mode": "OFFLINE", "seed": 42}
    create_res = client.post("/v1/evaluation/runs", json=payload)
    assert create_res.status_code == 201
    run_id = create_res.json()["run_id"]

    cancel_res = client.post(f"/v1/evaluation/runs/{run_id}/cancel")
    assert cancel_res.status_code == 200
    assert cancel_res.json()["status"] == "CANCELLED"


def test_api_trigger_suite():
    payload = {"suite_id": "smoke", "mode": "OFFLINE", "seed": 42}
    res = client.post("/v1/evaluation/suites/run", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["suite_id"] == "smoke"
    assert data["total_scenarios"] > 0
    assert len(data["runs"]) > 0


def test_api_baselines_and_diff():
    # 1. Run scenario
    run_res = client.post("/v1/evaluation/runs", json={"scenario_id": "SCEN-GEN-001", "seed": 42})
    assert run_res.status_code == 201
    run_id = run_res.json()["run_id"]

    # 2. Capture baseline
    base_res = client.post("/v1/evaluation/baselines", json={"run_id": run_id, "tag": "test-v1"})
    assert base_res.status_code == 201
    baseline_id = base_res.json()["baseline_id"]

    # 3. List baselines
    list_res = client.get("/v1/evaluation/baselines")
    assert list_res.status_code == 200
    assert list_res.json()["total"] > 0

    # 4. Compute diff
    diff_res = client.post("/v1/evaluation/diff", json={"current_run_id": run_id, "baseline_id": baseline_id})
    assert diff_res.status_code == 200
    diff_data = diff_res.json()
    assert diff_data["has_regression"] is False
