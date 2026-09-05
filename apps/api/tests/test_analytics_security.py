"""
Security & Role Authorization tests for Analytics Subsystem.
Validates denial of unauthorized roles, IDOR protections, and injection defenses.
"""

import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_operator_role_denied_district_analytics():
    # OPERATOR role must NOT have access to macro district intelligence
    res = client.get("/v1/analytics/districts/TN-CHE/summary", headers={"X-User-Role": "OPERATOR"})
    assert res.status_code == 403
    data = res.json()
    err_msg = data.get("detail") or data.get("error", {}).get("message", "")
    assert "Access denied" in err_msg


def test_operator_role_denied_trends():
    res = client.get("/v1/analytics/districts/TN-CHE/trends", headers={"X-User-Role": "OPERATOR"})
    assert res.status_code == 403


def test_operator_role_denied_query():
    body = {
        "district_code": "TN-CHE",
        "period": "DAY",
        "start_date": "2026-09-01T00:00:00Z",
        "end_date": "2026-09-02T00:00:00Z",
        "role": "OPERATOR",
    }
    res = client.post("/v1/analytics/query", json=body, headers={"X-User-Role": "OPERATOR"})
    assert res.status_code == 403


def test_recompute_restricted_to_admin_and_supervisor():
    # Operator cannot recompute
    res = client.post(
        "/v1/analytics/recompute",
        json={"district_code": "TN-CHE", "period": "DAY", "start_date": "2026-09-01", "end_date": "2026-09-02"},
        headers={"X-User-Role": "OPERATOR"},
    )
    assert res.status_code == 403


def test_audit_logs_restricted_to_admin_and_supervisor():
    # District admin or operator cannot read cross-system access audit
    res = client.get("/v1/analytics/audit", headers={"X-User-Role": "OPERATOR"})
    assert res.status_code == 403

    res_dist = client.get("/v1/analytics/audit", headers={"X-User-Role": "DISTRICT_ADMIN"})
    assert res_dist.status_code == 403

    # Supervisor is allowed
    res_sup = client.get("/v1/analytics/audit", headers={"X-User-Role": "SUPERVISOR"})
    assert res_sup.status_code == 200


def test_injection_defense_in_district_code():
    # SQL injection attempt
    res = client.get(
        "/v1/analytics/districts/TN-CHE' OR 1=1;--/summary",
        headers={"X-User-Role": "DISTRICT_ADMIN"},
    )
    assert res.status_code == 200
    # Safely normalized to UNKNOWN
    assert res.json()["district_code"] == "UNKNOWN"


def test_path_traversal_defense_in_district_code():
    res = client.get(
        "/v1/analytics/districts/..-etc-passwd/summary",
        headers={"X-User-Role": "DISTRICT_ADMIN"},
    )
    assert res.status_code == 200
    assert res.json()["district_code"] == "UNKNOWN"
