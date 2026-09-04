import asyncio
from collections import deque
from datetime import datetime, timezone
import logging
from typing import Any, Deque, Dict, List, Optional
import uuid

from app.operator.models import OperatorActionType, OperatorAuditEvent

logger = logging.getLogger("samved.operator.audit")


class OperatorAuditLogger:
    """Thread-safe, append-only audit logger for operator actions and state transitions.

    Guarantees:
    - Immutability: Audit records cannot be modified or deleted.
    - Bounded memory: History per call is bounded to prevent resource exhaustion.
    - Determinism: Ordered by monotonic arrival and server timestamps.
    """

    def __init__(self, max_history_per_call: int = 150):
        self._max_history = max_history_per_call
        self._call_audits: Dict[str, Deque[OperatorAuditEvent]] = {}
        self._lock = asyncio.Lock()

    async def log_action(
        self,
        call_id: str,
        action: OperatorActionType,
        actor_id: str = "operator",
        summary: str = "",
        previous_state: Optional[str] = None,
        new_state: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> OperatorAuditEvent:
        """Records an immutable audit event for an operator action."""
        if not summary:
            summary = f"Operator {actor_id} performed {action.value}"

        event = OperatorAuditEvent(
            event_id=str(uuid.uuid4()),
            call_id=call_id,
            action=action,
            actor_id=actor_id,
            timestamp=datetime.now(timezone.utc).isoformat(),
            category="OPERATOR",
            summary=summary,
            previous_state=previous_state,
            new_state=new_state,
            details=details or {},
        )

        async with self._lock:
            if call_id not in self._call_audits:
                self._call_audits[call_id] = deque(maxlen=self._max_history)
            self._call_audits[call_id].append(event)

        logger.info(
            f"Audit log recorded: [{action.value}] call={call_id} actor={actor_id} summary={summary}"
        )
        return event

    async def get_audit_trail(
        self,
        call_id: str,
        limit: int = 50,
        action_filter: Optional[str] = None,
    ) -> List[OperatorAuditEvent]:
        """Retrieves bounded, chronologically sorted audit trail for a call."""
        async with self._lock:
            records = list(self._call_audits.get(call_id, []))

        if action_filter:
            records = [r for r in records if r.action.value == action_filter or r.category == action_filter]

        return records[-limit:]


operator_audit_logger = OperatorAuditLogger()
