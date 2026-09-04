import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class SVIBand(str, Enum):
    LOW = "LOW"             # 0–25: Routine support, informational
    MODERATE = "MODERATE"   # 26–50: Non-lethal difficulties, moderate distress
    HIGH = "HIGH"           # 51–75: Severe distress, coercion, significant barriers
    CRITICAL = "CRITICAL"    # 76–100: Active violence, lethal weapons, escape need


class SVITrend(str, Enum):
    INITIAL = "INITIAL"
    RISING = "RISING"
    FALLING = "FALLING"
    STABLE = "STABLE"


class SVIFeatureCategory(str, Enum):
    IMMEDIATE_SAFETY = "immediate_safety"
    COERCION_CONTROL = "coercion_control"
    ISOLATION_SUPPORT = "isolation_support"
    DISTRESS_OVERWHELM = "distress_overwhelm"
    HELP_BARRIERS = "help_barriers"
    PROTECTIVE_FACTORS = "protective_factors"


class SVIFeatureContribution(BaseModel):
    category: SVIFeatureCategory
    feature_name: str
    raw_score: float
    recency: str = "PRESENT"  # PRESENT | RECENT | HISTORICAL
    recency_weight: float = 1.0
    weighted_score: float
    matched_phrase: Optional[str] = None
    rule_id: Optional[str] = None
    description: str


class SVIAssessment(BaseModel):
    assessment_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    call_id: str
    session_id: str
    turn_index: int = 0
    score: int = Field(..., ge=0, le=100)
    band: SVIBand
    trend: SVITrend = SVITrend.INITIAL
    delta: int = 0
    assessment_completeness: float = Field(default=0.0, ge=0.0, le=1.0)
    features: List[SVIFeatureContribution] = Field(default_factory=list)
    top_contributors: List[str] = Field(default_factory=list)
    protective_factor_reduction: int = 0
    critical_override_applied: bool = False
    acoustic_evidence_available: bool = False
    acoustic_evidence_note: str = "Acoustic evidence: Not available in current phase (Phase 6 deferred)"
    requires_human_review: bool = False
    disclaimer: str = "Operational Prototype Priority Indicator — NOT a clinical, medical, or diagnostic score"
    evaluated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    svi_version: str = "v1"


class SVIEvaluationTurn(BaseModel):
    speaker: str = "caller"  # caller | agent | system
    text: str
    language: str = "en-IN"
    timestamp: Optional[str] = None


class SVIEvaluationRequest(BaseModel):
    call_id: Optional[str] = "sim-call-01"
    session_id: Optional[str] = "sim-sess-01"
    turn_index: int = 1
    turns: List[SVIEvaluationTurn] = Field(default_factory=list)
    safety_signals: Optional[List[Dict[str, Any]]] = None
    previous_score: Optional[int] = None


class SVIHistoryResponse(BaseModel):
    call_id: str
    session_id: str
    total_assessments: int
    assessments: List[SVIAssessment]
    latest_assessment: Optional[SVIAssessment] = None
