"""SAMVED Phase 15: Role-Based Access Control (RBAC) Tests.

Tests permission matrices, role hierarchy, least privilege enforcement, and endpoint guards.
"""

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.schemas.events import UserRole
from app.security.models import Permission
from app.security.rbac import (
    check_role_hierarchy,
    get_role_permissions,
    has_permission,
    normalize_role,
)


@pytest.fixture
def client():
    return TestClient(app)


def test_role_permissions_matrix():
    """Verifies that all 5 roles have expected baseline permissions."""
    # 1. System Admin has wildcard
    assert has_permission(UserRole.SYSTEM_ADMIN, Permission.CASES_WRITE)
    assert has_permission(UserRole.SYSTEM_ADMIN, "any:custom:permission")

    # 2. Supervisor has cases, audit, alerts override, simulation
    assert has_permission(UserRole.SUPERVISOR, Permission.CASES_WRITE)
    assert has_permission(UserRole.SUPERVISOR, Permission.ALERTS_OVERRIDE)
    assert has_permission(UserRole.SUPERVISOR, Permission.RETENTION_MANAGE)

    # 3. District Admin has analytics and district scope
    assert has_permission(UserRole.DISTRICT_ADMIN, Permission.ANALYTICS_READ)
    assert has_permission(UserRole.DISTRICT_ADMIN, Permission.DISTRICTS_READ)
    assert not has_permission(UserRole.DISTRICT_ADMIN, Permission.ALERTS_OVERRIDE)

    # 4. Operator has case and call handling, but not supervisor override
    assert has_permission(UserRole.OPERATOR, Permission.CALLS_HANDLE)
    assert not has_permission(UserRole.OPERATOR, Permission.ALERTS_OVERRIDE)
    assert not has_permission(UserRole.OPERATOR, Permission.RETENTION_MANAGE)

    # 5. Auditor has read-only access
    assert has_permission(UserRole.AUDITOR, Permission.AUDIT_READ)
    assert has_permission(UserRole.AUDITOR, Permission.ANALYTICS_READ)
    assert not has_permission(UserRole.AUDITOR, Permission.CASES_WRITE)


def test_role_hierarchy():
    """Verifies hierarchy comparisons for administrative delegation."""
    assert check_role_hierarchy(UserRole.SYSTEM_ADMIN, UserRole.SUPERVISOR)
    assert check_role_hierarchy(UserRole.SUPERVISOR, UserRole.OPERATOR)
    assert not check_role_hierarchy(UserRole.OPERATOR, UserRole.SUPERVISOR)


def test_rbac_endpoint_forbidden_for_insufficient_role(client):
    """Verifies that endpoints protected by require_permission return 403 when caller lacks authority."""
    # Operator attempting retention policy update (requires RETENTION_MANAGE)
    headers = {
        "X-User-Id": "op-101",
        "X-User-Role": "OPERATOR",
    }
    payload = {
        "retention_days": 15,
        "purge_strategy": "HARD_DELETE",
        "requires_supervisor_approval": True,
        "is_active": True,
    }
    res = client.put("/v1/security/retention/policies/RAW_AUDIO", json=payload, headers=headers)
    assert res.status_code == 403
    err_body = res.json()
    msg = err_body.get("error", {}).get("message", "") or err_body.get("detail", "")
    assert "lacks required permission" in msg


def test_rbac_endpoint_allowed_for_authorized_role(client):
    """Verifies that supervisor can update retention policies."""
    headers = {
        "X-User-Id": "sup-202",
        "X-User-Role": "SUPERVISOR",
    }
    payload = {
        "retention_days": 45,
        "purge_strategy": "HARD_DELETE",
        "requires_supervisor_approval": True,
        "is_active": True,
    }
    res = client.put("/v1/security/retention/policies/RAW_AUDIO", json=payload, headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["retention_days"] == 45
    assert data["data_category"] == "RAW_AUDIO"
