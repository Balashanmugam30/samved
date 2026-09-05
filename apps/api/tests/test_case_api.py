"""Test suite for Case Intelligence REST API endpoints (Phase 11)."""

import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_api_case_status():
    resp = client.get("/v1/cases/status")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "READY"
    assert data["total_cases"] >= 1


def test_api_create_and_get_case():
    payload = {
        "call_id": "call-api-test-01",
        "case_number": "CAS-API-001",
        "primary_language": "en-IN",
        "operator_id": "op_test",
        "initial_notes": "Caller requested information on counseling.",
    }
    create_resp = client.post("/v1/cases", json=payload)
    assert create_resp.status_code == 201
    case_data = create_resp.json()
    assert case_data["case_number"] == "CAS-API-001"
    case_id = case_data["case_id"]

    # Get by case_id
    get_resp = client.get(f"/v1/cases/{case_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["case_id"] == case_id

    # Get by call_id
    by_call_resp = client.get(f"/v1/cases/by-call/call-api-test-01")
    assert by_call_resp.status_code == 200
    assert by_call_resp.json()["case_id"] == case_id


def test_api_add_entity_and_relationship():
    # Use default seeded case
    case_id = "case-1001"

    # Add entity
    ent_payload = {
        "type": "PERSON",
        "label": "Deepa",
        "role": "SUPPORT_PERSON",
        "claim_status": "REPORTED",
    }
    ent_resp = client.post(f"/v1/cases/{case_id}/entities", json=ent_payload)
    assert ent_resp.status_code == 201
    ent_data = ent_resp.json()
    ent_id = ent_data["entity_id"]
    assert ent_data["label"] == "Deepa"

    # Add relationship from Priya to Deepa
    rel_payload = {
        "source_entity": "ent-1001",
        "relationship_type": "CONNECTED_TO",
        "target_entity": ent_id,
        "claim_status": "REPORTED",
    }
    rel_resp = client.post(f"/v1/cases/{case_id}/relationships", json=rel_payload)
    assert rel_resp.status_code == 201
    rel_data = rel_resp.json()
    assert rel_data["target_entity"] == ent_id

    # Query graph
    graph_resp = client.get(f"/v1/cases/{case_id}/graph?depth=2")
    assert graph_resp.status_code == 200
    graph_data = graph_resp.json()
    assert graph_data["total_nodes"] >= 4


def test_api_candidate_confirmation_and_rejection():
    case_id = "case-1001"

    # Confirm existing candidate cand-1001
    confirm_resp = client.post(
        f"/v1/cases/{case_id}/candidates/cand-1001/confirm",
        json={"operator_id": "operator_verified"},
    )
    assert confirm_resp.status_code == 200
    edge = confirm_resp.json()
    assert edge["edge_id"].startswith("edge-")

    # Re-confirming should fail since it's already CONFIRMED
    re_confirm = client.post(
        f"/v1/cases/{case_id}/candidates/cand-1001/confirm",
        json={"operator_id": "operator_verified"},
    )
    assert re_confirm.status_code == 404


def test_api_case_integrity_and_audit():
    case_id = "case-1001"
    int_resp = client.get(f"/v1/cases/{case_id}/integrity")
    assert int_resp.status_code == 200
    assert "valid" in int_resp.json()

    audit_resp = client.get(f"/v1/cases/{case_id}/audit")
    assert audit_resp.status_code == 200
    logs = audit_resp.json()
    assert isinstance(logs, list)
