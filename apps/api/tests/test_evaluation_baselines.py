"""
Unit tests for evaluation baselines and run-to-run regression diffs.
"""

import pytest
from app.evaluation.corpus import get_scenario_by_id
from app.evaluation.diff import compute_baseline_diff
from app.evaluation.engine import EvaluationEngine
from app.evaluation.models import (
    BaselineSnapshot,
    EvaluationMode,
    EvaluationStatus,
    SubsystemMetrics,
)
from app.evaluation.service import EvaluationService


@pytest.fixture
def service():
    return EvaluationService()


def test_baseline_creation_and_retrieval(service):
    run = service.run_scenario("SCEN-GEN-001", mode=EvaluationMode.OFFLINE, seed=42)
    baseline = service.create_baseline(run.run_id, description="Golden v1.0", tag="v1.0")

    assert baseline is not None
    assert baseline.scenario_id == "SCEN-GEN-001"
    fetched = service.get_baseline(baseline.baseline_id)
    assert fetched is not None
    assert fetched.baseline_id == baseline.baseline_id


def test_diff_identical_runs(service):
    run = service.run_scenario("SCEN-GEN-001", mode=EvaluationMode.OFFLINE, seed=42)
    baseline = service.create_baseline(run.run_id)

    diff = service.compute_diff(current_run_id=run.run_id, baseline_id=baseline.baseline_id)
    assert diff is not None
    assert diff.has_regression is False
    assert diff.status in ["IDENTICAL", "CHANGED"]


def test_diff_safety_regression_detection(service):
    """Simulates a drop in safety severity to verify regression flagging."""
    engine = EvaluationEngine()
    scenario = get_scenario_by_id("SCEN-THREAT-001")
    assert scenario is not None

    run_baseline = engine.replay_scenario(scenario, mode=EvaluationMode.OFFLINE, seed=42)
    baseline = BaselineSnapshot(
        baseline_id="BASE-THREAT-TEST",
        scenario_id="SCEN-THREAT-001",
        scenario_version="1.0",
        evaluation_version="1.0",
        seed=42,
        status=EvaluationStatus.PASS,
        metrics=run_baseline.metrics,
    )

    # Fabricate a regressed run where safety was downgraded to SAFE
    run_regressed = engine.replay_scenario(scenario, mode=EvaluationMode.OFFLINE, seed=42)
    run_regressed.metrics.safety["state"] = "SAFE"

    diff = compute_baseline_diff(baseline, run_regressed)
    assert diff.has_regression is True
    assert any(d.field == "safety_state" and d.is_regression for d in diff.differences)
