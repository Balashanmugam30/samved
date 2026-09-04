from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class RoleType(str, Enum):
    ADMIN = "ADMIN"
    SUPERVISOR = "SUPERVISOR"
    OPERATOR = "OPERATOR"
    AUDITOR = "AUDITOR"


class UserBase(BaseModel):
    email: str
    full_name: str
    role: RoleType = RoleType.OPERATOR
    is_active: bool = True


class CaseStatus(str, Enum):
    INTAKE = "INTAKE"
    TRIAGED = "TRIAGED"
    ESCALATED = "ESCALATED"
    FOLLOW_UP_PENDING = "FOLLOW_UP_PENDING"
    CLOSED = "CLOSED"


class CaseBase(BaseModel):
    case_number: str
    status: CaseStatus = CaseStatus.INTAKE
    primary_language: str = "hi-IN"
    svi_score: Optional[int] = Field(None, ge=0, le=100)
    svi_band: Optional[str] = None
    consent_recorded: bool = False
    notes_summary: Optional[str] = None


class CallBase(BaseModel):
    telephony_provider: str = "exotel"
    external_call_id: str
    caller_masked_number: str
    status: str = "in_progress"
    case_id: Optional[str] = None


class SafetyAlertBase(BaseModel):
    call_id: str
    alert_level: str
    trigger_reason: str
    status: str = "ACTIVE"
    acknowledged_by: Optional[str] = None


class RecommendationBase(BaseModel):
    case_id: str
    category: str
    title: str
    description: str
    legal_grounding_ref: Optional[str] = None
