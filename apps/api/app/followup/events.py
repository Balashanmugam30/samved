"""Event builders for SAMVED Follow-up Subsystem."""

from datetime import datetime, timezone
from typing import Any, Dict, Optional
import uuid

from app.followup.models import FollowupAttempt, FollowupRecord
from app.schemas.events import EventEnvelope, EventType, FollowupStatus


def create_followup_event(
    event_type: EventType,
    followup: FollowupRecord,
    actor_id: str,
    previous_status: Optional[FollowupStatus] = None,
    reason: Optional[str] = None,
    attempt: Optional[FollowupAttempt] = None,
    details: Optional[Dict[str, Any]] = None,
) -> EventEnvelope:
    """Creates a canonical EventEnvelope for follow-up state mutations."""
    payload: Dict[str, Any] = {
        "followup_id": followup.followup_id,
        "case_id": followup.case_id,
        "call_id": followup.call_id,
        "status": followup.status.value,
        "previous_status": previous_status.value if previous_status else None,
        "actor_id": actor_id,
        "purpose": followup.purpose,
        "priority": followup.priority.value,
        "scheduled_for": followup.scheduled_for,
        "due_at": followup.due_at,
        "consent_state": followup.consent_state.value,
        "channel": followup.channel.value,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "reason": reason,
        "details": details or {},
    }
    
    if attempt:
        payload["attempt"] = {
            "attempt_id": attempt.attempt_id,
            "attempt_number": attempt.attempt_number,
            "channel": attempt.channel if isinstance(attempt.channel, str) else attempt.channel.value,
            "result": attempt.result if isinstance(attempt.result, str) else attempt.result.value,
            "notes": attempt.notes,
        }
    if followup.outcome:
        payload["outcome"] = followup.outcome if isinstance(followup.outcome, str) else followup.outcome.value

    return EventEnvelope(
        event_id=str(uuid.uuid4()),
        event_type=event_type,
        schema_version="1.0",
        timestamp=datetime.now(timezone.utc).isoformat(),
        session_id=followup.call_id or followup.case_id or "system",
        call_id=followup.call_id or "system",
        case_id=followup.case_id,
        payload=payload,
    )
