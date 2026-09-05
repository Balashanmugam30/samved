import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Union
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

    # Legal / Policy Knowledge RAG (Phase 10)
    KNOWLEDGE_SEARCH_STARTED = "KNOWLEDGE_SEARCH_STARTED"
    KNOWLEDGE_SEARCH_COMPLETED = "KNOWLEDGE_SEARCH_COMPLETED"
    KNOWLEDGE_SEARCH_FAILED = "KNOWLEDGE_SEARCH_FAILED"
    KNOWLEDGE_SOURCE_SELECTED = "KNOWLEDGE_SOURCE_SELECTED"
    KNOWLEDGE_SOURCE_CONFLICT = "KNOWLEDGE_SOURCE_CONFLICT"
    KNOWLEDGE_REVIEW_RECOMMENDED = "KNOWLEDGE_REVIEW_RECOMMENDED"
    KNOWLEDGE_ANSWER_BLOCKED = "KNOWLEDGE_ANSWER_BLOCKED"

    # Case Intelligence & Knowledge Graph (Phase 11)
    CASE_CREATED = "CASE_CREATED"
    CASE_UPDATED = "CASE_UPDATED"
    CASE_CALL_LINKED = "CASE_CALL_LINKED"
    CASE_CALL_UNLINKED = "CASE_CALL_UNLINKED"
    CASE_ENTITY_CREATED = "CASE_ENTITY_CREATED"
    CASE_ENTITY_UPDATED = "CASE_ENTITY_UPDATED"
    CASE_ENTITY_CANDIDATE_CREATED = "CASE_ENTITY_CANDIDATE_CREATED"
    CASE_RELATIONSHIP_CREATED = "CASE_RELATIONSHIP_CREATED"
    CASE_RELATIONSHIP_CONFIRMED = "CASE_RELATIONSHIP_CONFIRMED"
    CASE_RELATIONSHIP_REJECTED = "CASE_RELATIONSHIP_REJECTED"
    CASE_RELATIONSHIP_SUPERSEDED = "CASE_RELATIONSHIP_SUPERSEDED"
    CASE_NOTE_LINKED = "CASE_NOTE_LINKED"
    FOLLOWUP_SCHEDULED = "FOLLOWUP_SCHEDULED"

    # Follow-up Workflow & Continuity Engine (Phase 12)
    FOLLOWUP_CREATED = "FOLLOWUP_CREATED"
    FOLLOWUP_APPROVAL_REQUESTED = "FOLLOWUP_APPROVAL_REQUESTED"
    FOLLOWUP_APPROVED = "FOLLOWUP_APPROVED"
    FOLLOWUP_READY = "FOLLOWUP_READY"
    FOLLOWUP_STARTED = "FOLLOWUP_STARTED"
    FOLLOWUP_COMPLETED = "FOLLOWUP_COMPLETED"
    FOLLOWUP_RESCHEDULED = "FOLLOWUP_RESCHEDULED"
    FOLLOWUP_CANCELLED = "FOLLOWUP_CANCELLED"
    FOLLOWUP_BLOCKED = "FOLLOWUP_BLOCKED"
    FOLLOWUP_MISSED = "FOLLOWUP_MISSED"
    FOLLOWUP_EXPIRED = "FOLLOWUP_EXPIRED"
    FOLLOWUP_CONSENT_REVOKED = "FOLLOWUP_CONSENT_REVOKED"
    FOLLOWUP_ATTEMPT_RECORDED = "FOLLOWUP_ATTEMPT_RECORDED"
    FOLLOWUP_OUTCOME_RECORDED = "FOLLOWUP_OUTCOME_RECORDED"

    # District Intelligence & Operational Analytics (Phase 13)
    ANALYTICS_SUMMARY_UPDATED = "ANALYTICS_SUMMARY_UPDATED"
    ANALYTICS_JOB_STARTED = "ANALYTICS_JOB_STARTED"
    ANALYTICS_JOB_COMPLETED = "ANALYTICS_JOB_COMPLETED"
    ANALYTICS_JOB_FAILED = "ANALYTICS_JOB_FAILED"

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


