from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from app.operator.models import (
    CallOperatorState,
    HandoffStatus,
    OperatorActionType,
    OperatorAuditEvent,
    OperatorNote,
    OperatorNoteCategory,
    OperatorOwnershipState,
)


class TakeoverRequest(BaseModel):
    reason: str = Field(default="Operator initiated human takeover", min_length=2)
    operator_id: str = Field(default="operator")


class PauseRequest(BaseModel):
    reason: str = Field(default="Operator paused adaptive AI assistance", min_length=2)
    operator_id: str = Field(default="operator")


class ResumeRequest(BaseModel):
    reason: str = Field(default="Operator resumed AI assistance", min_length=2)
    operator_id: str = Field(default="operator")


class SafetyCheckRequest(BaseModel):
    reason: str = Field(default="Operator requested immediate safety verification", min_length=2)
    operator_id: str = Field(default="operator")


class HandoffRequest(BaseModel):
    target_department: str = Field(default="tele_counselor_tier2")
    notes: Optional[str] = Field(default=None)
    operator_id: str = Field(default="operator")


class HandoffConfirmRequest(BaseModel):
    transfer_confirmed_by: str = Field(default="supervisor")
    target_agent: Optional[str] = Field(default="counselor-01")
    notes: Optional[str] = Field(default=None)


class HandoffCancelRequest(BaseModel):
    reason: str = Field(default="Operator cancelled transfer request", min_length=2)
    operator_id: str = Field(default="operator")


class AddNoteRequest(BaseModel):
    category: OperatorNoteCategory = Field(default=OperatorNoteCategory.GENERAL)
    text: str = Field(..., min_length=1)
    operator_id: str = Field(default="operator")


class EndCallRequest(BaseModel):
    reason: str = Field(default="Operator concluded call", min_length=2)
    operator_id: str = Field(default="operator")


class SubsystemStatus(BaseModel):
    name: str
    status: str  # AVAILABLE, DEGRADED, UNAVAILABLE
    details: str
    version: Optional[str] = None


class OperatorStatusResponse(BaseModel):
    status: str = "healthy"
    app_mode: str = "DEV"
    subsystems: List[SubsystemStatus]
    active_operators_count: int = 1
    total_active_calls: int = 0
    timestamp: str


class TimelineEventItem(BaseModel):
    event_id: str
    timestamp: str
    category: str  # OPERATOR, SAFETY, SVI, ACOUSTIC, ADAPTIVE, SYSTEM
    event_type: str
    summary: str
    actor_id: Optional[str] = None
    details: Dict[str, Any] = Field(default_factory=dict)


class OperatorTimelineResponse(BaseModel):
    call_id: str
    events: List[TimelineEventItem]
    total_events: int


class OperatorNotesListResponse(BaseModel):
    call_id: str
    notes: List[OperatorNote]
    total_notes: int


class OperatorActionResponse(BaseModel):
    success: bool = True
    action: str
    call_id: str
    ownership_state: str
    handoff_status: str
    message: str
    timestamp: str
