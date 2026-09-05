"""Integration tests for benchmark harness and safety recall verification."""

import pytest
from app.simulation.catalog import scenario_catalog
from app.simulation.harness import benchmark_harness, evaluate_single_scenario
from app.simulation.models import BenchmarkSuiteType


def test_evaluate_critical_scenario_safety_recall():
    crit_sc = scenario_catalog.get_scenario("SCEN-CRIT-001")
    assert crit_sc is not None

    res = evaluate_single_scenario(crit_sc)
    assert res.scenario_id == "SCEN-CRIT-001"
    assert res.safety_recall == 1.0
    assert not res.false_negative_hazard
    assert res.actual_svi_band in ("CRITICAL", "HIGH")
    assert res.passed is True


def test_evaluate_negation_trap_defense():
    neg_sc = scenario_catalog.get_scenario("SCEN-EDGE-001")
    assert neg_sc is not None

    res = evaluate_single_scenario(neg_sc)
    assert res.scenario_id == "SCEN-EDGE-001"
    # Prohibited trigger must NOT fire
    assert "IMMEDIATE_SELF_HARM_RISK" not in [t.upper() for t in res.actual_safety_triggers]
    assert res.safety_recall == 1.0


def test_benchmark_smoke_suite_execution():
    run = benchmark_harness.run_suite(BenchmarkSuiteType.SMOKE)
    assert run.status.value == "COMPLETED"
    assert run.total_scenarios >= 8
    assert run.passed_scenarios > 0
    assert run.pass_rate >= 0.85
    assert run.safety_recall_rate >= 0.90
    assert run.critical_safety_passed is True
    assert run.p95_latency_ms < 500.0  # sub-second benchmark latency
