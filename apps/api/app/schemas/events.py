import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class EventType(str, Enum):
    # Telephony lifecycle
    CALL_STARTED = "CALL_STARTED"
    CALL_CONNECTED = "CALL_CONNECTED"
    CALL_ENDED = "CALL_ENDED"

    # Language & speech
    LANGUAGE_DETECTED = "LANGUAGE_DETECTED"
    LANGUAGE_CHANGED = "LANGUAGE_CHANGED"
    TRANSCRIPT_PARTIAL = "TRANSCRIPT_PARTIAL"
    TRANSCRIPT_FINAL = "TRANSCRIPT_FINAL"
    ACOUSTIC_UPDATE = "ACOUSTIC_UPDATE"

    # Safety & risk
    SAFETY_SIGNAL = "SAFETY_SIGNAL"
    SAFETY_STATE_UPDATED = "SAFETY_STATE_UPDATED"
    SAFETY_SIGNAL_ACKNOWLEDGED = "SAFETY_SIGNAL_ACKNOWLEDGED"
    RISK_UPDATED = "RISK_UPDATED"
    SVI_UPDATED = "SVI_UPDATED"

    # Multi-agent & AI response
    AGENT_ACTION = "AGENT_ACTION"
    AI_THINKING = "AI_THINKING"
    AI_RESPONSE_STARTED = "AI_RESPONSE_STARTED"
    AI_RESPONSE_ENDED = "AI_RESPONSE_ENDED"
    TTS_STARTED = "TTS_STARTED"
    TTS_ENDED = "TTS_ENDED"
    SPEECH_INTERRUPTED = "SPEECH_INTERRUPTED"
    CONVERSATION_STATE_CHANGED = "CONVERSATION_STATE_CHANGED"
    TURN_LATENCY = "TURN_LATENCY"
    OPERATOR_SNAPSHOT = "OPERATOR_SNAPSHOT"
    STT_ERROR = "STT_ERROR"
    LLM_ERROR = "LLM_ERROR"
    TTS_ERROR = "TTS_ERROR"

    # Escalation & human oversight
    HUMAN_ALERT = "HUMAN_ALERT"
    ESCALATION_RECOMMENDED = "ESCALATION_RECOMMENDED"
    ESCALATION_ACCEPTED = "ESCALATION_ACCEPTED"
    ESCALATION_OVERRIDDEN = "ESCALATION_OVERRIDDEN"

    # Case & follow-up
    CASE_CREATED = "CASE_CREATED"
    FOLLOWUP_SCHEDULED = "FOLLOWUP_SCHEDULED"

    # Heartbeat
    HEARTBEAT_PING = "HEARTBEAT_PING"
    HEARTBEAT_PONG = "HEARTBEAT_PONG"


class EventEnvelope(BaseModel):
    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    event_type: EventType
    schema_version: str = "1.0"
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    session_id: str
    call_id: str
    case_id: Optional[str] = None
    payload: Dict[str, Any] = Field(default_factory=dict)


class SVIBand(str, Enum):
    LOW = "LOW"             # 0–25
    MODERATE = "MODERATE"   # 26–50
    HIGH = "HIGH"           # 51–75
    CRITICAL = "CRITICAL"    # 76–100


class SVIContributingFactor(BaseModel):
    factor: str
    weight: float
    evidence: str


class SVIUpdatedPayload(BaseModel):
    score: int = Field(..., ge=0, le=100)
    band: SVIBand
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    contributing_factors: List[SVIContributingFactor] = Field(default_factory=list)
    trend: str = "INITIAL"
    delta: int = 0
    assessment_completeness: float = Field(default=0.0, ge=0.0, le=1.0)
    top_contributors: List[str] = Field(default_factory=list)
    protective_factor_reduction: int = 0
    critical_override_applied: bool = False
    requires_human_review: bool = False
    acoustic_evidence_note: str = "Acoustic evidence: Not available in current phase (Phase 6 deferred)"
    is_clinical_diagnosis: bool = False  # Guaranteed non-clinical


class SafetySignalPayload(BaseModel):
    signal_type: str
    triggered_by: str
    severity: str
    description: str
    requires_human_confirmation: bool = True
