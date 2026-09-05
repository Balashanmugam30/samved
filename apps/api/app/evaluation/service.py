"""
SAMVED Phase 14: Evaluation Service
Coordinates scenario evaluation runs, suite orchestration, cancellation, baselines, and diff analysis.
"""

from __future__ import annotations

import logging
import time
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional, Set

from app.evaluation.corpus import (
    SYNTHETIC_SCENARIOS,
    get_scenario_by_id,
    get_scenarios_by_suite,
    get_scenarios_by_tag,
)
from app.evaluation.diff import compute_baseline_diff
from app.evaluation.engine import EvaluationEngine
from app.evaluation.models import (
    BaselineSnapshot,
    EvaluationMode,
    EvaluationRunRecord,
    EvaluationStatus,
    FaultType,
    RunDiffItem,
    RunDiffResult,
    ScenarioDefinition,
)
from app.evaluation.schemas import (
    EvaluationStatusResponse,
    SuiteRunResponse,
)

logger = logging.getLogger("samved.evaluation.service")


class EvaluationService:
    """
    Singleton service managing SAMVED Evaluation Lab runs, baselines, and suites.
    """

    def __init__(self, engine: Optional[EvaluationEngine] = None) -> None:
        self.engine = engine or EvaluationEngine()
        self._runs: Dict[str, EvaluationRunRecord] = {}
        self._baselines: Dict[str, BaselineSnapshot] = {}
        self._cancelled_runs: Set[str] = set()
        self._initialize_default_baselines()

    def _initialize_default_baselines(self) -> None:
        """Seeds canonical golden baselines for key benchmark scenarios."""
        canonical_ids = ["SCEN-GEN-001", "SCEN-THREAT-001", "SCEN-WEAPON-001", "SCEN-MED-001", "SCEN-HARM-001"]
        for scen_id in canonical_ids:
            scen = get_scenario_by_id(scen_id)
            if scen:
                run = self.engine.replay_scenario(scen, mode=EvaluationMode.OFFLINE, seed=42)
                base = BaselineSnapshot(
                    baseline_id=f"BASE-{scen_id.lower()}-v1",
                    scenario_id=scen.scenario_id,
                    scenario_version=scen.scenario_version,
                    evaluation_version="1.0",
                    seed=42,
                    status=run.evaluation_status,
                    metrics=run.metrics,
                    captured_at=datetime.now(timezone.utc).isoformat(),
                )
                self._baselines[base.baseline_id] = base

    def get_status(self) -> EvaluationStatusResponse:
        """Returns simulator health, available scenario/baseline/run counts, and governance disclaimers."""
        return EvaluationStatusResponse(
            status="ready",
            engine_version="1.0.0",
            scenarios_count=len(SYNTHETIC_SCENARIOS),
            baselines_count=len(self._baselines),
            runs_count=len(self._runs),
            supported_modes=["OFFLINE", "INTEGRATED"],
            supported_suites=[
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
            ],
            disclaimer=(
                "SYNTHETIC EVALUATION ENVIRONMENT: All scenarios, callers, and telephone interactions "
                "are strictly synthetic. No real victim records, live telephone lines, or emergency dispatches are invoked."
            ),
        )

    def list_scenarios(
        self, tag: Optional[str] = None, suite: Optional[str] = None
    ) -> List[ScenarioDefinition]:
        """Lists synthetic scenarios with optional tag or suite filtering."""
        if suite:
            return get_scenarios_by_suite(suite)
        if tag:
            return get_scenarios_by_tag(tag)
        return list(SYNTHETIC_SCENARIOS)

    def get_scenario(self, scenario_id: str) -> Optional[ScenarioDefinition]:
        """Fetches a scenario definition by ID."""
        return get_scenario_by_id(scenario_id)

    def run_scenario(
        self,
        scenario_id: str,
        mode: EvaluationMode = EvaluationMode.OFFLINE,
        seed: int = 42,
        baseline_id: Optional[str] = None,
        fault_override: Optional[FaultType] = None,
    ) -> EvaluationRunRecord:
        """Executes an evaluation run for a single scenario."""
        scenario = get_scenario_by_id(scenario_id)
        if not scenario:
            raise ValueError(f"Scenario '{scenario_id}' not found in synthetic corpus.")

        baseline = self._baselines.get(baseline_id) if baseline_id else None
        record = self.engine.replay_scenario(
            scenario=scenario,
            mode=mode,
            seed=seed,
            baseline=baseline,
            fault_override=fault_override,
        )

        if record.run_id in self._cancelled_runs:
            record.execution_status = "CANCELLED"

        self._runs[record.run_id] = record
        logger.info(f"Evaluation run {record.run_id} completed: status={record.evaluation_status.value}")
        return record

    def run_suite(
        self,
        suite_id: str = "smoke",
        mode: EvaluationMode = EvaluationMode.OFFLINE,
        seed: int = 42,
    ) -> SuiteRunResponse:
        """Executes an evaluation suite across multiple scenarios."""
        scenarios = get_scenarios_by_suite(suite_id)
        t_start = time.perf_counter()
        runs: List[EvaluationRunRecord] = []
        passed = 0
        failed = 0
        warning = 0
        blocked = 0

        for scen in scenarios:
            record = self.engine.replay_scenario(scenario=scen, mode=mode, seed=seed)
            record.suite_id = suite_id
            self._runs[record.run_id] = record
            runs.append(record)

            if record.evaluation_status == EvaluationStatus.PASS:
                passed += 1
            elif record.evaluation_status == EvaluationStatus.FAIL:
                failed += 1
            elif record.evaluation_status == EvaluationStatus.WARNING:
                warning += 1
            elif record.evaluation_status == EvaluationStatus.BLOCKED:
                blocked += 1

        total_ms = (time.perf_counter() - t_start) * 1000.0

        return SuiteRunResponse(
            suite_id=suite_id,
            total_scenarios=len(scenarios),
            passed_count=passed,
            failed_count=failed,
            warning_count=warning,
            blocked_count=blocked,
            duration_ms=round(total_ms, 2),
            runs=runs,
        )

    def cancel_run(self, run_id: str) -> bool:
        """Cancels an in-flight or pending run."""
        self._cancelled_runs.add(run_id)
        if run_id in self._runs:
            self._runs[run_id].execution_status = "CANCELLED"
            return True
        return False

    def list_runs(
        self,
        scenario_id: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 50,
    ) -> List[EvaluationRunRecord]:
        """Lists past evaluation runs."""
        results = list(self._runs.values())
        if scenario_id:
            results = [r for r in results if r.scenario_id == scenario_id]
        if status:
            results = [r for r in results if r.evaluation_status.value == status or r.execution_status == status]
        results.reverse()
        return results[:limit]

    def get_run(self, run_id: str) -> Optional[EvaluationRunRecord]:
        """Retrieves a single run record by ID."""
        return self._runs.get(run_id)

    def list_baselines(self) -> List[BaselineSnapshot]:
        """Lists all established golden baseline snapshots."""
        return list(self._baselines.values())

    def get_baseline(self, baseline_id: str) -> Optional[BaselineSnapshot]:
        """Retrieves a baseline snapshot by ID."""
        return self._baselines.get(baseline_id)

    def create_baseline(
        self, run_id: str, description: Optional[str] = None, tag: str = "release-baseline"
    ) -> Optional[BaselineSnapshot]:
        """Creates a baseline snapshot from an existing successful run."""
        run = self._runs.get(run_id)
        if not run:
            return None

        baseline_id = f"BASE-{run.scenario_id.lower()}-{uuid.uuid4().hex[:6]}"
        snapshot = BaselineSnapshot(
            baseline_id=baseline_id,
            scenario_id=run.scenario_id,
            scenario_version=run.scenario_version,
            evaluation_version="1.0",
            seed=run.seed,
            status=run.evaluation_status,
            metrics=run.metrics,
            captured_at=datetime.now(timezone.utc).isoformat(),
        )
        self._baselines[baseline_id] = snapshot
        return snapshot

    def compute_diff(
        self,
        current_run_id: str,
        baseline_id: Optional[str] = None,
        compare_run_id: Optional[str] = None,
    ) -> Optional[RunDiffResult]:
        """Computes regression and drift diff between a run and a baseline or another run."""
        curr_run = self._runs.get(current_run_id)
        if not curr_run:
            return None

        if baseline_id:
            baseline = self._baselines.get(baseline_id)
            if not baseline:
                return None
            return compute_baseline_diff(baseline, curr_run)

        if compare_run_id:
            comp_run = self._runs.get(compare_run_id)
            if not comp_run:
                return None
            pseudo_baseline = BaselineSnapshot(
                baseline_id=f"BASE-PSEUDO-{comp_run.run_id}",
                scenario_id=comp_run.scenario_id,
                scenario_version=comp_run.scenario_version,
                evaluation_version="1.0",
                seed=comp_run.seed,
                status=comp_run.evaluation_status,
                metrics=comp_run.metrics,
                captured_at=comp_run.completed_at or comp_run.started_at,
            )
            return compute_baseline_diff(pseudo_baseline, curr_run)

        return None


# Global singleton instance
_evaluation_service: Optional[EvaluationService] = None


def get_evaluation_service() -> EvaluationService:
    global _evaluation_service
    if _evaluation_service is None:
        _evaluation_service = EvaluationService()
    return _evaluation_service
