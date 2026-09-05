"""
Integration tests for Analytics REST API endpoints.
Uses TestClient to validate responses, status codes, and schema compliance.
"""

import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_get_analytics_status():
    res = client.get("/v1/analytics/status")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "HEALTHY"
    assert data["phase"] == "PHASE_13"
    assert data["predictive_policing_enabled"] is False
    assert data["surveillance_mode"] is False


def test_get_metrics_catalog():
    res = client.get("/v1/analytics/metrics")
    assert res.status_code == 200
    data = res.json()
    assert data["total_count"] >= 15
    assert data["catalog_version"] == "v1.0.0"


def test_get_districts_list():
    res = client.get("/v1/analytics/districts")
    assert res.status_code == 200
    data = res.json()
    assert data["total_count"] >= 5
    codes = [d["district_code"] for d in data["districts"]]
    assert "TN-CHE" in codes
    assert "DL-CEN" in codes
    assert "PY-KKL" in codes


def test_get_district_summary_healthy():
    res = client.get("/v1/analytics/districts/TN-CHE/summary", headers={"X-User-Role": "DISTRICT_ADMIN"})
    assert res.status_code == 200
    data = res.json()
    assert data["district_code"] == "TN-CHE"
    assert data["privacy_status"] == "PASS"
    assert data["total_calls"]["suppressed"] is False
    assert data["total_calls"]["display_value"] == "142"


def test_get_district_summary_suppressed():
    res = client.get("/v1/analytics/districts/PY-KKL/summary", headers={"X-User-Role": "DISTRICT_ADMIN"})
    assert res.status_code == 200
    data = res.json()
    assert data["district_code"] == "PY-KKL"
    assert data["privacy_status"] == "SUPPRESSED"
    assert data["total_calls"]["suppressed"] is True
    assert data["total_calls"]["display_value"] == "SUPPRESSED"
    assert data["total_calls"]["raw_value"] is None


def test_get_district_trends():
    res = client.get("/v1/analytics/districts/TN-CHE/trends", headers={"X-User-Role": "DISTRICT_ADMIN"})
    assert res.status_code == 200
    data = res.json()
    assert len(data["points"]) == 7
    assert data["overall_trend"] in ["RISING", "FALLING", "STABLE"]


def test_get_district_languages():
    res = client.get("/v1/analytics/districts/TN-CHE/languages", headers={"X-User-Role": "DISTRICT_ADMIN"})
    assert res.status_code == 200
    data = res.json()
    assert len(data["items"]) >= 2


def test_get_district_services():
    res = client.get("/v1/analytics/districts/TN-CHE/services", headers={"X-User-Role": "DISTRICT_ADMIN"})
    assert res.status_code == 200
    data = res.json()
    assert len(data["items"]) >= 3


def test_get_district_safety():
    res = client.get("/v1/analytics/districts/TN-CHE/safety", headers={"X-User-Role": "DISTRICT_ADMIN"})
    assert res.status_code == 200
    data = res.json()
    assert len(data["items"]) == 5


def test_get_district_svi():
    res = client.get("/v1/analytics/districts/TN-CHE/svi", headers={"X-User-Role": "DISTRICT_ADMIN"})
    assert res.status_code == 200
    data = res.json()
    assert len(data["items"]) == 4
    assert data["average_svi"]["raw_value"] == 46.5


def test_get_district_followups():
    res = client.get("/v1/analytics/districts/TN-CHE/followups", headers={"X-User-Role": "DISTRICT_ADMIN"})
    assert res.status_code == 200
    data = res.json()
    assert data["created_count"]["suppressed"] is False
    assert data["completion_rate"]["unit"] == "%"


def test_get_district_operations():
    res = client.get("/v1/analytics/districts/TN-CHE/operations", headers={"X-User-Role": "DISTRICT_ADMIN"})
    assert res.status_code == 200
    data = res.json()
    assert data["active_operators_count"]["suppressed"] is False


def test_post_analytics_query():
    body = {
        "district_code": "DL-CEN",
        "period": "DAY",
        "start_date": "2026-09-01T00:00:00Z",
        "end_date": "2026-09-02T00:00:00Z",
        "role": "DISTRICT_ADMIN",
    }
    res = client.post("/v1/analytics/query", json=body, headers={"X-User-Role": "DISTRICT_ADMIN"})
    assert res.status_code == 200
    data = res.json()
    assert data["summary"]["district_code"] == "DL-CEN"


def test_recompute_and_audit():
    res = client.post(
        "/v1/analytics/recompute",
        json={"district_code": "TN-CHE", "period": "DAY", "start_date": "2026-09-01", "end_date": "2026-09-02"},
        headers={"X-User-Role": "SYSTEM_ADMIN"},
    )
    assert res.status_code == 200
    assert res.json()["status"] == "COMPLETED"

    audit_res = client.get("/v1/analytics/audit", headers={"X-User-Role": "SYSTEM_ADMIN"})
    assert audit_res.status_code == 200
    assert audit_res.json()["total_count"] >= 1
