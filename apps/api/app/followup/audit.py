"""Thread-safe in-memory ring-buffer audit logger for SAMVED Follow-up Workflow."""

from collections import deque
from datetime import datetime, timezone
import logging
from threading import Lock
from typing import Any, Dict, List, Optional
import uuid
from pydantic import BaseModel, Field

from app.schemas.events import FollowupStatus

logger = logging.getLogger("samved.followup.audit")


class FollowupAuditRecord(BaseModel):
    """Immutable audit record detailing an administrative or operational follow-up action."""

    audit_id: str = Field(default_factory=lambda: f"faud-{uuid.uuid4().hex[:10]}")
    followup_id: str
    case_id: str
    actor_id: str
    action: str  # CREATED, APPROVED, SCHEDULED, ASSIGNED, STARTED, ATTEMPTED, COMPLETED, RESCHEDULED, CANCELLED, BLOCKED, CONSENT_REVOKED
    previous_status: Optional[FollowupStatus] = None
    new_status: Optional[FollowupStatus] = None
    reason: Optional[str] = None
    details: Dict[str, Any] = Field(default_factory=dict)
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


class FollowupAuditLogger:
    """Bounded, thread-safe ring-buffer audit logger."""

    def __init__(self, max_entries: int = 5000):
        self._entries: deque = deque(maxlen=max_entries)
        self._lock = Lock()

    def log(
        self,
        followup_id: str,
        case_id: str,
        actor_id: str,
        action: str,
        previous_status: Optional[FollowupStatus] = None,
        new_status: Optional[FollowupStatus] = None,
        reason: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> FollowupAuditRecord:
        record = FollowupAuditRecord(
            followup_id=followup_id,
            case_id=case_id,
            actor_id=actor_id,
            action=action,
            previous_status=previous_status,
            new_status=new_status,
            reason=reason,
            details=details or {},
        )
        with self._lock:
            self._entries.append(record)
        logger.info(
            f"[AUDIT:FOLLOWUP] {action} on {followup_id} by {actor_id} (Reason: {reason or 'None'})"
        )
        return record

    def get_logs_for_followup(self, followup_id: str) -> List[FollowupAuditRecord]:
        with self._lock:
            return [e for e in self._entries if e.followup_id == followup_id]

    def get_logs_for_case(self, case_id: str) -> List[FollowupAuditRecord]:
        with self._lock:
            return [e for e in self._entries if e.case_id == case_id]

    def get_all_logs(self) -> List[FollowupAuditRecord]:
        with self._lock:
            return list(self._entries)

    def clear(self) -> None:
        with self._lock:
            self._entries.clear()


_audit_logger_singleton: Optional[FollowupAuditLogger] = None
_audit_lock = Lock()


def get_audit_logger() -> FollowupAuditLogger:
    global _audit_logger_singleton
    if _audit_logger_singleton is None:
        with _audit_lock:
            if _audit_logger_singleton is None:
                _audit_logger_singleton = FollowupAuditLogger()
    return _audit_logger_singleton
