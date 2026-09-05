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

    # Adaptive conversation policy (Phase 7)
    ADAPTIVE_STRATEGY_SELECTED = "ADAPTIVE_STRATEGY_SELECTED"

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

    # Human Operator Workstation (Phase 8)
    OPERATOR_TAKEOVER = "OPERATOR_TAKEOVER"
    OPERATOR_RESUME_AI = "OPERATOR_RESUME_AI"
    OPERATOR_PAUSE_ADAPTIVE = "OPERATOR_PAUSE_ADAPTIVE"
    OPERATOR_REQUEST_SAFETY_CHECK = "OPERATOR_REQUEST_SAFETY_CHECK"
    OPERATOR_HANDOFF_REQUESTED = "OPERATOR_HANDOFF_REQUESTED"
    OPERATOR_HANDOFF_CONFIRMED = "OPERATOR_HANDOFF_CONFIRMED"
    OPERATOR_HANDOFF_CANCELLED = "OPERATOR_HANDOFF_CANCELLED"
    OPERATOR_NOTE_ADDED = "OPERATOR_NOTE_ADDED"
    OPERATOR_CALL_ENDED = "OPERATOR_CALL_ENDED"
    OPERATOR_STATE_CHANGED = "OPERATOR_STATE_CHANGED"

    # Multi-Agent Orchestration (Phase 9)
    ORCHESTRATION_STARTED = "ORCHESTRATION_STARTED"
    ORCHESTRATION_COMPLETED = "ORCHESTRATION_COMPLETED"
    ORCHESTRATION_DEGRADED = "ORCHESTRATION_DEGRADED"
    AGENT_STARTED = "AGENT_STARTED"
    AGENT_COMPLETED = "AGENT_COMPLETED"
    AGENT_FAILED = "AGENT_FAILED"
    AGENT_TIMEOUT = "AGENT_TIMEOUT"
    AGENT_CANCELLED = "AGENT_CANCELLED"
    OPERATOR_BRIEFING_GENERATED = "OPERATOR_BRIEFING_GENERATED"

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


class AcousticSignalItem(BaseModel):
    code: str
    evidence: str
    confidence: float = 1.0


class AcousticUpdatePayload(BaseModel):
    quality: str = "GOOD"
    confidence: float = 1.0
    speech_activity_ratio: float = 0.0
    silence_ratio: float = 1.0
    longest_pause_ms: int = 0
    pause_count: int = 0
    interruption_count: int = 0
    energy_variability: float = 0.0
    mean_energy_rms: float = 0.0
    median_f0_hz: Optional[float] = None
    signals: List[AcousticSignalItem] = Field(default_factory=list)
    engine_version: str = "v1.0.0"
    disclaimer: str = (
        "Acoustic analysis is an operational support signal and is not a clinical, medical, "
        "diagnostic, lie-detection, credibility, or psychological state classifier."
    )
    is_supporting_signal: bool = True


class AdaptiveStrategySelectedPayload(BaseModel):
    call_id: str
    session_id: str
    turn_index: int = 0
    action: str
    priority: str
    target_information: str
    reason_codes: List[str] = Field(default_factory=list)
    evidence_refs: List[str] = Field(default_factory=list)
    language: str = "en-IN"
    confidence: float = 1.0
    constraints: List[str] = Field(default_factory=list)
    requires_human_review: bool = False
    operator_override_active: bool = False
    fallback_applied: bool = False
    disclaimer: str = (
        "Adaptive Conversation is an operational conversational planning layer. It is not a clinical, "
        "medical, diagnostic, legal, credibility, lie-detection, or autonomous emergency-dispatch system."
    )
    evaluated_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


class OperatorOwnershipState(str, Enum):
    UNASSIGNED = "UNASSIGNED"
    AI_ASSISTED = "AI_ASSISTED"
    HUMAN_ASSIGNED = "HUMAN_ASSIGNED"
    HUMAN_ACTIVE = "HUMAN_ACTIVE"
    HANDOFF_PENDING = "HANDOFF_PENDING"
    ENDED = "ENDED"


