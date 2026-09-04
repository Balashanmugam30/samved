from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
import uuid
from pydantic import BaseModel, Field

from app.schemas.events import (
    HandoffStatus,
    OperatorNoteCategory,
    OperatorOwnershipState,
)


class OperatorActionType(str, Enum):
    TAKEOVER = "TAKEOVER"
    RESUME_AI = "RESUME_AI"
    PAUSE_ADAPTIVE = "PAUSE_ADAPTIVE"
    RESUME_ADAPTIVE = "RESUME_ADAPTIVE"
    REQUEST_SAFETY_CHECK = "REQUEST_SAFETY_CHECK"
    HANDOFF_REQUEST = "HANDOFF_REQUEST"
    HANDOFF_CONFIRM = "HANDOFF_CONFIRM"
    HANDOFF_CANCEL = "HANDOFF_CANCEL"
    ADD_NOTE = "ADD_NOTE"
    END_CALL = "END_CALL"


class OperatorNote(BaseModel):
    note_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    call_id: str
    operator_id: str = "operator"
    category: OperatorNoteCategory = OperatorNoteCategory.GENERAL
    text: str
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    is_structured: bool = True


class OperatorAuditEvent(BaseModel):
    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    call_id: str
    action: OperatorActionType
    actor_id: str = "operator"
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    category: str = "OPERATOR"
    summary: str
    previous_state: Optional[str] = None
    new_state: Optional[str] = None
    details: Dict[str, Any] = Field(default_factory=dict)


class CallOperatorState(BaseModel):
    call_id: str
    ownership_state: OperatorOwnershipState = OperatorOwnershipState.AI_ASSISTED
    handoff_status: HandoffStatus = HandoffStatus.AVAILABLE
    adaptive_paused: bool = False
    active_operator_id: Optional[str] = None
    handoff_target: Optional[str] = None
    handoff_notes: Optional[str] = None
    handoff_requested_at: Optional[str] = None
    handoff_confirmed_at: Optional[str] = None
    updated_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
