"""
SAMVED Phase 14: Scenario Evaluation Lab Schemas
Pydantic API request and response schemas for evaluation operations.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from app.evaluation.models import (
    BaselineSnapshot,
    EvaluationMode,
    EvaluationRunRecord,
    EvaluationStatus,
    FaultType,
    ScenarioDefinition,
)


class EvaluationStatusResponse(BaseModel):
    status: str = "ready"
    engine_version: str = "1.0.0"
    scenarios_count: int
    baselines_count: int
    runs_count: int
    supported_modes: List[str] = ["OFFLINE", "INTEGRATED"]
    supported_suites: List[str] = [
        "smoke",
        "ci",
        "safety",
        "multilingual",
        "adaptive",
        "orchestration",
        "rag",
        "case",
        "followup",
        "privacy",
        "full",
    ]
    disclaimer: str = (
        "SYNTHETIC EVALUATION ENVIRONMENT: All scenarios, callers, and telephone interactions "
        "are strictly synthetic. No real victim records, live telephone lines, or emergency dispatches are invoked."
    )


class RunEvaluationRequest(BaseModel):
    scenario_id: str
    mode: EvaluationMode = EvaluationMode.OFFLINE
    seed: int = 42
    baseline_id: Optional[str] = None
    fault_override: Optional[FaultType] = None


class SuiteRunRequest(BaseModel):
    suite_id: str = "smoke"
    mode: EvaluationMode = EvaluationMode.OFFLINE
    seed: int = 42


class SuiteRunResponse(BaseModel):
    suite_id: str
    total_scenarios: int
    passed_count: int
    failed_count: int
    warning_count: int
    blocked_count: int
    duration_ms: float
    runs: List[EvaluationRunRecord]


class BaselineCreateRequest(BaseModel):
    run_id: str
    description: Optional[str] = None
    tag: str = "release-baseline"


class BaselineListResponse(BaseModel):
    baselines: List[BaselineSnapshot]
    total: int


class DiffRequest(BaseModel):
    current_run_id: str
    baseline_id: Optional[str] = None
    compare_run_id: Optional[str] = None


class ScenariosListResponse(BaseModel):
    scenarios: List[ScenarioDefinition]
    total: int


class RunsListResponse(BaseModel):
    runs: List[EvaluationRunRecord]
    total: int
