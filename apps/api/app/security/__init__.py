"""SAMVED Phase 15: Security, Privacy & Governance Package.

Exports core security components for authorization, rate limiting, PII redaction,
cryptographic audit logging, data retention, and living control inventory.
"""

from app.security.models import (
    Permission,
    RateLimitConfig,
    RateLimitResult,
    RedactionEntity,
    ScopeCheckResult,
)
from app.security.rbac import (
    ROLE_PERMISSIONS,
    ROLE_HIERARCHY,
    normalize_role,
    get_role_permissions,
    has_permission,
    check_role_hierarchy,
    get_current_identity,
    require_permission,
    require_role,
)
from app.security.idor import validate_object_scope, enforce_scope
from app.security.pii import PIIScrubber, redact_pii, scrub_dict_pii
from app.security.rate_limit import RateLimiter, get_rate_limiter, enforce_rate_limit
from app.security.audit import SecurityAuditService, get_audit_service
from app.security.retention import RetentionService, get_retention_service
from app.security.service import SecurityService, get_security_service

__all__ = [
    "Permission",
    "RateLimitConfig",
    "RateLimitResult",
    "RedactionEntity",
    "ScopeCheckResult",
    "ROLE_PERMISSIONS",
    "ROLE_HIERARCHY",
    "normalize_role",
    "get_role_permissions",
    "has_permission",
    "check_role_hierarchy",
    "get_current_identity",
    "require_permission",
    "require_role",
    "validate_object_scope",
    "enforce_scope",
    "PIIScrubber",
    "redact_pii",
    "scrub_dict_pii",
    "RateLimiter",
    "get_rate_limiter",
    "enforce_rate_limit",
    "SecurityAuditService",
    "get_audit_service",
    "RetentionService",
    "get_retention_service",
    "SecurityService",
    "get_security_service",
]