# ==========================================
# Phase 10: Legal / Policy Knowledge RAG Models
# ==========================================

class AuthorityTier(int, Enum):
    TIER_1 = 1  # Official GoI / State Official Sources, Statutory Gazettes
    TIER_2 = 2  # Official Courts, Tribunals, Statutory Commissions
    TIER_3 = 3  # Approved Institutional Partners & Shelters
    TIER_4 = 4  # Secondary References & Operational SOPs


class DocumentStatus(str, Enum):
    DISCOVERED = "DISCOVERED"
    INGESTED = "INGESTED"
    PARSED = "PARSED"
    VALIDATED = "VALIDATED"
    INDEXED = "INDEXED"
    ACTIVE = "ACTIVE"
    SUPERSEDED = "SUPERSEDED"
    RETIRED = "RETIRED"
    REJECTED = "REJECTED"


class FreshnessStatus(str, Enum):
    CURRENT = "CURRENT"
    STALE = "STALE"
    EXPIRED = "EXPIRED"
    UNKNOWN = "UNKNOWN"


class KnowledgeJurisdiction(str, Enum):
    INDIA = "INDIA"
    TAMIL_NADU = "TAMIL_NADU"
    CENTRAL_GOVERNMENT = "CENTRAL_GOVERNMENT"
    JURISDICTION_UNCERTAIN = "JURISDICTION_UNCERTAIN"


class CitationMetadata(BaseModel):
    citation_id: str
    document_id: str
    document_title: str
    publisher: str
    version: str
    section_page: str
    effective_date: str
    source_url: str
    retrieved_at: str
    excerpt: str
    authority_tier: int
    jurisdiction: str


class KnowledgeItemPayload(BaseModel):
    document_id: str
    version: str
    title: str
    publisher: str
    jurisdiction: str
    source_url: str
    chunk_id: str
    excerpt: str
    relevance: float
    authority_tier: int
    effective_status: str
    source_date: str
    retrieved_at: str
    citation: CitationMetadata


class KnowledgeQueryPayload(BaseModel):
    query: str
    language: Optional[str] = None
    jurisdiction: Optional[str] = None
    topic: Optional[str] = None
    source_tiers: Optional[List[int]] = None
    as_of_date: Optional[str] = None
    effective_only: bool = True
    max_results: int = 5


class KnowledgeResultPayload(BaseModel):
    query_id: str
    call_id: Optional[str] = None
    query: str
    status: str
    total_found: int
    results: List[KnowledgeItemPayload] = Field(default_factory=list)
    citations: List[CitationMetadata] = Field(default_factory=list)
    ai_summary: Optional[str] = None
    requires_human_review: bool = False
    review_reasons: List[str] = Field(default_factory=list)
    conflict_detected: bool = False
    conflicting_sources: List[Dict[str, Any]] = Field(default_factory=list)
    search_latency_ms: float = 0.0
    executed_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


# ==========================================
# Phase 11: Case Intelligence & Knowledge Graph Contracts
# ==========================================

class CaseStatus(str, Enum):
    OPEN = "OPEN"
    ACTIVE = "ACTIVE"
    INTAKE = "INTAKE"
    TRIAGED = "TRIAGED"
    ESCALATED = "ESCALATED"
    ON_HOLD = "ON_HOLD"
    FOLLOW_UP_PENDING = "FOLLOW_UP_PENDING"
    RESOLVED = "RESOLVED"
    CLOSED = "CLOSED"
    ARCHIVED = "ARCHIVED"
    UNKNOWN = "UNKNOWN"


class EntityType(str, Enum):
    CASE = "CASE"
    CALL = "CALL"
    PERSON = "PERSON"
    OPERATOR = "OPERATOR"
    ORGANIZATION = "ORGANIZATION"
    SERVICE = "SERVICE"
    LOCATION = "LOCATION"
    EVENT = "EVENT"
    DOCUMENT = "DOCUMENT"
    KNOWLEDGE_SOURCE = "KNOWLEDGE_SOURCE"
    NOTE = "NOTE"
    INTERVENTION = "INTERVENTION"
    CONTACT_POINT = "CONTACT_POINT"
    FOLLOW_UP = "FOLLOW_UP"


