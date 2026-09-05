"""SAMVED Phase 15: Data Retention & Privacy Lifecycle Tests.

Tests policy retrieval, policy updates, supervisor-approval guards for destructive purges, and execution auditing.
"""

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.schemas.events import DataRetentionPurgeStrategy, UserIdentity, UserRole
from app.security.retention import RetentionService


@pytest.fixture
def client():
    return TestClient(app)


def test_default_retention_policies():
    """Verifies that default policies cover RAW_AUDIO, TRANSCRIPTS, ANALYTICS, AUDIT_LOGS, TRAINING_RUNS."""
    svc = RetentionService()
    policies = svc.list_policies()
    categories = {p.data_category for p in policies}

    assert "RAW_AUDIO" in categories
    assert "TRANSCRIPTS" in categories
    assert "ANALYTICS_AGGREGATES" in categories
    assert "AUDIT_LOGS" in categories
    assert "TRAINING_RUNS" in categories


def test_purge_requires_supervisor_approval():
    """Verifies that attempting destructive purge without supervisor role/approval is rejected."""
    svc = RetentionService()
    op_identity = UserIdentity(
        user_id="op-1",
        username="op_1",
        role=UserRole.OPERATOR,
        permissions=["cases:read"],
    )

    with pytest.raises(Exception) as exc_info:
        svc.execute_purge("RAW_AUDIO", identity=op_identity, supervisor_approved=False)
    assert "supervisor" in str(exc_info.value).lower()


def test_purge_succeeds_with_supervisor_authority():
    """Verifies that a supervisor can trigger data lifecycle purge."""
    svc = RetentionService()
    sup_identity = UserIdentity(
        user_id="sup-1",
        username="sup_1",
        role=UserRole.SUPERVISOR,
        permissions=["retention:manage"],
    )

    res = svc.execute_purge("RAW_AUDIO", identity=sup_identity, supervisor_approved=True)
    assert res["status"] == "COMPLETED"
    assert res["records_purged"] > 0
    assert res["initiated_by"] == "sup-1"


def test_retention_api_endpoints(client):
    """Verifies GET /v1/security/retention/policies and POST purge endpoints."""
    # 1. List policies
    res = client.get("/v1/security/retention/policies")
    assert res.status_code == 200
    policies = res.json()
    assert len(policies) >= 5

    # 2. Operator purge attempt denied
    headers_op = {"X-User-Role": "OPERATOR", "X-User-Id": "op-42"}
    res_deny = client.post(
        "/v1/security/retention/purge/TRANSCRIPTS",
        json={"supervisor_approved": False},
        headers=headers_op,
    )
    assert res_deny.status_code == 403

    # 3. Supervisor purge allowed
    headers_sup = {"X-User-Role": "SUPERVISOR", "X-User-Id": "sup-42"}
    res_allow = client.post(
        "/v1/security/retention/purge/TRANSCRIPTS",
        json={"supervisor_approved": True, "confirmation_reason": "Scheduled quarterly cleanup"},
        headers=headers_sup,
    )
    assert res_allow.status_code == 200
    assert res_allow.json()["status"] == "COMPLETED"
