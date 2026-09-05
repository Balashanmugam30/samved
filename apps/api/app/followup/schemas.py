"""Pydantic API request and response schemas for SAMVED Follow-up Workflow."""

from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field

from app.followup.models import (
    ContactPreferences,
    FollowupAttempt,
    FollowupRecord,
    FollowupWorkqueueSummary,
)
from app.schemas.events import (
    ConsentState,
    ContactChannel,
    ContactResult,
    FollowupOutcome,
    FollowupPriority,
    FollowupStatus,
    FollowupType,
    RecurrenceRule,
)


class CreateFollowupRequest(BaseModel):
    call_id: Optional[str] = None
    type: FollowupType = FollowupType.HUMAN_CALLBACK
    priority: FollowupPriority = FollowupPriority.NORMAL
    channel: ContactChannel = ContactChannel.OPERATOR_CALLBACK
    purpose: str
    scheduled_for: str  # ISO-8601 UTC
    due_at: Optional[str] = None  # ISO-8601 UTC; defaults to scheduled_for + 2h if not provided
    consent_state: ConsentState = ConsentState.GRANTED
    contact_preferences: Optional[ContactPreferences] = None
    safe_contact_window: Optional[str] = None
    assigned_to: Optional[str] = None
    notes_ref: Optional[str] = None
    citation_ref: Optional[str] = None
    recurrence: Optional[RecurrenceRule] = RecurrenceRule.ONCE
    recurrence_max: int = 1
    operator_id: str = "operator"


class ApproveFollowupRequest(BaseModel):
    operator_id: str = "operator"
    notes: Optional[str] = None


class ScheduleFollowupRequest(BaseModel):
    scheduled_for: str
    due_at: Optional[str] = None
    safe_contact_window: Optional[str] = None
    operator_id: str = "operator"


class AssignFollowupRequest(BaseModel):
    assigned_to: str
    operator_id: str = "operator"


class StartFollowupRequest(BaseModel):
    operator_id: str = "operator"


class RecordAttemptRequest(BaseModel):
    channel: Union[ContactChannel, str] = ContactChannel.OPERATOR_CALLBACK
    result: Union[ContactResult, str] = ContactResult.CONTACTED_SUCCESSFULLY
    notes: Optional[str] = None
    operator_id: str = "operator"


class CompleteFollowupRequest(BaseModel):
    outcome: Union[FollowupOutcome, str] = FollowupOutcome.CONTACTED_SUCCESSFULLY
    notes_ref: Optional[str] = None
    channel_used: Optional[Union[ContactChannel, str]] = None
    operator_id: str = "operator"


class RescheduleFollowupRequest(BaseModel):
    scheduled_for: str
    due_at: Optional[str] = None
    safe_contact_window: Optional[str] = None
    reason: str
    operator_id: str = "operator"


class CancelFollowupRequest(BaseModel):
    reason: str
    operator_id: str = "operator"


class RevokeConsentRequest(BaseModel):
    reason: str
    operator_id: str = "operator"


class FollowupListResponse(BaseModel):
    items: List[FollowupRecord]
    total: int
    limit: int
    offset: int
    summary: FollowupWorkqueueSummary


class FollowupActionResponse(BaseModel):
    success: bool
    message: str
    followup: FollowupRecord
