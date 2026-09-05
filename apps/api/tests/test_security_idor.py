"""SAMVED Phase 15: Insecure Direct Object Reference (IDOR) & Scope Isolation Tests.

Tests district isolation boundaries, cross-operator tampering prevention, and synthetic simulation quarantine.
"""

import pytest
from app.schemas.events import UserIdentity, UserRole
from app.security.idor import enforce_scope, validate_object_scope
from fastapi import HTTPException


def test_district_admin_isolated_to_own_jurisdiction():
    """Verifies that a District Admin cannot access resources outside their designated district."""
    identity = UserIdentity(
        user_id="da-kolkata",
        username="da_kolkata",
        role=UserRole.DISTRICT_ADMIN,
        district_code="KOLKATA",
        assigned_districts=["KOLKATA"],
        permissions=["analytics:read", "cases:read"],
    )

    # 1. Access inside jurisdiction is allowed
    res_in = validate_object_scope(
        identity=identity,
        object_type="district_analytics",
        object_id="analytics-kolkata-01",
        object_district="KOLKATA",
    )
    assert res_in.allowed is True

    # 2. Access outside jurisdiction is denied
    res_out = validate_object_scope(
        identity=identity,
        object_type="district_analytics",
        object_id="analytics-nadia-01",
        object_district="NADIA",
    )
    assert res_out.allowed is False
    assert "DISTRICT_ISOLATION_VIOLATION" in res_out.reason

    # enforce_scope raises HTTPException
    with pytest.raises(HTTPException) as exc_info:
        enforce_scope(
            identity=identity,
            object_type="district_analytics",
            object_id="analytics-nadia-01",
            object_district="NADIA",
        )
    assert exc_info.value.status_code == 403


def test_cross_operator_tampering_prevention():
    """Verifies that an Operator cannot mutate a case record owned by another operator."""
    identity = UserIdentity(
        user_id="op-alpha",
        username="op_alpha",
        role=UserRole.OPERATOR,
        district_code="DELHI",
        assigned_districts=["DELHI"],
        permissions=["cases:read", "cases:write"],
    )

    # Mutation on case assigned to Operator Beta is denied
    res = validate_object_scope(
        identity=identity,
        object_type="case",
        object_id="case-1002",
        object_assigned_operator="op-beta",
        is_write_action=True,
    )
    assert res.allowed is False
    assert "IDOR_OPERATOR_VIOLATION" in res.reason

    # Mutation on own case is allowed
    res_own = validate_object_scope(
        identity=identity,
        object_type="case",
        object_id="case-1002",
        object_assigned_operator="op-alpha",
        is_write_action=True,
    )
    assert res_own.allowed is True


def test_supervisor_has_cross_district_and_operator_scope():
    """Verifies that Supervisor can oversee cases across operators and districts."""
    sup_identity = UserIdentity(
        user_id="sup-hq",
        username="sup_hq",
        role=UserRole.SUPERVISOR,
        district_code=None,
        assigned_districts=[],
        permissions=["*"],
    )

    res = validate_object_scope(
        identity=sup_identity,
        object_type="case",
        object_id="case-999",
        object_district="MUMBAI",
        object_assigned_operator="op-gamma",
        is_write_action=True,
    )
    assert res.allowed is True


def test_simulation_quarantine_prevents_production_mutation():
    """Verifies that a simulation test execution is strictly blocked from mutating production entities."""
    sim_identity = UserIdentity(
        user_id="sim-runner",
        username="sim_runner",
        role=UserRole.OPERATOR,
        district_code="TEST",
        assigned_districts=["TEST"],
        permissions=["cases:write"],
    )

    res = validate_object_scope(
        identity=sim_identity,
        object_type="case",
        object_id="case-prod-101",
        is_simulation=True,
        is_write_action=True,
    )
    assert res.allowed is False
    assert "SYNTHETIC_SIMULATION_VIOLATION" in res.reason
