"""Deterministic Policy Engine for SAMVED Follow-up Workflow."""

from datetime import datetime, timezone
import logging
import re
from typing import List, Optional, Tuple

from app.followup.models import ContactPreferences, FollowupRecord
from app.schemas.events import ConsentState, ContactChannel, FollowupPriority, FollowupStatus

logger = logging.getLogger("samved.followup.policy")

SAFE_WINDOW_REGEX = re.compile(r"^([01]\d|2[0-3]):[0-5]\d-([01]\d|2[0-3]):[0-5]\d$")
VAGUE_PURPOSES = {"check caller", "follow up", "call", "test", "check", "callback", "asap"}


class PolicyDecision:
    def __init__(self, allowed: bool, reason_code: Optional[str] = None, message: Optional[str] = None):
        self.allowed = allowed
        self.reason_code = reason_code
        self.message = message

    @classmethod
    def allow(cls) -> "PolicyDecision":
        return cls(allowed=True)

    @classmethod
    def deny(cls, reason_code: str, message: str) -> "PolicyDecision":
        return cls(allowed=False, reason_code=reason_code, message=message)


def validate_purpose(purpose: str) -> PolicyDecision:
    """Validates that a follow-up purpose is explicit and non-vague."""
    if not purpose or not purpose.strip():
        return PolicyDecision.deny("PURPOSE_EMPTY", "Purpose must not be empty.")
    
    cleaned = purpose.strip().lower()
    if len(cleaned) < 5:
        return PolicyDecision.deny("PURPOSE_TOO_SHORT", "Purpose must be at least 5 characters.")
    
    if cleaned in VAGUE_PURPOSES:
        return PolicyDecision.deny(
            "PURPOSE_TOO_VAGUE",
            f"Purpose '{purpose}' is too vague. Please provide a specific operational reason."
        )
    
    return PolicyDecision.allow()


def validate_consent_for_channel(
    consent_state: ConsentState,
    channel: ContactChannel,
    contact_prefs: Optional[ContactPreferences] = None
) -> PolicyDecision:
    """Verifies that caller consent is sufficient for the requested contact channel."""
    if consent_state == ConsentState.REVOKED:
        return PolicyDecision.deny("CONSENT_REVOKED", "Caller consent has been explicitly revoked.")
    
    if consent_state == ConsentState.REFUSED:
        return PolicyDecision.deny("CONSENT_REFUSED", "Caller explicitly refused follow-up contact.")
    
    # Internal tasks do not contact the caller externally
    if channel == ContactChannel.INTERNAL_TASK:
        return PolicyDecision.allow()
    
    # For external contact channels, consent must be explicitly granted or limited
    if consent_state not in (ConsentState.GRANTED, ConsentState.LIMITED):
        return PolicyDecision.deny(
            "INSUFFICIENT_CONSENT",
            f"External contact via {channel} requires explicit GRANTED or LIMITED consent. Current: {consent_state}."
        )
    
    # Check preferences
    if contact_prefs:
        if not contact_prefs.safe_to_contact:
            return PolicyDecision.deny("UNSAFE_TO_CONTACT", "Caller contact preferences indicate safe_to_contact is FALSE.")
        if contact_prefs.no_text and channel == ContactChannel.SMS:
            return PolicyDecision.deny("CHANNEL_RESTRICTED", "Caller preferences explicitly forbid SMS contact.")
        if contact_prefs.no_voicemail and channel == ContactChannel.PHONE:
            logger.info("Caller preferences forbid voicemail; tele-counselor must not leave recordings.")
            
    return PolicyDecision.allow()


def validate_safe_contact_window(
    safe_window: Optional[str],
    scheduled_for_iso: str,
    tz_name: Optional[str] = "Asia/Kolkata"
) -> PolicyDecision:
    """Validates that scheduled contact time falls within the caller's safe contact window."""
    if not safe_window:
        # If no window is specified, allowed but flagged
        return PolicyDecision.allow()
    
    if not SAFE_WINDOW_REGEX.match(safe_window.strip()):
        return PolicyDecision.deny(
            "INVALID_WINDOW_FORMAT",
            f"Safe contact window '{safe_window}' must follow HH:MM-HH:MM format (e.g. 18:00-20:00)."
        )
    
    start_str, end_str = safe_window.strip().split("-")
    try:
        dt = datetime.fromisoformat(scheduled_for_iso.replace("Z", "+00:00"))
        # In a real app with zoneinfo, we convert to local tz. Here we extract hour:minute
        scheduled_time_str = dt.strftime("%H:%M")
        if not (start_str <= scheduled_time_str <= end_str):
            return PolicyDecision.deny(
                "OUTSIDE_SAFE_WINDOW",
                f"Scheduled time {scheduled_time_str} falls outside caller safe contact window {safe_window}."
            )
    except Exception as e:
        return PolicyDecision.deny("INVALID_TIMESTAMP", f"Could not parse scheduled_for timestamp: {str(e)}")
    
    return PolicyDecision.allow()


def check_duplicate_followup(
    new_case_id: str,
    new_purpose: str,
    new_channel: ContactChannel,
    existing_followups: List[FollowupRecord]
) -> PolicyDecision:
    """Prevents redundant identical follow-up tasks from being opened simultaneously."""
    cleaned_new = new_purpose.strip().lower()
    active_statuses = {
        FollowupStatus.DRAFT,
        FollowupStatus.PENDING_APPROVAL,
        FollowupStatus.SCHEDULED,
        FollowupStatus.READY,
        FollowupStatus.IN_PROGRESS,
    }
    
    for f in existing_followups:
        if f.case_id == new_case_id and f.status in active_statuses:
            if f.channel == new_channel and f.purpose.strip().lower() == cleaned_new:
                return PolicyDecision.deny(
                    "DUPLICATE_FOLLOW_UP",
                    f"An active follow-up ({f.followup_id}) already exists with identical purpose and channel for this case."
                )
    return PolicyDecision.allow()


def check_max_attempts(followup: FollowupRecord) -> PolicyDecision:
    """Enforces attempt cap to prevent caller harassment."""
    if followup.attempt_count >= followup.max_attempts:
        return PolicyDecision.deny(
            "MAX_ATTEMPTS_EXCEEDED",
            f"Maximum allowed contact attempts ({followup.max_attempts}) reached for follow-up {followup.followup_id}."
        )
    return PolicyDecision.allow()


def check_safety_precedence(safety_state: Optional[str], priority: FollowupPriority) -> PolicyDecision:
    """Enforces that urgent safety crises take precedence over future follow-up scheduling."""
    if safety_state in ("CRITICAL", "EMERGENCY"):
        if priority not in (FollowupPriority.HIGH, FollowupPriority.CRITICAL_REVIEW):
            return PolicyDecision.deny(
                "CRITICAL_SAFETY_PRIORITY_REQUIRED",
                "Case has active CRITICAL safety state. Follow-up must have HIGH or CRITICAL_REVIEW priority, and cannot defer emergency intervention."
            )
    return PolicyDecision.allow()