class PersonRole(str, Enum):
    CALLER = "CALLER"
    HOUSEHOLD_MEMBER = "HOUSEHOLD_MEMBER"
    CONTACT = "CONTACT"
    SUPPORT_PERSON = "SUPPORT_PERSON"
    REPORTED_ACTOR = "REPORTED_ACTOR"
    SERVICE_PROVIDER = "SERVICE_PROVIDER"
    OPERATOR = "OPERATOR"
    UNKNOWN_PERSON = "UNKNOWN_PERSON"


class ClaimStatus(str, Enum):
    REPORTED = "REPORTED"
    OBSERVED = "OBSERVED"
    VERIFIED = "VERIFIED"
    INFERRED = "INFERRED"
    UNKNOWN = "UNKNOWN"
    DISPUTED = "DISPUTED"


class RelationshipType(str, Enum):
    REPORTED_BY = "REPORTED_BY"
    MENTIONED_IN = "MENTIONED_IN"
    CONNECTED_TO = "CONNECTED_TO"
    LOCATED_AT = "LOCATED_AT"
    LIVES_AT = "LIVES_AT"
    WORKS_AT = "WORKS_AT"
    SUPPORTS = "SUPPORTS"
    REFERRED_TO = "REFERRED_TO"
    CONTACTED = "CONTACTED"
    CALLED = "CALLED"
    PART_OF_CASE = "PART_OF_CASE"
    DESCRIBES = "DESCRIBES"
    DOCUMENTED_BY = "DOCUMENTED_BY"
    CITED_BY = "CITED_BY"
    OCCURRED_AT = "OCCURRED_AT"
    INVOLVES = "INVOLVES"
    HAS_FOLLOW_UP = "HAS_FOLLOW_UP"
    BASED_ON = "BASED_ON"


class CaseEvidenceLinkPayload(BaseModel):
    link_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    source_type: str = "CALL_TRANSCRIPT"
    source_id: str
    turn_index: Optional[int] = None
    verbatim_excerpt: Optional[str] = None
    citation_ref: Optional[str] = None
    content_hash: Optional[str] = None
    confidence: float = 1.0


class CaseGraphNodePayload(BaseModel):
    entity_id: str
    case_id: str
    type: EntityType
    role: Optional[Union[PersonRole, str]] = None
    label: str
    claim_status: ClaimStatus = ClaimStatus.REPORTED
    confidence: float = 1.0
    source_refs: List[str] = Field(default_factory=list)
    evidence: List[CaseEvidenceLinkPayload] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    first_seen: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    last_seen: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class CaseGraphEdgePayload(BaseModel):
    edge_id: str
    case_id: str
    source_entity: str
    relationship_type: RelationshipType
    target_entity: str
    claim_status: ClaimStatus = ClaimStatus.REPORTED
    confidence: float = 1.0
    source_refs: List[str] = Field(default_factory=list)
    evidence: List[CaseEvidenceLinkPayload] = Field(default_factory=list)
    valid_from: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    valid_to: Optional[str] = None
    observed_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    superseded_at: Optional[str] = None
    superseded_by: Optional[str] = None
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class CaseCandidatePayload(BaseModel):
    candidate_id: str
    case_id: str
    source_entity: str
    source_label: str
    relationship_type: RelationshipType
    target_entity: str
    target_label: str
    confidence: float = 1.0
    evidence_excerpt: str
    source_turn: Optional[str] = None
    status: str = "PENDING"
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class CaseTimelineItemPayload(BaseModel):
    event_id: str
    case_id: str
    event_type: str
    title: str
    summary: str
    severity: Optional[str] = None
    actor_id: Optional[str] = None
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    evidence_refs: List[str] = Field(default_factory=list)
    claim_status: ClaimStatus = ClaimStatus.REPORTED


