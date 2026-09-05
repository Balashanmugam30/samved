"""Domain models for SAMVED Phase 14 Scenario Simulation & Operator Training Sandbox."""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
import uuid
from pydantic import BaseModel, Field


class BenchmarkSuiteType(str, Enum):
    SMOKE = "SMOKE"
    FULL = "FULL"
    CUSTOM = "CUSTOM"


class BenchmarkRunStatus(str, Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class NoiseProfile(str, Enum):
    CLEAN = "CLEAN"
    TELEPHONY_8KHZ = "TELEPHONY_8KHZ"
    LOW_SNR_STREET = "LOW_SNR_STREET"
    PACKET_LOSS_BURST = "PACKET_LOSS_BURST"


class DrillDifficulty(str, Enum):
    BEGINNER = "BEGINNER"
    INTERMEDIATE = "INTERMEDIATE"
    ADVANCED = "ADVANCED"
    EXPERT = "EXPERT"


class SyntheticDialogueTurn(BaseModel):
    turn: int
    speaker: str  # "caller" | "agent"
    text: str
    partial: Optional[str] = None
    language: Optional[str] = None
    delay_after_ms: Optional[int] = 500


class SimulationScenario(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    scenario_id: str
    title: str
    description: str
    language: str
    expected_svi_band: str  # "LOW" | "MODERATE" | "HIGH" | "CRITICAL"
    expected_score_range: List[int] = Field(default_factory=lambda: [0, 100])
    expected_safety_triggers: List[str] = Field(default_factory=list)
    prohibited_safety_triggers: List[str] = Field(default_factory=list)
    noise_profile: NoiseProfile = NoiseProfile.CLEAN
    synthetic_dialogue: List[SyntheticDialogueTurn] = Field(default_factory=list)
    expected_rag_citations: List[str] = Field(default_factory=list)
    tags: List[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class TokenAlignmentOp(BaseModel):
    ref_token: str
    hyp_token: str
    op: str  # "match" | "sub" | "del" | "ins"


class WERMetricResult(BaseModel):
    wer: float
    cer: float
    substitutions: int
    deletions: int
    insertions: int
    hits: int
    reference_words: int
    hypothesis_words: int
    reference_chars: int
    hypothesis_chars: int
    normalized_reference: str
    normalized_hypothesis: str
    alignment: Optional[List[TokenAlignmentOp]] = None


class ScenarioEvaluationResult(BaseModel):
    scenario_id: str
    passed: bool
    language: str
    expected_svi_band: str
    actual_svi_band: str
    svi_score: float
    expected_safety_triggers: List[str] = Field(default_factory=list)
    actual_safety_triggers: List[str] = Field(default_factory=list)
    safety_recall: float  # 1.0 (pass) or 0.0 (fail)
    false_negative_hazard: bool = False
    wer_result: Optional[WERMetricResult] = None
    turn_latencies_ms: List[float] = Field(default_factory=list)
    p95_latency_ms: float = 0.0
    error_message: Optional[str] = None


class BenchmarkRun(BaseModel):
    run_id: str = Field(default_factory=lambda: f"RUN-{uuid.uuid4().hex[:8].upper()}")
    suite: BenchmarkSuiteType
    status: BenchmarkRunStatus = BenchmarkRunStatus.PENDING
    started_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: Optional[datetime] = None
    total_scenarios: int = 0
    passed_scenarios: int = 0
    failed_scenarios: int = 0
    pass_rate: float = 0.0
    mean_wer: float = 0.0
    mean_cer: float = 0.0
    safety_recall_rate: float = 1.0
    svi_band_accuracy: float = 1.0
    p95_latency_ms: float = 0.0
    critical_safety_passed: bool = True
    results: List[ScenarioEvaluationResult] = Field(default_factory=list)


class TrainingDrill(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    drill_key: str
    title: str
    category: str
    difficulty: DrillDifficulty
    language: str
    description: str
    scenario_context: str
    expected_competencies: List[str] = Field(default_factory=list)
    turns: List[SyntheticDialogueTurn] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class TrainingTurnEvaluation(BaseModel):
    turn_number: int
    trainee_input: str
    score: float  # 0-100
    safety_protocol_score: float  # 0-35
    empathy_score: float  # 0-25
    de_escalation_score: float  # 0-20
    statutory_referral_score: float  # 0-20
    feedback_hints: List[str] = Field(default_factory=list)
    caller_next_turn: Optional[str] = None


class TrainingSession(BaseModel):
    session_id: str = Field(default_factory=lambda: f"TRN-{uuid.uuid4().hex[:8].upper()}")
    drill_id: str
    trainee_id: str
    trainee_name: str = "Counselor Trainee"
    status: str = "ACTIVE"
    started_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: Optional[datetime] = None
    current_turn: int = 1
    total_turns: int = 2
    overall_score: Optional[float] = None
    performance_rating: Optional[str] = None
    competency_breakdown: Dict[str, float] = Field(default_factory=dict)
    recommendations: List[str] = Field(default_factory=list)
    evaluated_turns: List[TrainingTurnEvaluation] = Field(default_factory=list)
