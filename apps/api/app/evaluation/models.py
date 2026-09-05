"""
SAMVED Phase 14: Scenario Simulator & Evaluation Lab Domain Models
Typed, versioned models for scenarios, assertions, golden expectations, metrics, baselines, and diffs.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class EvaluationMode(str, Enum):
    OFFLINE = "OFFLINE"
    INTEGRATED = "INTEGRATED"


class FindingSeverity(str, Enum):
    PASS = "PASS"
    INFO = "INFO"
    WARNING = "WARNING"
    FAIL = "FAIL"
    BLOCKED = "BLOCKED"


class EvaluationStatus(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    WARNING = "WARNING"
    BLOCKED = "BLOCKED"


class FaultType(str, Enum):
    NONE = "NONE"
    STT_UNAVAILABLE = "STT_UNAVAILABLE"
    TTS_UNAVAILABLE = "TTS_UNAVAILABLE"
    ORCHESTRATION_TIMEOUT = "ORCHESTRATION_TIMEOUT"
    KNOWLEDGE_TIMEOUT = "KNOWLEDGE_TIMEOUT"
    STALE_AGENT_RESULT = "STALE_AGENT_RESULT"
    MALFORMED_EVENT = "MALFORMED_EVENT"
    DUPLICATE_EVENT = "DUPLICATE_EVENT"
    OUT_OF_ORDER_EVENT = "OUT_OF_ORDER_EVENT"
    PARTIAL_STAGE_FAILURE = "PARTIAL_STAGE_FAILURE"
    OPERATOR_DISCONNECT = "OPERATOR_DISCONNECT"


class CallerProfile(BaseModel):
    caller_id: str = "SYNTHETIC-CALLER-01"
    age_group: Optional[str] = None
    gender: Optional[str] = None
    location_hint: Optional[str] = None
    dialect_notes: Optional[str] = None
    prior_contact_history: bool = False


class ScenarioTurn(BaseModel):
    turn_number: int
    speaker: str = "caller"
    text: str
    transcription_hypothesis: Optional[str] = None
    acoustic_features: Dict[str, Any] = Field(default_factory=dict)
    injected_fault: FaultType = FaultType.NONE


class GoldenExpectations(BaseModel):
    expected_safety_state: Optional[str] = None
    expected_safety_minimum: Optional[str] = None
    expected_svi_band: Optional[str] = None
    expected_svi_score_range: Optional[List[int]] = None
    expected_required_human_review: Optional[bool] = None
    expected_language: Optional[str] = None
    expected_event_types: List[str] = Field(default_factory=list)
    expected_adaptive_policy: Optional[str] = None
    expected_handoff_state: Optional[str] = None
    expected_followup_state: Optional[str] = None
    expected_knowledge_citations: List[str] = Field(default_factory=list)
    forbidden_event_types: List[str] = Field(default_factory=list)
    forbidden_actions: List[str] = Field(default_factory=list)
    max_p95_latency_ms: Optional[float] = 1200.0


class EvaluationAssertion(BaseModel):
    assertion_id: str
    category: str
    description: str
    passed: bool
    expected: Any = None
    actual: Any = None
    message: Optional[str] = None


class EvaluationFinding(BaseModel):
    finding_id: str = Field(default_factory=lambda: f"FND-{uuid.uuid4().hex[:8]}")
    scenario_id: str
    subsystem: str
    severity: FindingSeverity
    message: str
    details: Dict[str, Any] = Field(default_factory=dict)
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class LatencyMetrics(BaseModel):
    total_ms: float = 0.0
    p95_ms: float = 0.0
    min_ms: float = 0.0
    median_ms: float = 0.0
    max_ms: float = 0.0
    stage_breakdown: Dict[str, float] = Field(default_factory=dict)


class SubsystemMetrics(BaseModel):
    safety: Dict[str, Any] = Field(default_factory=dict)
    svi: Dict[str, Any] = Field(default_factory=dict)
    adaptive: Dict[str, Any] = Field(default_factory=dict)
    acoustic: Dict[str, Any] = Field(default_factory=dict)
    orchestration: Dict[str, Any] = Field(default_factory=dict)
    rag: Dict[str, Any] = Field(default_factory=dict)
    case_intelligence: Dict[str, Any] = Field(default_factory=dict)
    followup: Dict[str, Any] = Field(default_factory=dict)
    analytics_isolation: Dict[str, Any] = Field(default_factory=dict)
    latency: LatencyMetrics = Field(default_factory=LatencyMetrics)


class ScenarioDefinition(BaseModel):
    scenario_id: str
    scenario_version: str = "1.0"
    title: str
    description: str
    locale: str = "en-IN"
    channel: str = "PSTN_8KHZ"
    difficulty: str = "BEGINNER"
    tags: List[str] = Field(default_factory=list)
    synthetic_disclaimer: str = (
        "SYNTHETIC BENCHMARK ISOLATION: All scenarios and caller entities are purely synthetic. "
        "No live records or active carrier connections are used."
    )
    caller_profile: CallerProfile = Field(default_factory=CallerProfile)
    turns: List[ScenarioTurn] = Field(default_factory=list)
    expected: GoldenExpectations = Field(default_factory=GoldenExpectations)
    fault_injection: FaultType = FaultType.NONE


class BaselineSnapshot(BaseModel):
    baseline_id: str = Field(default_factory=lambda: f"BASE-{uuid.uuid4().hex[:8]}")
    scenario_id: str
    scenario_version: str = "1.0"
    evaluation_version: str = "1.0"
    seed: int = 42
    status: EvaluationStatus = EvaluationStatus.PASS
    metrics: SubsystemMetrics = Field(default_factory=SubsystemMetrics)
    captured_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class RunDiffItem(BaseModel):
    field: str
    subsystem: str
    baseline_value: Any = None
    current_value: Any = None
    is_regression: bool = False
    message: str


class RunDiffResult(BaseModel):
    baseline_id: str
    current_run_id: str
    scenario_id: str
    status: str = "IDENTICAL"  # IDENTICAL, IMPROVED, REGRESSED, CHANGED
    has_regression: bool = False
    differences: List[RunDiffItem] = Field(default_factory=list)


class EvaluationRunRecord(BaseModel):
    run_id: str = Field(default_factory=lambda: f"RUN-EVAL-{uuid.uuid4().hex[:8]}")
    scenario_id: str
    scenario_version: str = "1.0"
    suite_id: Optional[str] = None
    mode: EvaluationMode = EvaluationMode.OFFLINE
    seed: int = 42
    execution_status: str = "COMPLETED"
    evaluation_status: EvaluationStatus = EvaluationStatus.PASS
    started_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    completed_at: Optional[str] = None
    duration_ms: float = 0.0
    synthetic_marker: str = "SYNTHETIC_EVALUATION"
    assertions: List[EvaluationAssertion] = Field(default_factory=list)
    findings: List[EvaluationFinding] = Field(default_factory=list)
    metrics: SubsystemMetrics = Field(default_factory=SubsystemMetrics)
    events_count: int = 0
    baseline_diff: Optional[RunDiffResult] = None
