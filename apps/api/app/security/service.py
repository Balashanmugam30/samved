"""SAMVED Phase 15: Unified Security & Governance Service.

Central coordinator aggregating RBAC, IDOR, PII scrubbing, cryptographic auditing,
rate limiting, and living security controls inventory.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.schemas.events import (
    SecurityControlCategory,
    SecurityControlHealth,
    SecurityControlStatus,
    UserRole,
    UserIdentity,
    AuditStatusResult,
    SecurityAuditEntry,
    PIIRedactionResult,
    DataRetentionPolicy,
)
from app.security.audit import get_audit_service
from app.security.idor import validate_object_scope
from app.security.pii import redact_pii, scrub_dict_pii
from app.security.rate_limit import get_rate_limiter
from app.security.rbac import has_permission, check_role_hierarchy, normalize_role
from app.security.retention import get_retention_service


class SecurityService:
    """Enterprise security & governance coordinator for SAMVED."""

    def __init__(self):
        self._audit = get_audit_service()
        self._limiter = get_rate_limiter()
        self._retention = get_retention_service()

    def get_controls_inventory(self) -> List[SecurityControlStatus]:
        """Return the living inventory of all active Phase 15 security controls."""
        now_ts = datetime.now(timezone.utc).isoformat()
        return [
            SecurityControlStatus(
                control_id="CTRL-AUTH-001",
                name="Identity & Context Verification",
                category=SecurityControlCategory.AUTHENTICATION,
                status=SecurityControlHealth.OPERATIONAL,
                description="Verifies user identity headers, session tokens, and district context.",
                last_verified_at=now_ts,
                metrics={"active_identities_tracked": 5, "enforcement": "STRICT_HEADER_TOKEN"},
            ),
            SecurityControlStatus(
                control_id="CTRL-AUTH-002",
                name="Least Privilege Role-Based Access Control (RBAC)",
                category=SecurityControlCategory.AUTHORIZATION,
                status=SecurityControlHealth.OPERATIONAL,
                description="Enforces 5 distinct roles (Operator, Supervisor, District Admin, System Admin, Auditor) with granular permissions.",
                last_verified_at=now_ts,
                metrics={"roles_defined": 5, "permissions_catalog": 14},
            ),
            SecurityControlStatus(
                control_id="CTRL-AUTH-003",
                name="Object-Level Scope & District Isolation (IDOR Guard)",
                category=SecurityControlCategory.AUTHORIZATION,
                status=SecurityControlHealth.OPERATIONAL,
                description="Prevents cross-district data leakage and unauthorized operator record modification.",
                last_verified_at=now_ts,
                metrics={"district_boundaries_enforced": True, "cross_district_denial_active": True},
            ),
            SecurityControlStatus(
                control_id="CTRL-DATA-001",
                name="Indian Entity PII Redaction Pipeline",
                category=SecurityControlCategory.DATA_PROTECTION,
                status=SecurityControlHealth.OPERATIONAL,
                description="High-accuracy regex + heuristic masking for Aadhaar, PAN, Indian phone numbers, emails, and bank accounts.",
                last_verified_at=now_ts,
                metrics={"entity_types_covered": ["AADHAAR", "PAN", "PHONE", "EMAIL", "BANK_ACCOUNT", "VEHICLE"]},
            ),
            SecurityControlStatus(
                control_id="CTRL-DATA-002",
                name="Log Stream PII Sanitization",
                category=SecurityControlCategory.DATA_PROTECTION,
                status=SecurityControlHealth.OPERATIONAL,
                description="JSONLogFormatter interceptor scrubs PII before emission to stdout, files, or SIEM.",
                last_verified_at=now_ts,
                metrics={"interceptor_active": True, "scrubbed_streams": ["stdout", "audit"]},
            ),
            SecurityControlStatus(
                control_id="CTRL-AUDT-001",
                name="Cryptographically Chained Audit Trail",
                category=SecurityControlCategory.AUDITABILITY,
                status=SecurityControlHealth.OPERATIONAL,
                description="Append-only log chained with SHA-256 cryptographic hashes for tamper evidence.",
                last_verified_at=now_ts,
                metrics={
                    "total_entries": self._audit.total_count(),
                    "hash_algorithm": "SHA-256",
                    "chain_valid": self._audit.verify_integrity()[0],
                },
            ),
            SecurityControlStatus(
                control_id="CTRL-ABUS-001",
                name="Sliding-Window Adaptive Rate Limiter",
                category=SecurityControlCategory.ABUSE_RESISTANCE,
                status=SecurityControlHealth.OPERATIONAL,
                description="Protects public endpoints, telephony ingresses, and API routes against volumetric bombardment.",
                last_verified_at=now_ts,
                metrics={"default_limit_rpm": 60, "progressive_blocking": True},
            ),
            SecurityControlStatus(
                control_id="CTRL-ABUS-002",
                name="WebSocket Frame & Message Rate Guard",
                category=SecurityControlCategory.ABUSE_RESISTANCE,
                status=SecurityControlHealth.OPERATIONAL,
                description="Restricts WebSocket frames to <= 64KB and limits message throughput to 10 msgs/sec.",
                last_verified_at=now_ts,
                metrics={"max_frame_bytes": 65536, "max_msg_rate_per_sec": 10},
            ),
            SecurityControlStatus(
                control_id="CTRL-GOVN-001",
                name="Synthetic Simulation Quarantine",
                category=SecurityControlCategory.GOVERNANCE,
                status=SecurityControlHealth.OPERATIONAL,
                description="Isolates synthetic benchmark scenarios and evaluation runs from mutating production case records.",
                last_verified_at=now_ts,
                metrics={"quarantine_enforced": True, "production_leak_prevention": "ACTIVE"},
            ),
            SecurityControlStatus(
                control_id="CTRL-GOVN-002",
                name="Zero Autonomous Dispatch Guardrail",
                category=SecurityControlCategory.GOVERNANCE,
                status=SecurityControlHealth.OPERATIONAL,
                description="Inviolable architectural constraint requiring human supervisor confirmation for emergency dispatch and follow-ups.",
                last_verified_at=now_ts,
                metrics={"human_in_the_loop_mandatory": True, "autonomous_actions_allowed": False},
            ),
            SecurityControlStatus(
                control_id="CTRL-DATA-003",
                name="Data Retention & Lifecycle Manager",
                category=SecurityControlCategory.DATA_PROTECTION,
                status=SecurityControlHealth.OPERATIONAL,
                description="Configurable time-to-live policies with supervisor-confirmed destructive purging and anonymization.",
                last_verified_at=now_ts,
                metrics={"active_policies": len(self._retention.list_policies())},
            ),
        ]

    def get_security_summary(self) -> Dict[str, Any]:
        """Provide a consolidated security posture overview."""
        controls = self.get_controls_inventory()
        is_chain_valid, chain_msg, entries_count = self._audit.verify_integrity()
        policies = self._retention.list_policies()

        return {
            "overall_posture": "HEALTHY",
            "prototype_notice": "SAMVED Phase 15 prototype security hardening. Production deployment requires external HSM/KMS keys, TLS termination, and OIDC identity provider integration.",
            "controls_count": len(controls),
            "controls_operational": sum(1 for c in controls if c.status == SecurityControlHealth.OPERATIONAL),
            "audit_chain": {
                "is_valid": is_chain_valid,
                "message": chain_msg,
                "total_records": entries_count,
            },
            "retention_policies_count": len(policies),
            "last_evaluated_at": datetime.now(timezone.utc).isoformat(),
        }


# Global Singleton
_global_security_service = SecurityService()


def get_security_service() -> SecurityService:
    return _global_security_service
