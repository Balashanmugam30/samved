import logging
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional, Set
from app.core.errors import AppException

logger = logging.getLogger("samved.telephony.state")


class CallState(str, Enum):
    NEW = "NEW"
    RINGING = "RINGING"
    CONNECTING = "CONNECTING"
    CONNECTED = "CONNECTED"
    STREAMING = "STREAMING"
    ENDING = "ENDING"
    ENDED = "ENDED"
    FAILED = "FAILED"


# Valid state transitions matrix
VALID_TRANSITIONS: Dict[CallState, Set[CallState]] = {
    CallState.NEW: {CallState.RINGING, CallState.CONNECTING, CallState.FAILED, CallState.ENDED},
    CallState.RINGING: {CallState.CONNECTING, CallState.CONNECTED, CallState.FAILED, CallState.ENDED},
    CallState.CONNECTING: {CallState.CONNECTED, CallState.STREAMING, CallState.FAILED, CallState.ENDED},
    CallState.CONNECTED: {CallState.STREAMING, CallState.ENDING, CallState.ENDED, CallState.FAILED},
    CallState.STREAMING: {CallState.ENDING, CallState.ENDED, CallState.FAILED},
    CallState.ENDING: {CallState.ENDED, CallState.FAILED},
    CallState.ENDED: set(),  # Terminal state
    CallState.FAILED: set(),  # Terminal state
}


class CallStateMachine:
    """Manages explicit lifecycle transitions for a telephony call."""

    def __init__(self, call_id: str, initial_state: CallState = CallState.NEW):
        self.call_id = call_id
        self.current_state = initial_state
        self.history: List[Dict[str, str]] = [
            {
                "state": initial_state.value,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "reason": "initialized",
            }
        ]
        self.created_at = datetime.now(timezone.utc).isoformat()
        self.ended_at: Optional[str] = None
        self.disconnect_reason: Optional[str] = None

    def can_transition_to(self, target_state: CallState) -> bool:
        return target_state in VALID_TRANSITIONS.get(self.current_state, set())

    def transition_to(self, target_state: CallState, reason: str = "") -> None:
        if target_state == self.current_state:
            return  # Idempotent no-op

        if not self.can_transition_to(target_state):
            err_msg = (
                f"Invalid telephony transition from {self.current_state.value} to {target_state.value} "
                f"for call {self.call_id}"
            )
            logger.error(err_msg)
            raise AppException(
                code="INVALID_STATE_TRANSITION",
                message=err_msg,
                details={
                    "call_id": self.call_id,
                    "current_state": self.current_state.value,
                    "target_state": target_state.value,
                },
            )

        now = datetime.now(timezone.utc).isoformat()
        previous_state = self.current_state
        self.current_state = target_state
        self.history.append({"state": target_state.value, "timestamp": now, "reason": reason})

        if target_state in {CallState.ENDED, CallState.FAILED}:
            self.ended_at = now
            self.disconnect_reason = reason or target_state.value.lower()

        logger.info(
            f"Call {self.call_id} transitioned: {previous_state.value} -> {target_state.value} ({reason})"
        )

    @property
    def is_active(self) -> bool:
        return self.current_state not in {CallState.ENDED, CallState.FAILED}

    @property
    def is_streaming(self) -> bool:
        return self.current_state == CallState.STREAMING
