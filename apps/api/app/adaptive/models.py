import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class AdaptiveAction(str, Enum):
    SAFETY_CHECK = "SAFETY_CHECK"
    ASK_IMMEDIATE_DANGER = "ASK_IMMEDIATE_DANGER"
    ASK_LOCATION = "ASK_LOCATION"
    ASK_SAFE_TO_CONTINUE = "ASK_SAFE_TO_CONTINUE"
    ASK_SUPPORT = "ASK_SUPPORT"
    ASK_RECENCY = "ASK_RECENCY"
    ASK_PREFERENCE = "ASK_PREFERENCE"
    ASK_NEXT_STEP = "ASK_NEXT_STEP"
    OFFER_OPTIONS = "OFFER_OPTIONS"
    PROVIDE_BRIEF_GUIDANCE = "PROVIDE_BRIEF_GUIDANCE"
    ALLOW_SILENCE = "ALLOW_SILENCE"
    CLARIFY_AUDIO = "CLARIFY_AUDIO"
    HUMAN_HANDOFF = "HUMAN_HANDOFF"
    PAUSE_ADAPTIVE_QUESTIONS = "PAUSE_ADAPTIVE_QUESTIONS"
    END_GRACEFULLY = "END_GRACEFULLY"
    ACKNOWLEDGE = "ACKNOWLEDGE"
    CLARIFY = "CLARIFY"


class AdaptivePriority(str, Enum):
    P0 = "P0"  # Critical / Immediate Safety
    P1 = "P1"  # Elevated Safety / Safety Uncertainty
    P2 = "P2"  # High SVI / Severe Vulnerability
    P3 = "P3"  # Operational Information Gap
    P4 = "P4"  # General Clarification / Support
    P5 = "P5"  # Closure


class AdaptiveReasonCode(str, Enum):
    SAFETY_UNKNOWN = "SAFETY_UNKNOWN"
    SAFETY_REASSESSMENT = "SAFETY_REASSESSMENT"
    CRITICAL_SAFETY_PRIORITY = "CRITICAL_SAFETY_PRIORITY"
    LOCATION_REQUIRED = "LOCATION_REQUIRED"
    SUPPORT_CONTEXT_MISSING = "SUPPORT_CONTEXT_MISSING"
    RECENCY_UNCLEAR = "RECENCY_UNCLEAR"
    CALLER_REQUEST_UNCLEAR = "CALLER_REQUEST_UNCLEAR"
    HIGH_SVI_FOCUS = "HIGH_SVI_FOCUS"
    SVI_RISING = "SVI_RISING"
    ACOUSTIC_LOW_CONFIDENCE = "ACOUSTIC_LOW_CONFIDENCE"
    AUDIO_QUALITY_DEGRADED = "AUDIO_QUALITY_DEGRADED"
    PROLONGED_SILENCE_HANDLING = "PROLONGED_SILENCE_HANDLING"
    CALLER_REQUESTED_HUMAN = "CALLER_REQUESTED_HUMAN"
    OPERATOR_REQUESTED_HUMAN = "OPERATOR_REQUESTED_HUMAN"
    OPERATOR_OVERRIDE_ACTIVE = "OPERATOR_OVERRIDE_ACTIVE"
    REPEATED_AMBIGUITY = "REPEATED_AMBIGUITY"
    CALLER_REFUSAL_HONORED = "CALLER_REFUSAL_HONORED"
    CONTRADICTION_RESOLVED = "CONTRADICTION_RESOLVED"
    CLOSURE_READY = "CLOSURE_READY"
    NORMAL_SUPPORT_FLOW = "NORMAL_SUPPORT_FLOW"


class FactPriority(str, Enum):
    CRITICAL = "CRITICAL"
    IMPORTANT = "IMPORTANT"
    OPTIONAL = "OPTIONAL"


class ConversationFact(BaseModel):
    key: str
    value: Any
    source: str = "caller_statement"
    source_turn_id: Optional[str] = None
    confidence: float = 1.0
    priority: FactPriority = FactPriority.IMPORTANT
    observed_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    superseded: bool = False


class OperatorOverrideAction(str, Enum):
    FORCE_HUMAN = "operator_force_human"
    PAUSE_ADAPTIVE = "operator_pause_adaptive"
    REQUEST_SAFETY_CHECK = "operator_request_safety_check"
    RESUME_ADAPTIVE = "operator_resume_adaptive"
    END_SESSION = "operator_end_session"


class OperatorOverride(BaseModel):
    action: OperatorOverrideAction
    reason: str
    operator_id: str = "operator_counselor_1"
    applied_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    is_active: bool = True


class ConversationPhase(str, Enum):
    OPENING = "OPENING"
    SAFETY_ASSESSMENT = "SAFETY_ASSESSMENT"
    CORE_CONTEXT = "CORE_CONTEXT"
    OPTIONS = "OPTIONS"
    HANDOFF = "HANDOFF"
    CLOSURE = "CLOSURE"


class ConversationStrategy(BaseModel):
    strategy_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    call_id: str
    session_id: str
    turn_index: int = 0
    action: AdaptiveAction
    priority: AdaptivePriority
    target_information: str
    reason_codes: List[AdaptiveReasonCode] = Field(default_factory=list)
    evidence_refs: List[str] = Field(default_factory=list)
    language: str = "en-IN"
    confidence: float = 1.0
    constraints: List[str] = Field(default_factory=list)
    max_attempts: int = 2
    expires_after_turns: int = 2
    requires_human_review: bool = False
    operator_override_active: bool = False
    fallback_applied: bool = False
    disclaimer: str = (
        "Adaptive Conversation is an operational conversational planning layer. It is not a clinical, "
        "medical, diagnostic, legal, credibility, lie-detection, or autonomous emergency-dispatch system."
    )
    engine_version: str = "v1.0.0"
    evaluated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class AdaptivePlanRequest(BaseModel):
    call_id: str = "sim-call-adaptive"
    session_id: str = "sim-sess-adaptive"
    turn_index: int = 1
    language: str = "en-IN"
    safety_state: str = "NONE"
    safety_signals: List[Dict[str, Any]] = Field(default_factory=list)
    svi_score: int = 20
    svi_band: str = "LOW"
    svi_trend: str = "INITIAL"
    acoustic_quality: str = "GOOD"
    acoustic_signals: List[Dict[str, Any]] = Field(default_factory=list)
    known_facts: Dict[str, Any] = Field(default_factory=dict)
    last_caller_utterance: str = ""
    override_action: Optional[str] = None


class AdaptiveStatusResponse(BaseModel):
    status: str = "ready"
    engine_version: str = "v1.0.0"
    is_operational_planning_only: bool = True
    safety_precedence_inviolable: bool = True
    active_policies_count: int = 17
    supported_languages: List[str] = Field(default_factory=lambda: ["ta-IN", "hi-IN", "en-IN"])
    disclaimer: str


class AdaptivePolicyRuleItem(BaseModel):
    condition: str
    strategy: AdaptiveAction
    priority: AdaptivePriority
    primary_reason: AdaptiveReasonCode
    description: str


class AdaptivePolicyResponse(BaseModel):
    engine_version: str = "v1.0.0"
    policy_rules: List[AdaptivePolicyRuleItem]
    total_actions: int
    actions: List[str]


class AdaptiveHistoryResponse(BaseModel):
    call_id: str
    total_strategies: int
    strategies: List[ConversationStrategy]
    active_override: Optional[OperatorOverride] = None
