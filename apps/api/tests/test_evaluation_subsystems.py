"""
Unit tests for subsystem evaluation: Acoustic, Adaptive, RAG, Orchestration Faults, and Multilingual.
"""

import pytest
from app.evaluation.corpus import get_scenario_by_id
from app.evaluation.engine import EvaluationEngine
from app.evaluation.faults import FaultInjectionInterceptor
from app.evaluation.models import EvaluationMode, FaultType


@pytest.fixture
def engine():
    return EvaluationEngine()


def test_acoustic_prolonged_silence_evaluation(engine):
    """Verifies that acoustic features are analyzed during replay."""
    scenario = get_scenario_by_id("SCEN-ACOUSTIC-001")
    assert scenario is not None

    record = engine.replay_scenario(scenario, mode=EvaluationMode.OFFLINE, seed=42)
    assert record.metrics.acoustic.get("frames_analyzed") > 0


def test_rag_statutory_citations(engine):
    """Verifies that statutory citations (NDPS Section 64A) are grounded during replay."""
    scenario = get_scenario_by_id("SCEN-RAG-001")
    assert scenario is not None

    record = engine.replay_scenario(scenario, mode=EvaluationMode.OFFLINE, seed=42)
    cits = record.metrics.rag.get("citations", [])
    assert len(cits) > 0
    assert "CIT-NDPS-IMMUNITY-01" in cits


def test_orchestration_fault_tolerance(engine):
    """Verifies that orchestration timeouts trigger graceful fallback."""
    interceptor = FaultInjectionInterceptor()
    fault_res = interceptor.intercept_orchestration(
        FaultType.ORCHESTRATION_TIMEOUT, ["safety_context", "operator_briefing"]
    )
    assert fault_res["timeout"] is True
    assert "safety_context_agent" in fault_res["completed_agents"]
    assert "operator_briefing_agent" in fault_res["failed_agents"]

    scenario = get_scenario_by_id("SCEN-FAULT-001")
    assert scenario is not None
    record = engine.replay_scenario(scenario, mode=EvaluationMode.OFFLINE, seed=42)
    assert record.metrics.orchestration.get("dag_execution_successful") is False


def test_multilingual_replays(engine):
    """Verifies multi-lingual scenarios in Tamil, Hindi, and Telugu."""
    for s_id, exp_lang in [
        ("SCEN-LANG-TA-001", "ta-IN"),
        ("SCEN-LANG-HI-001", "hi-IN"),
        ("SCEN-LANG-TE-001", "te-IN"),
    ]:
        scenario = get_scenario_by_id(s_id)
        assert scenario is not None
        record = engine.replay_scenario(scenario, mode=EvaluationMode.OFFLINE, seed=42)
        assert record.metrics.adaptive.get("language") == exp_lang
