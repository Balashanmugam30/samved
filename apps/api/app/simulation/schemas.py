"""REST API request and response schemas for SAMVED Phase 14 Simulation & Training."""

from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from app.simulation.models import (
    BenchmarkRunStatus,
    BenchmarkSuiteType,
    DrillDifficulty,
    NoiseProfile,
    ScenarioEvaluationResult,
    TokenAlignmentOp,
    WERMetricResult,
)


class BenchmarkRunRequest(BaseModel):
    suite: BenchmarkSuiteType = BenchmarkSuiteType.SMOKE


class ScenarioItemResponse(BaseModel):
    scenario_id: str
    title: str
    description: str
    language: str
    expected_svi_band: str
    expected_score_range: List[int]
    expected_safety_triggers: List[str]
    prohibited_safety_triggers: List[str]
    noise_profile: NoiseProfile
    turns_count: int
    tags: List[str]


class BenchmarkRunResponse(BaseModel):
    run_id: str
    suite: BenchmarkSuiteType
    status: BenchmarkRunStatus
    started_at: str
    completed_at: Optional[str] = None
    total_scenarios: int
    passed_scenarios: int
    failed_scenarios: int
    pass_rate: float
    mean_wer: float
    mean_cer: float
    safety_recall_rate: float
    svi_band_accuracy: float
    p95_latency_ms: float
    critical_safety_passed: bool
    results: List[ScenarioEvaluationResult] = Field(default_factory=list)


class WERCalculateRequest(BaseModel):
    reference: str
    hypothesis: str


class TrainingDrillItemResponse(BaseModel):
    id: str
    drill_key: str
    title: str
    category: str
    difficulty: DrillDifficulty
    language: str
    description: str
    scenario_context: str
    expected_competencies: List[str]
    turns_count: int


class TrainingSessionStartRequest(BaseModel):
    drill_key: str
    trainee_id: Optional[str] = "T-1001"
    trainee_name: Optional[str] = "Counselor Trainee"


class TrainingTurnSubmitRequest(BaseModel):
    trainee_input: str


class TrainingTurnResponse(BaseModel):
    turn_number: int
    trainee_input: str
    score: float
    safety_protocol_score: float
    empathy_score: float
    de_escalation_score: float
    statutory_referral_score: float
    feedback_hints: List[str]
    caller_next_turn: Optional[str] = None


class TrainingSessionResponse(BaseModel):
    session_id: str
    drill_id: str
    trainee_id: str
    trainee_name: str
    status: str
    started_at: str
    completed_at: Optional[str] = None
    current_turn: int
    total_turns: int
    overall_score: Optional[float] = None
    performance_rating: Optional[str] = None
    competency_breakdown: Dict[str, float] = Field(default_factory=dict)
    recommendations: List[str] = Field(default_factory=list)
    evaluated_turns: List[TrainingTurnResponse] = Field(default_factory=list)


class SimulationStatusResponse(BaseModel):
    status: str = "healthy"
    version: str = "v1.0.0"
    total_scenarios: int
    total_drills: int
    languages_supported: List[str]
    recent_benchmark_runs: int
