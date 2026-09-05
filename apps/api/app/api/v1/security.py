"""SAMVED Phase 15: Security, Privacy & Governance REST API.

Provides endpoints for security posture inspection, living controls inventory,
cryptographic audit log verification, PII redaction sandbox, data retention management,
and caller identity context.
"""

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel, Field

from app.schemas.events import (
    UserRole,
    UserIdentity,
    AuditStatusResult,
    SecurityAuditEntry,
    PIIRedactionResult,
    SecurityControlStatus,
    DataRetentionPurgeStrategy,
    DataRetentionPolicy,
)
from app.security.audit import get_audit_service
from app.security.models import Permission
from app.security.pii import redact_pii
from app.security.rate_limit import enforce_rate_limit
from app.security.rbac import (
    get_current_identity,
    require_permission,
    require_role,
    normalize_role,
)
from app.security.retention import get_retention_service
from app.security.service import get_security_service


security_router = APIRouter(tags=["security"])


class PIIRedactRequest(BaseModel):
    text: str = Field(..., min_length=1, description="Raw input text to scrub")


class UpdateRetentionPolicyRequest(BaseModel):
    retention_days: int = Field(..., ge=1, le=3650)
    purge_strategy: DataRetentionPurgeStrategy
    requires_supervisor_approval: bool = True
    is_active: bool = True


class ExecutePurgeRequest(BaseModel):
    supervisor_approved: bool = False
    confirmation_reason: Optional[str] = None


@security_router.get("/status")
async def get_security_status(
    request: Request,
    identity: UserIdentity = Depends(get_current_identity),
) -> Dict[str, Any]:
    """Retrieve top-level platform security posture, compliance flags, and subsystem health."""
    enforce_rate_limit(f"sec_status:{identity.user_id}", limit=120, window_seconds=60)
    svc = get_security_service()
    summary = svc.get_security_summary()
    summary["caller_context"] = {
        "user_id": identity.user_id,
        "role": identity.role.value,
        "district": identity.district_code,
    }
    return summary


@security_router.get("/controls", response_model=List[SecurityControlStatus])
async def list_security_controls(
    identity: UserIdentity = Depends(get_current_identity),
) -> List[SecurityControlStatus]:
    """List living inventory of all Phase 15 security, privacy, and governance controls."""
    svc = get_security_service()
    return svc.get_controls_inventory()


@security_router.get("/audit", response_model=List[SecurityAuditEntry])
async def get_audit_trail(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    actor_id: Optional[str] = Query(None),
    action: Optional[str] = Query(None),
    resource_type: Optional[str] = Query(None),
    district_code: Optional[str] = Query(None),
    status_result: Optional[AuditStatusResult] = Query(None),
    identity: UserIdentity = Depends(require_permission(Permission.AUDIT_READ)),
) -> List[SecurityAuditEntry]:
    """Query append-only audit trail entries with role-scoped filtering."""
    audit_svc = get_audit_service()

    # Scope isolation: District Admin can only query audit logs within their jurisdiction
    query_district = district_code
    if identity.role == UserRole.DISTRICT_ADMIN and identity.district_code:
        query_district = identity.district_code

    entries = audit_svc.get_entries(
        limit=limit,
        offset=offset,
        actor_id=actor_id,
        action=action,
        resource_type=resource_type,
        district_code=query_district,
        status_result=status_result,
    )
    return entries


@security_router.get("/audit/verify")
async def verify_audit_chain_integrity(
    identity: UserIdentity = Depends(require_permission(Permission.AUDIT_READ)),
) -> Dict[str, Any]:
    """Verify cryptographic SHA-256 hash chaining across all stored audit entries."""
    audit_svc = get_audit_service()
    is_valid, message, total_verified = audit_svc.verify_integrity()
    return {
        "chain_valid": is_valid,
        "verification_message": message,
        "entries_verified": total_verified,
        "hash_algorithm": "SHA-256",
        "verified_by": identity.user_id,
    }


@security_router.post("/pii/redact", response_model=PIIRedactionResult)
async def scrub_pii_content(
    payload: PIIRedactRequest,
    identity: UserIdentity = Depends(get_current_identity),
) -> PIIRedactionResult:
    """Execute Indian PII redaction pipeline against submitted text."""
    enforce_rate_limit(f"pii_redact:{identity.user_id}", limit=60, window_seconds=60)
    result = redact_pii(payload.text)

    # Record event in security audit trail if PII was detected
    if result.has_pii:
        audit_svc = get_audit_service()
        audit_svc.record_event(
            actor_id=identity.user_id,
            actor_role=identity.role,
            action="PII_REDACTION_EXECUTED",
            resource_type="text_payload",
            resource_id="adhoc_redaction",
            status_result=AuditStatusResult.MUTATED,
            district_code=identity.district_code,
            details={
                "redactions_count": result.redactions_count,
                "types_redacted": result.redaction_types,
            },
        )

    return result


@security_router.get("/retention/policies", response_model=List[DataRetentionPolicy])
async def get_retention_policies(
    identity: UserIdentity = Depends(get_current_identity),
) -> List[DataRetentionPolicy]:
    """List data retention and privacy lifecycle policies."""
    ret_svc = get_retention_service()
    return ret_svc.list_policies()


@security_router.put("/retention/policies/{data_category}", response_model=DataRetentionPolicy)
async def update_retention_policy(
    data_category: str,
    payload: UpdateRetentionPolicyRequest,
    identity: UserIdentity = Depends(require_permission(Permission.RETENTION_MANAGE)),
) -> DataRetentionPolicy:
    """Update retention rule parameters (requires supervisor or system admin authority)."""
    ret_svc = get_retention_service()
    updated = ret_svc.update_policy(
        data_category=data_category,
        retention_days=payload.retention_days,
        purge_strategy=payload.purge_strategy,
        requires_supervisor_approval=payload.requires_supervisor_approval,
        is_active=payload.is_active,
    )

    audit_svc = get_audit_service()
    audit_svc.record_event(
        actor_id=identity.user_id,
        actor_role=identity.role,
        action="RETENTION_POLICY_UPDATED",
        resource_type="retention_policy",
        resource_id=data_category.upper(),
        status_result=AuditStatusResult.MUTATED,
        details={
            "retention_days": payload.retention_days,
            "purge_strategy": payload.purge_strategy.value,
        },
    )

    return updated


@security_router.post("/retention/purge/{data_category}")
async def execute_retention_purge(
    data_category: str,
    payload: ExecutePurgeRequest,
    identity: UserIdentity = Depends(require_permission(Permission.RETENTION_MANAGE)),
) -> Dict[str, Any]:
    """Trigger lifecycle purge execution according to configured category policy."""
    ret_svc = get_retention_service()
    res = ret_svc.execute_purge(
        data_category=data_category,
        identity=identity,
        supervisor_approved=payload.supervisor_approved,
    )

    audit_svc = get_audit_service()
    audit_svc.record_event(
        actor_id=identity.user_id,
        actor_role=identity.role,
        action="RETENTION_PURGE_EXECUTED",
        resource_type="data_category",
        resource_id=data_category.upper(),
        status_result=AuditStatusResult.MUTATED,
        details=res,
    )

    return res


@security_router.get("/identity/me", response_model=UserIdentity)
async def get_my_identity(
    identity: UserIdentity = Depends(get_current_identity),
) -> UserIdentity:
    """Return currently authenticated identity, active role, district scope, and permissions."""
    return identity
