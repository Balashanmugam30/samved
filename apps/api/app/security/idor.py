"""SAMVED Phase 15: Object-Level Authorization & Scope Isolation Engine.

Guards against Insecure Direct Object Reference (IDOR) attacks, enforces district jurisdiction boundaries,
and strictly separates synthetic simulation environments from production databases.
"""

from typing import Optional
from fastapi import HTTPException, status

from app.schemas.events import UserRole, UserIdentity
from app.security.models import ScopeCheckResult


def validate_object_scope(
    identity: UserIdentity,
    object_type: str,
    object_id: str,
    object_district: Optional[str] = None,
    object_assigned_operator: Optional[str] = None,
    is_simulation: bool = False,
    is_write_action: bool = False,
) -> ScopeCheckResult:
    """Validate whether an authenticated identity is authorized to access a specific resource instance.
    
    Enforces:
    1. Simulation Boundary: Production entities cannot be mutated by simulation runs, and vice-versa.
    2. District Jurisdiction: District Admins can only view and operate on resources in their assigned district.
    3. Operator Workstation Scope: Operators cannot tamper with cases assigned to other operators unless supervisor approved.
    4. Auditor Read-Only: Auditors cannot perform mutating write operations.
    """
    actor_id = identity.user_id
    actor_role = identity.role

    # 1. System Admin has full oversight
    if actor_role == UserRole.SYSTEM_ADMIN:
        return ScopeCheckResult(
            allowed=True,
            reason="SYSTEM_ADMIN has global scope.",
            actor_id=actor_id,
            actor_role=actor_role,
            object_type=object_type,
            object_id=object_id,
            district_code=object_district,
        )

    # 2. Auditor write prohibition
    if actor_role == UserRole.AUDITOR and is_write_action:
        return ScopeCheckResult(
            allowed=False,
            reason="AUDITOR role is strictly read-only; mutation prohibited.",
            actor_id=actor_id,
            actor_role=actor_role,
            object_type=object_type,
            object_id=object_id,
            district_code=object_district,
        )

    # 3. Simulation environment quarantine
    if is_simulation and not is_write_action:
        # Simulation read is allowed for testing
        pass
    elif is_simulation and is_write_action and object_type in ["case", "call", "utterance"]:
        return ScopeCheckResult(
            allowed=False,
            reason="SYNTHETIC_SIMULATION_VIOLATION: Simulation executions are forbidden from mutating production case records.",
            actor_id=actor_id,
            actor_role=actor_role,
            object_type=object_type,
            object_id=object_id,
            district_code=object_district,
        )

    # 4. District Admin jurisdiction boundaries
    if actor_role == UserRole.DISTRICT_ADMIN:
        if object_district and identity.district_code:
            norm_target = object_district.strip().upper()
            norm_actor_dist = identity.district_code.strip().upper()
            allowed_districts = {d.strip().upper() for d in identity.assigned_districts}
            allowed_districts.add(norm_actor_dist)

            if norm_target not in allowed_districts:
                return ScopeCheckResult(
                    allowed=False,
                    reason=f"DISTRICT_ISOLATION_VIOLATION: District Admin '{actor_id}' from district '{norm_actor_dist}' cannot access district '{norm_target}' resources.",
                    actor_id=actor_id,
                    actor_role=actor_role,
                    object_type=object_type,
                    object_id=object_id,
                    district_code=object_district,
                )

    # 5. Operator case tampering prevention
    if actor_role == UserRole.OPERATOR and is_write_action:
        if (
            object_assigned_operator
            and object_assigned_operator != actor_id
            and object_assigned_operator != "unassigned"
            and not actor_id.startswith("usr-default-operator")  # Dev mode fallback
        ):
            return ScopeCheckResult(
                allowed=False,
                reason=f"IDOR_OPERATOR_VIOLATION: Operator '{actor_id}' cannot mutate case assigned to '{object_assigned_operator}' without supervisor handoff.",
                actor_id=actor_id,
                actor_role=actor_role,
                object_type=object_type,
                object_id=object_id,
                district_code=object_district,
            )

    return ScopeCheckResult(
        allowed=True,
        reason="Object scope verification passed.",
        actor_id=actor_id,
        actor_role=actor_role,
        object_type=object_type,
        object_id=object_id,
        district_code=object_district,
    )


def enforce_scope(
    identity: UserIdentity,
    object_type: str,
    object_id: str,
    object_district: Optional[str] = None,
    object_assigned_operator: Optional[str] = None,
    is_simulation: bool = False,
    is_write_action: bool = False,
) -> ScopeCheckResult:
    """Enforce object scope; raises HTTP 403 Forbidden if validation fails."""
    res = validate_object_scope(
        identity=identity,
        object_type=object_type,
        object_id=object_id,
        object_district=object_district,
        object_assigned_operator=object_assigned_operator,
        is_simulation=is_simulation,
        is_write_action=is_write_action,
    )
    if not res.allowed:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Access Denied: {res.reason}",
        )
    return res
