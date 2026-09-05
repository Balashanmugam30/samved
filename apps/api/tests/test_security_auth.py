"""SAMVED Phase 15: Authentication & Security Posture Tests.

Tests identity extraction, context headers, security status, and defense-in-depth response headers.
"""

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.schemas.events import UserRole


@pytest.fixture
def client():
    return TestClient(app)


def test_security_status_endpoint(client):
    """Verifies that /v1/security/status returns healthy posture and active controls."""
    res = client.get("/v1/security/status")
    assert res.status_code == 200
    data = res.json()
    assert data["overall_posture"] == "HEALTHY"
    assert data["controls_count"] >= 10
    assert data["controls_operational"] >= 10
    assert data["audit_chain"]["is_valid"] is True
    assert "caller_context" in data
    assert data["caller_context"]["role"] == "OPERATOR"


def test_security_controls_inventory(client):
    """Verifies that /v1/security/controls returns the living inventory with required metadata."""
    res = client.get("/v1/security/controls")
    assert res.status_code == 200
    controls = res.json()
    assert len(controls) >= 10
    control_ids = [c["control_id"] for c in controls]
    assert "CTRL-AUTH-001" in control_ids
    assert "CTRL-AUTH-002" in control_ids
    assert "CTRL-AUTH-003" in control_ids
    assert "CTRL-DATA-001" in control_ids
    assert "CTRL-AUDT-001" in control_ids
    assert "CTRL-GOVN-002" in control_ids


def test_security_headers_middleware(client):
    """Verifies that defense-in-depth security headers are present on API responses."""
    res = client.get("/v1/health")
    assert res.status_code == 200
    headers = res.headers
    assert headers.get("x-content-type-options") == "nosniff"
    assert headers.get("x-frame-options") == "DENY"
    assert headers.get("x-xss-protection") == "1; mode=block"
    assert headers.get("referrer-policy") == "strict-origin-when-cross-origin"
    assert "default-src 'self'" in headers.get("content-security-policy", "")


def test_identity_me_resolution(client):
    """Verifies that identity is correctly resolved from headers."""
    # 1. Default identity
    res1 = client.get("/v1/security/identity/me")
    assert res1.status_code == 200
    data1 = res1.json()
    assert data1["role"] == "OPERATOR"
    assert data1["user_id"] == "usr-default-operator"

    # 2. Explicit headers identity
    headers = {
        "X-User-Id": "sup-77",
        "X-User-Role": "SUPERVISOR",
        "X-District-Code": "DL-NEW",
    }
    res2 = client.get("/v1/security/identity/me", headers=headers)
    assert res2.status_code == 200
    data2 = res2.json()
    assert data2["role"] == "SUPERVISOR"
    assert data2["user_id"] == "sup-77"
    assert data2["district_code"] == "DL-NEW"
    assert "alerts:override" in data2["permissions"]