class HandoffStatus(str, Enum):
    AVAILABLE = "AVAILABLE"
    REQUESTED = "REQUESTED"
    PENDING = "PENDING"
    CONFIRMED = "CONFIRMED"
    CANCELLED = "CANCELLED"
    FAILED = "FAILED"


class OperatorNoteCategory(str, Enum):
    GENERAL = "GENERAL"
    SAFETY = "SAFETY"
    FOLLOW_UP_NOTE = "FOLLOW_UP_NOTE"
    HANDOFF_NOTE = "HANDOFF_NOTE"
    TECHNICAL = "TECHNICAL"


class OperatorNotePayload(BaseModel):
    note_id: str
    call_id: str
    operator_id: str = "operator"
    category: OperatorNoteCategory = OperatorNoteCategory.GENERAL
    text: str
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    is_structured: bool = True


class OperatorActionPayload(BaseModel):
    action_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    call_id: str
    actor_id: str = "operator"
    action_type: str
    previous_state: Optional[str] = None
    new_state: Optional[str] = None
    details: Dict[str, Any] = Field(default_factory=dict)
    summary: str
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


class OperatorStateChangedPayload(BaseModel):
    call_id: str
    ownership_state: OperatorOwnershipState = OperatorOwnershipState.AI_ASSISTED
    handoff_status: HandoffStatus = HandoffStatus.AVAILABLE
    adaptive_paused: bool = False
    active_operator_id: Optional[str] = None
    updated_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


# Phase 9 Multi-Agent Orchestration Enums & Contracts
class AgentType(str, Enum):
    DETERMINISTIC_ADAPTER = "DETERMINISTIC_ADAPTER"
    RULE_WORKER = "RULE_WORKER"
    LLM_WORKER = "LLM_WORKER"
    FORMATTER = "FORMATTER"
    SUMMARIZER = "SUMMARIZER"
    INTERFACE_STUB = "INTERFACE_STUB"


class AgentSafetyClassification(str, Enum):
    READ_ONLY_SAFETY = "READ_ONLY_SAFETY"
    OPERATIONAL = "OPERATIONAL"
    ADVISORY = "ADVISORY"
    NON_CRITICAL = "NON_CRITICAL"
    PLACEHOLDER = "PLACEHOLDER"


class AgentTimeoutTier(str, Enum):
    REALTIME_CRITICAL = "REALTIME_CRITICAL"
    REALTIME_NORMAL = "REALTIME_NORMAL"
    BACKGROUND = "BACKGROUND"


class AgentStatus(str, Enum):
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    TIMED_OUT = "TIMED_OUT"
    CANCELLED = "CANCELLED"
    DEGRADED = "DEGRADED"
    UNAVAILABLE = "UNAVAILABLE"


class OrchestrationState(str, Enum):
    READY = "READY"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    DEGRADED = "DEGRADED"
    FAILED = "FAILED"


class AgentResponsePayload(BaseModel):
    request_id: str
    call_id: str
    turn_id: str
    agent_name: str
    agent_version: str
    status: AgentStatus
    result: Dict[str, Any] = Field(default_factory=dict)
    confidence: float = 1.0
    evidence_refs: List[str] = Field(default_factory=list)
    latency_ms: float = 0.0
    warnings: List[str] = Field(default_factory=list)
    produced_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


class OperatorBriefingPayload(BaseModel):
    safety_summary: str
    svi_summary: str
    acoustic_summary: str
    adaptive_recommendation: str
    key_facts: List[str] = Field(default_factory=list)
    evidence_refs: List[str] = Field(default_factory=list)
    confidence: float = 1.0
    generated_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


class OrchestrationResultPayload(BaseModel):
    request_id: str
    call_id: str
    turn_id: str
    state: OrchestrationState
    selected_agents: List[str] = Field(default_factory=list)
    completed_agents: List[str] = Field(default_factory=list)
    failed_agents: List[str] = Field(default_factory=list)
    timed_out_agents: List[str] = Field(default_factory=list)
    cancelled_agents: List[str] = Field(default_factory=list)
    briefing: Optional[OperatorBriefingPayload] = None
    total_latency_ms: float = 0.0
    warnings: List[str] = Field(default_factory=list)
    completed_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


