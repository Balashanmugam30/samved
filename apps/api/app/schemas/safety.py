import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class SafetySignalType(str, Enum):
    IMMEDIATE_DANGER = "IMMEDIATE_DANGER"
    ACTIVE_VIOLENCE = "ACTIVE_VIOLENCE"
    ACTIVE_THREAT = "ACTIVE_THREAT"
    WEAPON_MENTION = "WEAPON_MENTION"
    WEAPON_THREAT = "WEAPON_THREAT"
    SELF_HARM = "SELF_HARM"
    SUICIDE_RISK = "SUICIDE_RISK"
    ONGOING_THREAT = "ONGOING_THREAT"
    COERCION = "COERCION"
    CONFINEMENT = "CONFINEMENT"
    STALKING = "STALKING"
    CHILD_SAFETY = "CHILD_SAFETY"
    MEDICAL_EMERGENCY = "MEDICAL_EMERGENCY"
    UNSAFE_LOCATION = "UNSAFE_LOCATION"
    IMMEDIATE_ESCAPE_NEED = "IMMEDIATE_ESCAPE_NEED"


class SafetySeverity(str, Enum):
    NONE = "NONE"
    INFO = "INFO"
    LOW = "LOW"
    MODERATE = "MODERATE"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class SafetyState(str, Enum):
    NONE = "NONE"
    WATCH = "WATCH"
    ELEVATED = "ELEVATED"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class SafetyEvidence(BaseModel):
    rule_id: str
    rule_version: str = "v1"
    matched_category: str
    matched_phrase: str
    reason: str
    source_utterance_id: Optional[str] = None
    temporal_context: str = "PRESENT"  # PRESENT | PAST | HYPOTHETICAL
    negated: bool = False


class SafetySignal(BaseModel):
    signal_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    signal_type: SafetySignalType
    severity: SafetySeverity
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    evidence: SafetyEvidence
    rule_id: str
    rule_version: str = "v1"
    call_id: str
    session_id: str
    utterance_id: Optional[str] = None
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    requires_human_review: bool = True
    acknowledged: bool = False
    acknowledged_at: Optional[str] = None
    acknowledged_by: Optional[str] = None


class SafetyAssessment(BaseModel):
    assessment_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    call_id: str
    session_id: str
    current_state: SafetyState = SafetyState.NONE
    highest_severity: SafetySeverity = SafetySeverity.INFO
    signals: List[SafetySignal] = Field(default_factory=list)
    requires_human_review: bool = False
    safety_engine_version: str = "v1"
    evaluated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    evidence_refs: List[str] = Field(default_factory=list)
