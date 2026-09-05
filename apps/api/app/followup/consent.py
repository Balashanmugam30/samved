"""Consent State Machine and Revocation Engine for SAMVED Follow-up Subsystem."""

from datetime import datetime, timezone
import logging
from typing import Dict, List, Optional, Set, Tuple

from app.followup.models import FollowupConsent, FollowupRecord
from app.schemas.events import ConsentState, FollowupStatus

logger = logging.getLogger("samved.followup.consent")

# Permitted state transitions for caller consent
VALID_CONSENT_TRANSITIONS: Dict[ConsentState, Set[ConsentState]] = {
    ConsentState.UNKNOWN: {ConsentState.REQUESTED, ConsentState.GRANTED, ConsentState.LIMITED, ConsentState.REFUSED, ConsentState.NOT_APPLICABLE},
    ConsentState.REQUESTED: {ConsentState.GRANTED, ConsentState.LIMITED, ConsentState.REFUSED, ConsentState.REVOKED},
    ConsentState.GRANTED: {ConsentState.LIMITED, ConsentState.REVOKED},
    ConsentState.LIMITED: {ConsentState.GRANTED, ConsentState.REVOKED},
    ConsentState.REFUSED: {ConsentState.REQUESTED, ConsentState.GRANTED},  # Caller can voluntarily change mind later if asked
    ConsentState.REVOKED: {ConsentState.REQUESTED, ConsentState.GRANTED},  # Explicit renewal required
    ConsentState.NOT_APPLICABLE: {ConsentState.REQUESTED, ConsentState.GRANTED, ConsentState.REFUSED},
}


class ConsentTransitionResult:
    def __init__(self, valid: bool, previous_state: ConsentState, new_state: ConsentState, message: Optional[str] = None):
        self.valid = valid
        self.previous_state = previous_state
        self.new_state = new_state
        self.message = message


def validate_consent_transition(current_state: ConsentState, next_state: ConsentState) -> ConsentTransitionResult:
    """Validates whether a consent state transition is structurally permitted."""
    allowed = VALID_CONSENT_TRANSITIONS.get(current_state, set())
    if next_state not in allowed:
        return ConsentTransitionResult(
            valid=False,
            previous_state=current_state,
            new_state=next_state,
            message=f"Illegal consent transition from {current_state} to {next_state}."
        )
    return ConsentTransitionResult(valid=True, previous_state=current_state, new_state=next_state)


def apply_consent_revocation(
    case_id: str,
    followups: List[FollowupRecord],
    reason: str,
    operator_id: str
) -> Tuple[List[FollowupRecord], FollowupConsent]:
    """Atomically cascades consent revocation to all active follow-ups for a case.
    
    Any follow-up in DRAFT, PENDING_APPROVAL, SCHEDULED, READY, or IN_PROGRESS
    is transitioned to BLOCKED with reason CONSENT_REVOKED.
    """
    now_iso = datetime.now(timezone.utc).isoformat()
    active_statuses = {
        FollowupStatus.DRAFT,
        FollowupStatus.PENDING_APPROVAL,
        FollowupStatus.SCHEDULED,
        FollowupStatus.READY,
        FollowupStatus.IN_PROGRESS,
    }
    
    blocked_followups: List[FollowupRecord] = []
    for f in followups:
        if f.case_id == case_id and f.status in active_statuses:
            f.status = FollowupStatus.BLOCKED
            f.consent_state = ConsentState.REVOKED
            f.blocked_reason = f"CONSENT_REVOKED: {reason}"
            f.updated_at = now_iso
            blocked_followups.append(f)
            logger.warning(
                f"Follow-up {f.followup_id} in case {case_id} BLOCKED due to caller consent revocation."
            )
            
    consent_record = FollowupConsent(
        case_id=case_id,
        consent_state=ConsentState.REVOKED,
        purpose="ALL_PURPOSES",
        recorded_by=operator_id,
        recorded_at=now_iso,
        revoked_at=now_iso,
        notes=f"Caller explicitly revoked consent: {reason}"
    )
    
    return blocked_followups, consent_record
