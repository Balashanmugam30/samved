"""SAMVED Phase 15: Cryptographically Chained Security Audit Trail Tests.

Tests append-only logging, SHA-256 hash chaining, tamper detection, and verification API.
"""

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.schemas.events import AuditStatusResult, UserRole
from app.security.audit import GENESIS_HASH, SecurityAuditService, get_audit_service


@pytest.fixture
def client():
    return TestClient(app)


def test_audit_hash_chain_creation_and_integrity():
    """Verifies that events are appended with correct SHA-256 chaining and pass integrity checks."""
    svc = SecurityAuditService()
    svc.clear()

    # Initial state
    valid, msg, count = svc.verify_integrity()
    assert valid is True
    assert count == 0

    # Append Event 1
    e1 = svc.record_event(
        actor_id="op-1",
        actor_role=UserRole.OPERATOR,
        action="CALL_INTAKE_STARTED",
        resource_type="call",
        resource_id="call-101",
        status_result=AuditStatusResult.ALLOWED,
        details={"channel": "PSTN"},
    )
    assert e1.prev_hash == GENESIS_HASH
    assert len(e1.entry_hash) == 64

    # Append Event 2
    e2 = svc.record_event(
        actor_id="sup-1",
        actor_role=UserRole.SUPERVISOR,
        action="ESCALATION_OVERRIDE",
        resource_type="alert",
        resource_id="alert-202",
        status_result=AuditStatusResult.ALLOWED,
        details={"risk_level": "CRITICAL"},
    )
    assert e2.prev_hash == e1.entry_hash

    # Append Event 3
    e3 = svc.record_event(
        actor_id="da-1",
        actor_role=UserRole.DISTRICT_ADMIN,
        action="DISTRICT_REPORT_ACCESSED",
        resource_type="district",
        resource_id="dist-303",
        status_result=AuditStatusResult.ALLOWED,
    )
    assert e3.prev_hash == e2.entry_hash

    # Verify integrity across chain
    valid, msg, count = svc.verify_integrity()
    assert valid is True
    assert count == 3


def test_audit_tamper_detection():
    """Verifies that mutating any field in a past entry breaks chain verification."""
    svc = SecurityAuditService()
    svc.clear()

    svc.record_event(
        actor_id="op-1",
        actor_role=UserRole.OPERATOR,
        action="ACTION_A",
        resource_type="res",
        resource_id="1",
    )
    svc.record_event(
        actor_id="op-2",
        actor_role=UserRole.OPERATOR,
        action="ACTION_B",
        resource_type="res",
        resource_id="2",
    )

    # Chain is initially valid
    assert svc.verify_integrity()[0] is True

    # Tamper with entry 0 details
    with svc._lock:
        svc._entries[0].details = {"tampered": "illegal_modification"}

    # Verification must fail and report tamper
    valid, msg, count = svc.verify_integrity()
    assert valid is False
    assert "Tampered entry hash at index 0" in msg


def test_audit_query_and_verification_endpoints(client):
    """Verifies GET /v1/security/audit and /v1/security/audit/verify endpoints."""
    # Add an event via global service
    global_svc = get_audit_service()
    global_svc.record_event(
        actor_id="auditor-99",
        actor_role=UserRole.AUDITOR,
        action="COMPLIANCE_REVIEW",
        resource_type="case",
        resource_id="case-777",
        status_result=AuditStatusResult.ALLOWED,
    )

    # 1. Query audit trail (with supervisor permissions)
    headers = {"X-User-Role": "SUPERVISOR", "X-User-Id": "sup-lead"}
    res = client.get("/v1/security/audit?limit=10", headers=headers)
    assert res.status_code == 200
    entries = res.json()
    assert len(entries) >= 1
    assert any(e["action"] == "COMPLIANCE_REVIEW" for e in entries)

    # 2. Verify audit chain
    verify_res = client.get("/v1/security/audit/verify", headers=headers)
    assert verify_res.status_code == 200
    v_data = verify_res.json()
    assert v_data["chain_valid"] is True
    assert v_data["hash_algorithm"] == "SHA-256"
