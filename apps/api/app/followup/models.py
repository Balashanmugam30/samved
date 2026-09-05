"""Pydantic domain models for SAMVED Phase 12 Follow-up Workflow & Continuity Engine."""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Union
import uuid
from pydantic import BaseModel, Field

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


class ContactPreferences(BaseModel):
    """Caller preferences and safety constraints regarding follow-up contact."""

    preferred_channel: Union[ContactChannel, str] = ContactChannel.OPERATOR_CALLBACK
    preferred_time_window: Optional[str] = None  # e.g. "18:00-20:00"
    days_allowed: List[str] = Field(default_factory=lambda: ["MON", "TUE", "WED", "THU", "FRI"])
    safe_to_contact: bool = True
    preferred_language: Optional[str] = "en-IN"
    human_only: bool = True
    no_voicemail: bool = False
    no_text: bool = False
    timezone: Optional[str] = "Asia/Kolkata"


class FollowupAttempt(BaseModel):
    """Record of a discrete contact attempt by an operator."""

    attempt_id: str = Field(default_factory=lambda: f"att-{uuid.uuid4().hex[:10]}")
    followup_id: str
    case_id: str
    attempt_number: int
    attempted_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    operator_id: str
    channel: Union[ContactChannel, str]
    result: Union[ContactResult, str]
    notes: Optional[str] = None


class FollowupConsent(BaseModel):
    """Audit record of caller consent given, limited, refused, or revoked."""

    consent_id: str = Field(default_factory=lambda: f"cns-{uuid.uuid4().hex[:10]}")
    case_id: str
    followup_id: Optional[str] = None
    consent_state: ConsentState = ConsentState.UNKNOWN
    purpose: str
    channel: Union[ContactChannel, str] = ContactChannel.OPERATOR_CALLBACK
    recorded_by: str
    recorded_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    revoked_at: Optional[str] = None
    notes: Optional[str] = None


class FollowupEvent(BaseModel):
    """Immutable event audit record for follow-up state transitions."""

    event_id: str = Field(default_factory=lambda: f"fev-{uuid.uuid4().hex[:10]}")
    followup_id: str
    case_id: str
    event_type: str
    actor_id: str
    previous_status: Optional[FollowupStatus] = None
    new_status: FollowupStatus
    reason: Optional[str] = None
    details: Dict[str, Any] = Field(default_factory=dict)
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


class FollowupRecord(BaseModel):
    """Core domain model representing a bounded, auditable follow-up task."""

    followup_id: str = Field(default_factory=lambda: f"fol-{uuid.uuid4().hex[:10]}")
    case_id: str
    call_id: Optional[str] = None
    created_by: str
    assigned_to: Optional[str] = None
    type: FollowupType = FollowupType.HUMAN_CALLBACK
    status: FollowupStatus = FollowupStatus.DRAFT
    priority: FollowupPriority = FollowupPriority.NORMAL
    requested_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    scheduled_for: str  # ISO-8601 UTC
    due_at: str  # ISO-8601 UTC
    completed_at: Optional[str] = None
    cancelled_at: Optional[str] = None
    consent_state: ConsentState = ConsentState.UNKNOWN
    contact_preferences: ContactPreferences = Field(default_factory=ContactPreferences)
    safe_contact_window: Optional[str] = None  # e.g. "18:00-20:00"
    channel: ContactChannel = ContactChannel.OPERATOR_CALLBACK
    purpose: str
    notes_ref: Optional[str] = None
    citation_ref: Optional[str] = None
    source_event: Optional[str] = None
    last_attempt_at: Optional[str] = None
    attempt_count: int = 0
    max_attempts: int = 2
    outcome: Optional[Union[FollowupOutcome, str]] = None
    policy_version: str = "v1.0"
    blocked_reason: Optional[str] = None
    recurrence: Optional[RecurrenceRule] = RecurrenceRule.ONCE
    recurrence_max: int = 1
    recurrence_count: int = 0
    created_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    updated_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


class FollowupWorkqueueSummary(BaseModel):
    """Summary counts for operator follow-up workqueue."""

    total_active: int = 0
    due_today: int = 0
    overdue: int = 0
    blocked: int = 0
    completed_today: int = 0
