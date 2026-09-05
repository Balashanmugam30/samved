"""SimulationService singleton for SAMVED Phase 14 Scenario Simulation Engine."""

from datetime import datetime, timezone
import logging
from typing import Any, Dict, List, Optional
import uuid

from app.simulation.catalog import scenario_catalog
from app.simulation.harness import benchmark_harness
from app.simulation.metrics import calculate_wer_cer
from app.simulation.models import (
    BenchmarkRun,
    BenchmarkRunStatus,
    BenchmarkSuiteType,
    SimulationScenario,
    TrainingDrill,
    TrainingSession,
    TrainingTurnEvaluation,
    WERMetricResult,
)
from app.simulation.sandbox import training_sandbox

logger = logging.getLogger("samved.simulation.service")


class SimulationService:
    """Central service managing benchmark runs, scenario catalogs, and training drills."""

    def __init__(self):
        self._runs: Dict[str, BenchmarkRun] = {}
        self._seed_baseline_run()

    def _seed_baseline_run(self) -> None:
        """Seeds a verified baseline benchmark run for immediate UI hydration and status checks."""
        try:
            baseline = benchmark_harness.run_suite(BenchmarkSuiteType.SMOKE)
            self._runs[baseline.run_id] = baseline
            logger.info(f"SimulationService seeded baseline benchmark run: {baseline.run_id}")
        except Exception as e:
            logger.warning(f"Failed to pre-seed baseline benchmark run: {e}")

    def get_status(self) -> Dict[str, Any]:
        """Returns operational status of the simulation subsystem."""
        langs = sorted(list({s.language for s in scenario_catalog.list_scenarios()}))
        return {
            "status": "healthy",
            "version": "v1.0.0",
            "total_scenarios": scenario_catalog.count(),
            "total_drills": len(training_sandbox.list_drills()),
            "languages_supported": langs,
            "recent_benchmark_runs": len(self._runs),
        }

    def list_scenarios(
        self,
        band: Optional[str] = None,
        language: Optional[str] = None,
        tag: Optional[str] = None,
    ) -> List[SimulationScenario]:
        return scenario_catalog.list_scenarios(band=band, language=language, tag=tag)

    def get_scenario(self, scenario_id: str) -> Optional[SimulationScenario]:
        return scenario_catalog.get_scenario(scenario_id)

    def run_benchmark(
        self, suite_type: BenchmarkSuiteType = BenchmarkSuiteType.SMOKE
    ) -> BenchmarkRun:
        """Executes a benchmark suite and records results in history."""
        run = benchmark_harness.run_suite(suite_type)
        self._runs[run.run_id] = run
        return run

    def list_benchmark_runs(self) -> List[BenchmarkRun]:
        """Returns all completed benchmark runs, sorted newest first."""
        return sorted(list(self._runs.values()), key=lambda r: r.started_at, reverse=True)

    def get_benchmark_run(self, run_id: str) -> Optional[BenchmarkRun]:
        return self._runs.get(run_id)

    def evaluate_wer_cer(self, reference: str, hypothesis: str) -> WERMetricResult:
        return calculate_wer_cer(reference, hypothesis)

    def list_training_drills(self, difficulty: Optional[str] = None) -> List[TrainingDrill]:
        return training_sandbox.list_drills(difficulty=difficulty)

    def get_training_drill(self, drill_key: str) -> Optional[TrainingDrill]:
        return training_sandbox.get_drill(drill_key)

    def start_training_session(
        self, drill_key: str, trainee_id: str = "T-1001", trainee_name: str = "Counselor Trainee"
    ) -> TrainingSession:
        return training_sandbox.start_session(drill_key=drill_key, trainee_id=trainee_id, trainee_name=trainee_name)

    def submit_training_turn(
        self, session_id: str, trainee_input: str
    ) -> TrainingTurnEvaluation:
        return training_sandbox.evaluate_trainee_turn(session_id=session_id, trainee_input=trainee_input)

    def get_training_session(self, session_id: str) -> Optional[TrainingSession]:
        return training_sandbox.get_session(session_id)


simulation_service = SimulationService()
