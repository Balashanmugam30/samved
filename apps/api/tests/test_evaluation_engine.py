"""
Unit tests for the SAMVED Phase 14 Evaluation Engine replay and metrics calculation.
"""

import pytest
from app.evaluation.corpus import get_scenario_by_id
from app.evaluation.engine import EvaluationEngine
from app.evaluation.models import EvaluationMode, EvaluationStatus


@pytest.fixture
def engine():
    return EvaluationEngine()


def test_engine_replay_general_scenario(engine):
    scenario = get_scenario_by_id("SCEN-GEN-001")
    assert scenario is not None

    record = engine.replay_scenario(scenario, mode=EvaluationMode.OFFLINE, seed=42)
    assert record.scenario_id == "SCEN-GEN-001"
    assert record.execution_status == "COMPLETED"
    assert record.evaluation_status in [EvaluationStatus.PASS, EvaluationStatus.WARNING]
    assert record.metrics.latency.total_ms > 0
    assert record.metrics.latency.p95_ms >= 0
    assert "safety" in record.metrics.latency.stage_breakdown
    assert len(record.assertions) > 0


def test_engine_deterministic_seed(engine):
    scenario = get_scenario_by_id("SCEN-GEN-001")
    assert scenario is not None

    run1 = engine.replay_scenario(scenario, mode=EvaluationMode.OFFLINE, seed=1234)
    run2 = engine.replay_scenario(scenario, mode=EvaluationMode.OFFLINE, seed=1234)

    assert run1.metrics.svi.get("score") == run2.metrics.svi.get("score")
    assert run1.metrics.safety.get("state") == run2.metrics.safety.get("state")
    assert run1.evaluation_status == run2.evaluation_status


def test_engine_threat_scenario(engine):
    scenario = get_scenario_by_id("SCEN-THREAT-001")
    assert scenario is not None

    record = engine.replay_scenario(scenario, mode=EvaluationMode.OFFLINE, seed=42)
    assert record.metrics.safety.get("state") in ["CRITICAL", "HIGH"]
    assert record.metrics.safety.get("human_review_required") is True
    assert record.metrics.followup.get("autonomous_dispatch") is False
