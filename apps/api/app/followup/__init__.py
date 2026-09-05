"""SAMVED Phase 12 Follow-up Workflow & Continuity Engine."""

from app.followup.audit import FollowupAuditLogger, FollowupAuditRecord, get_audit_logger
from app.followup.consent import apply_consent_revocation, validate_consent_transition
from app.followup.models import (
    ContactPreferences,
    FollowupAttempt,
    FollowupConsent,
    FollowupEvent,
    FollowupRecord,
    FollowupWorkqueueSummary,
)
from app.followup.policy import (
    check_duplicate_followup,
    check_max_attempts,
    check_safety_precedence,
    validate_consent_for_channel,
    validate_purpose,
    validate_safe_contact_window,
)
from app.followup.scheduler import (
    FollowupScheduler,
    FrozenTimeProvider,
    SystemTimeProvider,
    TimeProvider,
)
from app.followup.service import FollowupService, get_followup_service

__all__ = [
    "FollowupService",
    "get_followup_service",
    "FollowupRecord",
    "FollowupAttempt",
    "FollowupConsent",
    "FollowupEvent",
    "FollowupWorkqueueSummary",
    "ContactPreferences",
    "FollowupScheduler",
    "TimeProvider",
    "SystemTimeProvider",
    "FrozenTimeProvider",
    "FollowupAuditLogger",
    "FollowupAuditRecord",
    "get_audit_logger",
    "validate_purpose",
    "validate_consent_for_channel",
    "validate_safe_contact_window",
    "check_duplicate_followup",
    "check_max_attempts",
    "check_safety_precedence",
    "validate_consent_transition",
    "apply_consent_revocation",
]
