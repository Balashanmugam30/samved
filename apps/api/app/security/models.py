"""SAMVED Phase 15: Security, Privacy & Governance Data Models.

Canonical security domain definitions aligned with contracts in packages/schemas.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from app.schemas.events import (
    UserRole,
    UserIdentity,
    AuditStatusResult,
    SecurityAuditEntry,
    PIIRedactionResult,
    SecurityControlCategory,
    SecurityControlHealth,
    SecurityControlStatus,
    DataRetentionPurgeStrategy,
    DataRetentionPolicy,
)


class Permission(str, Enum):
    # Case & Call Management
    CASES_READ = "cases:read"
    CASES_WRITE = "cases:write"
    CALLS_HANDLE = "calls:handle"
    CALLS_DISPATCH_OVERRIDE = "calls:dispatch_override"

    # Alerts & Safety
    ALERTS_OVERRIDE = "alerts:override"
    ALERTS_ACKNOWLEDGE = "alerts:acknowledge"

    # Audit Trail
    AUDIT_READ = "audit:read"
    AUDIT_EXPORT = "audit:export"

    # Operational Analytics
    ANALYTICS_READ = "analytics:read"
    DISTRICTS_READ = "districts:read"
    DISTRICTS_WRITE = "districts:write"

    # Simulation & Sandbox
    SIMULATION_READ = "simulation:read"
    SIMULATION_WRITE = "simulation:write"
    TRAINING_USE = "training:use"

    # Security & Governance
    SECURITY_ADMIN = "security:admin"
    RETENTION_MANAGE = "retention:manage"
    PII_DEANONYMIZE = "pii:deanonymize"  # Strictly restricted


class RateLimitConfig(BaseModel):
    key: str
    limit: int
    window_seconds: int
    burst_allowance: int = 0


class RateLimitResult(BaseModel):
    allowed: bool
    current_count: int
    limit: int
    window_seconds: int
    retry_after_seconds: float = 0.0
    client_ip: Optional[str] = None


class RedactionEntity(BaseModel):
    entity_type: str
    start: int
    end: int
    original: str
    redacted: str


class ScopeCheckResult(BaseModel):
    allowed: bool
    reason: str
    actor_id: str
    actor_role: UserRole
    object_type: str
    object_id: str
    district_code: Optional[str] = None
