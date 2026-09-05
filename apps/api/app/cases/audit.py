"""In-Memory Ring-Buffer Audit Logger for Case Intelligence (Phase 11)."""

from collections import deque
from datetime import datetime, timezone
import threading
from typing import Any, Dict, List, Optional
import uuid
from pydantic import BaseModel, Field


class CaseAuditEntry(BaseModel):
    """Immutable audit record for case mutations and decisions."""

    entry_id: str = Field(default_factory=lambda: f"aud-{uuid.uuid4().hex[:12]}")
    case_id: str
    action: str
    actor_id: str
    details: Dict[str, Any] = Field(default_factory=dict)
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


class CaseAuditLogger:
    """Thread-safe bounded ring buffer retaining recent case mutation audits."""

    def __init__(self, max_capacity: int = 1000):
        self._capacity = max_capacity
        self._buffer: deque = deque(maxlen=max_capacity)
        self._lock = threading.Lock()

    def log(
        self,
        case_id: str,
        action: str,
        actor_id: str = "system",
        details: Optional[Dict[str, Any]] = None,
    ) -> CaseAuditEntry:
        """Appends an immutable audit entry to the ring buffer."""
        entry = CaseAuditEntry(
            case_id=case_id,
            action=action,
            actor_id=actor_id,
            details=details or {},
        )
        with self._lock:
            self._buffer.append(entry)
        return entry

    def get_logs_for_case(
        self, case_id: str, limit: int = 50
    ) -> List[CaseAuditEntry]:
        """Retrieves audit entries for a case in reverse chronological order."""
        with self._lock:
            entries = [e for e in reversed(self._buffer) if e.case_id == case_id]
        return entries[:limit]

    def get_all_recent(self, limit: int = 100) -> List[CaseAuditEntry]:
        """Retrieves all recent audit entries across all cases."""
        with self._lock:
            return list(reversed(self._buffer))[:limit]

    def clear(self) -> None:
        """Clears all audit entries (primarily for testing)."""
        with self._lock:
            self._buffer.clear()


# Global audit logger instance
_global_audit_logger = CaseAuditLogger()


def get_audit_logger() -> CaseAuditLogger:
    """Returns the singleton audit logger."""
    return _global_audit_logger