class CaseSummaryPayload(BaseModel):
    case_id: str
    case_number: str
    status: CaseStatus
    created_at: str
    updated_at: str
    primary_language: str = "en-IN"
    linked_calls_count: int = 0
    linked_calls: List[str] = Field(default_factory=list)
    entities_count: int = 0
    relationships_count: int = 0
    events_count: int = 0
    pending_candidates_count: int = 0
    svi_score: Optional[int] = None
    svi_band: Optional[str] = None
    safety_state: Optional[str] = None


class CaseGraphPayload(BaseModel):
    case_id: str
    nodes: List[CaseGraphNodePayload] = Field(default_factory=list)
    edges: List[CaseGraphEdgePayload] = Field(default_factory=list)
    candidates: List[CaseCandidatePayload] = Field(default_factory=list)
    total_nodes: int = 0
    total_edges: int = 0


# ============================================================================
# Phase 12 — Follow-up Workflow & Continuity Engine Models
# ============================================================================

class FollowupType(str, Enum):
    CHECK_IN = "CHECK_IN"
    HUMAN_CALLBACK = "HUMAN_CALLBACK"
    RESOURCE_FOLLOW_UP = "RESOURCE_FOLLOW_UP"
    CASE_REVIEW = "CASE_REVIEW"
    DOCUMENT_FOLLOW_UP = "DOCUMENT_FOLLOW_UP"
    HANDOFF_FOLLOW_UP = "HANDOFF_FOLLOW_UP"
    OPERATOR_REVIEW = "OPERATOR_REVIEW"


class FollowupStatus(str, Enum):
    DRAFT = "DRAFT"
    PENDING_APPROVAL = "PENDING_APPROVAL"
    SCHEDULED = "SCHEDULED"
    READY = "READY"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"
    EXPIRED = "EXPIRED"
    MISSED = "MISSED"
    BLOCKED = "BLOCKED"


class ConsentState(str, Enum):
    UNKNOWN = "UNKNOWN"
    REQUESTED = "REQUESTED"
    GRANTED = "GRANTED"
    LIMITED = "LIMITED"
    REFUSED = "REFUSED"
    REVOKED = "REVOKED"
    NOT_APPLICABLE = "NOT_APPLICABLE"


class FollowupPriority(str, Enum):
    LOW = "LOW"
    NORMAL = "NORMAL"
    HIGH = "HIGH"
    CRITICAL_REVIEW = "CRITICAL_REVIEW"


class ContactChannel(str, Enum):
    INTERNAL_TASK = "INTERNAL_TASK"
    OPERATOR_CALLBACK = "OPERATOR_CALLBACK"
    PHONE = "PHONE"
    SMS = "SMS"
    EMAIL = "EMAIL"


class ContactResult(str, Enum):
    CONTACTED_SUCCESSFULLY = "CONTACTED_SUCCESSFULLY"
    NO_ANSWER = "NO_ANSWER"
    CALLER_DECLINED = "CALLER_DECLINED"
    WRONG_CONTACT = "WRONG_CONTACT"
    RESCHEDULED = "RESCHEDULED"
    REFERRED = "REFERRED"
    UNRESOLVED = "UNRESOLVED"


class FollowupOutcome(str, Enum):
    CONTACTED_SUCCESSFULLY = "CONTACTED_SUCCESSFULLY"
    NO_ANSWER = "NO_ANSWER"
    CALLER_DECLINED = "CALLER_DECLINED"
    WRONG_CONTACT = "WRONG_CONTACT"
    RESCHEDULED = "RESCHEDULED"
    REFERRED = "REFERRED"
    UNRESOLVED = "UNRESOLVED"


class RecurrenceRule(str, Enum):
    ONCE = "ONCE"
    DAILY = "DAILY"
    WEEKLY = "WEEKLY"
    CUSTOM_BOUNDED = "CUSTOM_BOUNDED"


