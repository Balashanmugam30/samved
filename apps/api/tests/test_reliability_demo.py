"""SAMVED Phase 16: SIH Demo Mode & Flagship Scenario Contract Tests."""

import pytest
from app.demo.catalog import FLAGSHIP_SCENARIO_ID, FLAGSHIP_TAMIL_ENG_SCENARIO


def test_demo_status_endpoint(client):
    response = client.get("/v1/demo/status")
    assert response.status_code == 200
    data = response.json()
    assert data["demo_mode_enabled"] is True
    assert data["flagship_scenario_id"] == FLAGSHIP_SCENARIO_ID
    assert "Tamil/English" in data["flagship_scenario_title"]
    assert data["available_scenarios_count"] >= 1
    assert data["is_safe_to_reset"] is True


def test_demo_flagship_scenario_specification(client):
    response = client.get("/v1/demo/flagship")
    assert response.status_code == 200
    data = response.json()
    assert data["scenario_id"] == FLAGSHIP_SCENARIO_ID
    assert "ta-IN / en-IN" in data["language_pair"]
    assert len(data["dialogue"]) == 3
    assert "IMMINENT_VIOLENCE" in data["expected_safety_triggers"]
    assert "WEAPON_INVOLVED" in data["expected_safety_triggers"]
    assert data["expected_svi"]["score"] == 88
    assert data["expected_svi"]["band"] == "CRITICAL"
    assert data["expected_protocol"] == "P0_EMERGENCY_DISPATCH_ASSIST"
    assert len(data["expected_rag_citations"]) >= 3


def test_demo_flagship_replay_pipeline(client):
    response = client.post("/v1/demo/flagship/replay")
    assert response.status_code == 200
    data = response.json()
    assert data["scenario_id"] == FLAGSHIP_SCENARIO_ID
    assert data["svi_score"] == 88
    assert data["svi_band"] == "CRITICAL"
    assert data["protocol_activated"] == "P0_EMERGENCY_DISPATCH_ASSIST"
    assert data["warm_transfer_ready"] is True
    assert len(data["stages"]) == 8

    # Assert specific stages exist in sequence
    stage_names = [s["stage_name"] for s in data["stages"]]
    assert "Multilingual Speech Ingestion & Code-Switching ASR" in stage_names[0]
    assert "Crisis Intent & Safety Screening" in stage_names[1]
    assert "Statistical Vulnerability Index (SVI) Assessment" in stage_names[2]
    assert "Adaptive Policy Selection" in stage_names[3]
    assert "Tele-Counselor Warm Transfer Synthesis" in stage_names[4]
    assert "Statutory RAG Grounding & Local Referral" in stage_names[5]
    assert "Case Intelligence & Entity Graph Linkage" in stage_names[6]
    assert "Cryptographic Audit Seal & Tamper Evident Log" in stage_names[7]

    # Verify cryptographic audit hash in result
    assert "audit_event_hash" in data
    assert len(data["audit_event_hash"]) == 64


def test_demo_reset_and_seed(client):
    # Seed call
    seed_res = client.post("/v1/demo/seed")
    assert seed_res.status_code == 200
    assert seed_res.json()["status"] == "SEEDED"

    # Reset call
    reset_res = client.post("/v1/demo/reset")
    assert reset_res.status_code == 200
    r_data = reset_res.json()
    assert r_data["status"] == "RESET_COMPLETE"
    assert r_data["demo_mode_enabled"] is True
