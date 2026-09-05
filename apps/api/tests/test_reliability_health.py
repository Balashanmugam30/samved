"""SAMVED Phase 16: Readiness, Liveness, and Operations API Tests."""

import pytest


def test_kubernetes_probes(client):
    # Liveness Probes
    res_healthz = client.get("/healthz")
    assert res_healthz.status_code == 200
    assert res_healthz.json()["status"] == "healthy"

    res_live = client.get("/health/live")
    assert res_live.status_code == 200
    assert res_live.json()["status"] == "healthy"

    # Readiness Probes
    res_ready = client.get("/ready")
    assert res_ready.status_code == 200
    assert res_ready.json()["ready"] is True

    res_health_ready = client.get("/health/ready")
    assert res_health_ready.status_code == 200
    assert res_health_ready.json()["ready"] is True

    # Startup Probe
    res_startup = client.get("/health/startup")
    assert res_startup.status_code == 200
    assert res_startup.json()["status"] == "started"


def test_operations_status_endpoint(client):
    response = client.get("/v1/operations/status")
    assert response.status_code == 200
    data = response.json()
    assert data["service"] == "samved-api"
    assert data["version"] == "1.0.0-sih2026"
    assert "telephony" in data
    assert "realtime_websockets" in data
    assert "security_governance" in data
    assert "circuit_breakers" in data
    assert len(data["circuit_breakers"]) >= 5


def test_operations_circuit_controls(client):
    # List circuits
    list_res = client.get("/v1/operations/circuits")
    assert list_res.status_code == 200
    circuits = list_res.json()
    assert isinstance(circuits, list)
    assert any(c["name"] == "sarvam-stt" for c in circuits)

    # Reset single circuit
    reset_single = client.post("/v1/operations/circuits/sarvam-stt/reset")
    assert reset_single.status_code == 200
    assert reset_single.json()["circuit"]["state"] == "CLOSED"

    # Reset all circuits
    reset_all = client.post("/v1/operations/circuits/reset-all")
    assert reset_all.status_code == 200
    assert "reset to operational" in reset_all.json()["message"]