class ContactPreferencesPayload(BaseModel):
    preferred_channel: Union[ContactChannel, str] = ContactChannel.OPERATOR_CALLBACK
    preferred_time_window: Optional[str] = None
    days_allowed: List[str] = Field(default_factory=list)
    safe_to_contact: bool = True
    preferred_language: Optional[str] = "en-IN"
    human_only: bool = True
    no_voicemail: bool = False
    no_text: bool = False
    timezone: Optional[str] = "Asia/Kolkata"


class FollowupAttemptPayload(BaseModel):
    attempt_number: int
    attempted_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    operator_id: str
    channel: Union[ContactChannel, str]
    result: Union[ContactResult, str]
    notes: Optional[str] = None


class FollowupPayload(BaseModel):
    followup_id: str
    case_id: str
    call_id: Optional[str] = None
    created_by: str
    assigned_to: Optional[str] = None
    type: FollowupType
    status: FollowupStatus
    priority: FollowupPriority
    requested_at: str
    scheduled_for: str
    due_at: str
    completed_at: Optional[str] = None
    cancelled_at: Optional[str] = None
    consent_state: ConsentState
    contact_preferences: ContactPreferencesPayload
    safe_contact_window: Optional[str] = None
    channel: ContactChannel
    purpose: str
    notes_ref: Optional[str] = None
    citation_ref: Optional[str] = None
    source_event: Optional[str] = None
    last_attempt_at: Optional[str] = None
    attempt_count: int = 0
    max_attempts: int = 2
    outcome: Optional[FollowupOutcome] = None
    policy_version: str = "v1.0"
    blocked_reason: Optional[str] = None
    created_at: str
    updated_at: str


class FollowupEventPayload(BaseModel):
    followup_id: str
    case_id: str
    call_id: Optional[str] = None
    status: FollowupStatus
    previous_status: Optional[FollowupStatus] = None
    actor_id: str
    purpose: str
    priority: FollowupPriority
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    reason_codes: List[str] = Field(default_factory=list)
    outcome: Optional[FollowupOutcome] = None
    details: Dict[str, Any] = Field(default_factory=dict)


class FollowupWorkqueueSummaryPayload(BaseModel):
    total_active: int = 0
    due_today: int = 0
    overdue: int = 0
    blocked: int = 0
    completed_today: int = 0


# -------------------------------------------------------------------------
# Phase 13: District Intelligence & Operational Analytics Contracts
# -------------------------------------------------------------------------

class MetricStatus(str, Enum):
    OBSERVED = "OBSERVED"
    CALCULATED = "CALCULATED"
    ESTIMATED = "ESTIMATED"
    SUPPRESSED = "SUPPRESSED"
    UNAVAILABLE = "UNAVAILABLE"


class TrendDirection(str, Enum):
    RISING = "RISING"
    FALLING = "FALLING"
    STABLE = "STABLE"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"


class DataQualityStatus(str, Enum):
    HEALTHY = "HEALTHY"
    DEGRADED = "DEGRADED"
    INCOMPLETE = "INCOMPLETE"


class AnalyticsRole(str, Enum):
    OPERATOR = "OPERATOR"
    SUPERVISOR = "SUPERVISOR"
    DISTRICT_ADMIN = "DISTRICT_ADMIN"
    SYSTEM_ADMIN = "SYSTEM_ADMIN"


class ServiceCategory(str, Enum):
    SAFETY_SUPPORT = "SAFETY_SUPPORT"
    COUNSELING_REFERRAL = "COUNSELING_REFERRAL"
    LEGAL_INFORMATION = "LEGAL_INFORMATION"
    SHELTER_SUPPORT = "SHELTER_SUPPORT"
    HEALTH_SUPPORT = "HEALTH_SUPPORT"
    FOLLOW_UP = "FOLLOW_UP"
    GENERAL_INFORMATION = "GENERAL_INFORMATION"
    OTHER = "OTHER"


class TimePeriod(str, Enum):
    HOUR = "HOUR"
    DAY = "DAY"
    WEEK = "WEEK"
    MONTH = "MONTH"
    QUARTER = "QUARTER"


