"""Data models and enums for SAMVED Phase 9 Multi-Agent Orchestration."""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
import uuid
from pydantic import BaseModel, Field


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
    REALTIME_CRITICAL = "REALTIME_CRITICAL"  # <= 50ms
    REALTIME_NORMAL = "REALTIME_NORMAL"      # <= 200ms
    BACKGROUND = "BACKGROUND"                # <= 1000ms


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


class AgentSpec(BaseModel):
    name: str
    version: str = "1.0.0"
    agent_type: AgentType
    capabilities: List[str] = Field(default_factory=list)
    timeout_tier: AgentTimeoutTier = AgentTimeoutTier.REALTIME_NORMAL
    max_latency_ms: int = 200
    safety_classification: AgentSafetyClassification = AgentSafetyClassification.OPERATIONAL
    requires_human_review: bool = False
    is_realtime_capable: bool = True
    enabled: bool = True


class AgentRequest(BaseModel):
    request_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    call_id: str
    turn_id: str
    task_type: str
    language: str = "ta-IN"
    deadline_ms: int = Field(default=0)  # Epoch timestamp ms or timeout ms
    relevant_context: Dict[str, Any] = Field(default_factory=dict)
    constraints: List[str] = Field(default_factory=list)


class AgentResponse(BaseModel):
    request_id: str
    call_id: str
    turn_id: str
    agent_name: str
    agent_version: str = "1.0.0"
    status: AgentStatus = AgentStatus.SUCCESS
    result: Dict[str, Any] = Field(default_factory=dict)
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    evidence_refs: List[str] = Field(default_factory=list)
    latency_ms: float = 0.0
    warnings: List[str] = Field(default_factory=list)
    produced_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


class ValidatedContext(BaseModel):
    facts: Dict[str, Any] = Field(default_factory=dict)
    unresolved_gaps: List[str] = Field(default_factory=list)
    contradictions: List[Dict[str, Any]] = Field(default_factory=list)
    language_info: Dict[str, Any] = Field(default_factory=dict)
    safety_info: Dict[str, Any] = Field(default_factory=dict)
    acoustic_info: Dict[str, Any] = Field(default_factory=dict)
    support_info: Dict[str, Any] = Field(default_factory=dict)
    evidence_refs: List[str] = Field(default_factory=list)
    conflict_resolutions: List[str] = Field(default_factory=list)


class OperatorBriefing(BaseModel):
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


class OrchestrationResult(BaseModel):
    request_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    call_id: str
    turn_id: str
    state: OrchestrationState = OrchestrationState.COMPLETED
    selected_agents: List[str] = Field(default_factory=list)
    completed_agents: List[str] = Field(default_factory=list)
    failed_agents: List[str] = Field(default_factory=list)
    timed_out_agents: List[str] = Field(default_factory=list)
    cancelled_agents: List[str] = Field(default_factory=list)
    briefing: Optional[OperatorBriefing] = None
    validated_context: Optional[ValidatedContext] = None
    agent_outputs: Dict[str, AgentResponse] = Field(default_factory=dict)
    total_latency_ms: float = 0.0
    warnings: List[str] = Field(default_factory=list)
    completed_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


class OrchestrationStatusResponse(BaseModel):
    status: str = "healthy"
    engine_version: str = "1.0.0"
    registered_agents_count: int = 0
    active_capabilities: List[str] = Field(default_factory=list)
    human_supervision_active: bool = True
    deterministic_safety_authoritative: bool = True
