"""Integration tests for SAMVED Phase 12 Follow-up REST API."""

import pytest
from starlette.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_followup_status_endpoint():
    resp = client.get("/v1/followups/status")
    assert resp.status_code == 200
    data = resp.json()
    assert data["subsystem"] == "followup_workflow"
    assert data["status"] == "ready"
    assert "safety_disclaimer" in data
    assert "workqueue_summary" in data


def test_list_followups_and_summary():
    resp = client.get("/v1/followups")
    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data
    assert "summary" in data
    assert data["total"] >= 1
    # Check default fixture exists
    fixture = next((f for f in data["items"] if f["followup_id"] == "fol-1001"), None)
    assert fixture is not None
    assert fixture["case_id"] == "case-1001"


def test_create_followup_success_and_validation():
    # Valid creation
    payload = {
        "call_id": "call-fixture-01",
        "type": "HUMAN_CALLBACK",
        "priority": "HIGH",
        "channel": "OPERATOR_CALLBACK",
        "purpose": "Verify safe shelter accommodation",
        "scheduled_for": "2026-09-05T18:30:00Z",
        "safe_contact_window": "18:00-20:00",
        "consent_state": "GRANTED",
        "operator_id": "operator-test",
    }
    resp = client.post("/v1/cases/case-1001/followups", json=payload)
    assert resp.status_code == 201
    data = resp.json()
    assert data["case_id"] == "case-1001"
    assert data["purpose"] == "Verify safe shelter accommodation"
    fol_id = data["followup_id"]

    # Reject invalid purpose (too short/vague)
    bad_payload = payload.copy()
    bad_payload["purpose"] = "call"
    resp_bad = client.post("/v1/cases/case-1001/followups", json=bad_payload)
    assert resp_bad.status_code == 400


def test_followup_lifecycle_actions():
    # 1. Create a follow-up
    create_payload = {
        "call_id": "call-fixture-01",
        "type": "HUMAN_CALLBACK",
        "priority": "NORMAL",
        "channel": "OPERATOR_CALLBACK",
        "purpose": "Check on caller referral status",
        "scheduled_for": "2026-09-05T18:45:00Z",
        "safe_contact_window": "18:00-20:00",
        "consent_state": "GRANTED",
        "operator_id": "op-lifecycle",
    }
    create_resp = client.post("/v1/cases/case-1001/followups", json=create_payload)
    assert create_resp.status_code == 201
    fol_id = create_resp.json()["followup_id"]

    # 2. Start follow-up
    start_resp = client.post(f"/v1/followups/{fol_id}/start", json={"operator_id": "op-lifecycle"})
    assert start_resp.status_code == 200
    assert start_resp.json()["followup"]["status"] == "IN_PROGRESS"

    # 3. Record attempt (No Answer)
    att_resp = client.post(
        f"/v1/followups/{fol_id}/attempt",
        json={
            "channel": "OPERATOR_CALLBACK",
            "result": "NO_ANSWER",
            "notes": "Ranged 4 times, no answer",
            "operator_id": "op-lifecycle",
        },
    )
    assert att_resp.status_code == 200
    assert att_resp.json()["followup"]["attempt_count"] == 1

    # 4. Reschedule follow-up
    resched_resp = client.post(
        f"/v1/followups/{fol_id}/reschedule",
        json={
            "scheduled_for": "2026-09-05T19:15:00Z",
            "safe_contact_window": "18:00-20:00",
            "reason": "Caller did not pick up on first try",
            "operator_id": "op-lifecycle",
        },
    )
    assert resched_resp.status_code == 200
    assert resched_resp.json()["followup"]["status"] == "SCHEDULED"

    # 5. Start again and complete
    client.post(f"/v1/followups/{fol_id}/start", json={"operator_id": "op-lifecycle"})
    comp_resp = client.post(
        f"/v1/followups/{fol_id}/complete",
        json={
            "outcome": "CONTACTED_SUCCESSFULLY",
            "notes_ref": "Caller confirmed safe shelter arrival",
            "operator_id": "op-lifecycle",
        },
    )
    assert comp_resp.status_code == 200
    assert comp_resp.json()["followup"]["status"] == "COMPLETED"

    # 6. Audit trail
    audit_resp = client.get(f"/v1/followups/{fol_id}/audit")
    assert audit_resp.status_code == 200
    audit_data = audit_resp.json()
    assert len(audit_data) >= 4


def test_consent_revocation_endpoint():
    resp = client.post(
        "/v1/cases/case-1001/revoke-consent",
        json={"reason": "Caller requested no further communication", "operator_id": "op-audit"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert "blocked_tasks_count" in data


def test_nonexistent_followup_404():
    resp = client.get("/v1/followups/fol-nonexistent-999")
    assert resp.status_code == 404
