"""SAMVED Phase 14: Scenario Simulation Engine & Operator Training Sandbox.

Automated synthetic scenario benchmark suite, Indic WER/CER speech evaluation,
deterministic safety recall verification, and tele-counselor training sandbox.
"""

from app.simulation.models import (
    BenchmarkSuiteType,
    BenchmarkRunStatus,
    NoiseProfile,
    DrillDifficulty,
    SimulationScenario,
    BenchmarkRun,
    ScenarioEvaluationResult,
    WERMetricResult,
    TrainingDrill,
    TrainingSession,
    TrainingTurnEvaluation,
)
from app.simulation.service import simulation_service

__all__ = [
    "BenchmarkSuiteType",
    "BenchmarkRunStatus",
    "NoiseProfile",
    "DrillDifficulty",
    "SimulationScenario",
    "BenchmarkRun",
    "ScenarioEvaluationResult",
    "WERMetricResult",
    "TrainingDrill",
    "TrainingSession",
    "TrainingTurnEvaluation",
    "simulation_service",
]