class MetricDefinitionPayload(BaseModel):
    metric_id: str
    metric_version: str = "v1.0.0"
    name: str
    category: str
    definition: str
    calculation_method: str
    status: MetricStatus
    privacy_level: str = "AGGREGATE"
    source_event_types: List[str] = Field(default_factory=list)


class MetricItemPayload(BaseModel):
    metric_id: str
    metric_version: str = "v1.0.0"
    display_value: str
    raw_value: Optional[float] = None
    unit: Optional[str] = None
    status: MetricStatus
    suppressed: bool = False
    trend: Optional[TrendDirection] = None
    trend_pct: Optional[float] = None
    period_start: str
    period_end: str


class DistrictSummaryPayload(BaseModel):
    district_code: str
    district_name: str
    state_code: str
    state_name: str
    period: TimePeriod
    period_start: str
    period_end: str
    timezone: str = "Asia/Kolkata"
    total_calls: MetricItemPayload
    completed_calls: MetricItemPayload
    abandoned_calls: MetricItemPayload
    unique_cases: MetricItemPayload
    active_followups: MetricItemPayload
    avg_response_time_sec: MetricItemPayload
    safety_escalations_count: MetricItemPayload
    privacy_status: str = "PASS"
    data_quality_status: DataQualityStatus = DataQualityStatus.HEALTHY
    computed_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    metric_version: str = "v1.0.0"


class LanguageDistributionItem(BaseModel):
    language: str
    language_name: str
    percentage: float
    count_display: str
    suppressed: bool = False


class ServiceDemandItem(BaseModel):
    category: ServiceCategory
    category_name: str
    percentage: float
    count_display: str
    suppressed: bool = False


class SafetyDistributionItem(BaseModel):
    safety_state: str
    percentage: float
    count_display: str
    suppressed: bool = False


class SviDistributionItem(BaseModel):
    band: str
    percentage: float
    count_display: str
    suppressed: bool = False


class FollowupAnalyticsPayload(BaseModel):
    district_code: str
    period_start: str
    period_end: str
    created_count: MetricItemPayload
    completed_count: MetricItemPayload
    missed_count: MetricItemPayload
    blocked_count: MetricItemPayload
    completion_rate: MetricItemPayload
    missed_rate: MetricItemPayload
    suppressed: bool = False


class OperatorWorkloadPayload(BaseModel):
    district_code: str
    period_start: str
    period_end: str
    active_operators_count: MetricItemPayload
    avg_calls_per_operator: MetricItemPayload
    takeovers_count: MetricItemPayload
    handoffs_requested: MetricItemPayload
    handoffs_confirmed: MetricItemPayload
    median_response_time_sec: MetricItemPayload
    suppressed: bool = False


class KnowledgeCategoryItem(BaseModel):
    category: str
    count_display: str
    percentage: float
    suppressed: bool = False


class KnowledgeAnalyticsPayload(BaseModel):
    district_code: str
    total_queries: MetricItemPayload
    no_source_rate: MetricItemPayload
    conflict_rate: MetricItemPayload
    review_recommended_rate: MetricItemPayload
    top_categories: List[KnowledgeCategoryItem] = Field(default_factory=list)


class SystemHealthPayload(BaseModel):
    api_latency_p95_ms: MetricItemPayload
    stt_failure_rate: MetricItemPayload
    tts_failure_rate: MetricItemPayload
    orchestration_timeout_rate: MetricItemPayload
    websocket_reconnect_rate: MetricItemPayload


class AnalyticsQueryPayload(BaseModel):
    state_code: Optional[str] = None
    district_code: Optional[str] = None
    period: TimePeriod = TimePeriod.DAY
    start_date: str
    end_date: str
    language: Optional[str] = None
    service_category: Optional[ServiceCategory] = None
    role: AnalyticsRole = AnalyticsRole.DISTRICT_ADMIN


class AnalyticsJobPayload(BaseModel):
    job_id: str
    period: str
    started_at: str
    completed_at: Optional[str] = None
    status: str = "RUNNING"
    source_event_count: int = 0
    processed_count: int = 0
    suppressed_count: int = 0
    error_count: int = 0
