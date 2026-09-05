"""
Unit tests for SAMVED Phase 14 Evaluation Lab domain models and schemas.
"""

import pytest
from app.evaluation.models import (
    BaselineSnapshot,
    CallerProfile,
    EvaluationAssertion,
    EvaluationFinding,
    EvaluationMode,
    EvaluationRunRecord,
    EvaluationStatus,
    FaultType,
    FindingSeverity,
    GoldenExpectations,
    LatencyMetrics,
    RunDiffItem,
    RunDiffResult,
    ScenarioDefinition,
    ScenarioTurn,
    SubsystemMetrics,
)
from app.evaluation.schemas import (
    BaselineCreateRequest,
    DiffRequest,
    EvaluationStatusResponse,
    RunEvaluationRequest,
    SuiteRunRequest,
    SuiteRunResponse,
)


def test_caller_profile_defaults():
    profile = CallerProfile()
    assert profile.caller_id == "SYNTHETIC-CALLER-01"
    assert profile.prior_contact_history is False


def test_scenario_turn_creation():
    turn = ScenarioTurn(turn_number=1, speaker="caller", text="Help me please")
    assert turn.turn_number == 1
    assert turn.speaker == "caller"
    assert turn.injected_fault == FaultType.NONE
    assert isinstance(turn.acoustic_features, dict)


def test_golden_expectations_validation():
    expectations = GoldenExpectations(
        expected_safety_state="CRITICAL",
        expected_svi_band="CRITICAL",
        expected_svi_score_range=[75, 100],
        expected_required_human_review=True,
        expected_language="hi-IN",
        expected_knowledge_citations=["CIT-BNS-85"],
        forbidden_actions=["autonomous_police_dispatch"],
        max_p95_latency_ms=1000.0,
    )
    assert expectations.expected_safety_state == "CRITICAL"
    assert expectations.expected_required_human_review is True
    assert "autonomous_police_dispatch" in expectations.forbidden_actions


def test_evaluation_run_record_serialization():
    record = EvaluationRunRecord(
        scenario_id="SCEN-GEN-001",
        mode=EvaluationMode.OFFLINE,
        seed=42,
        evaluation_status=EvaluationStatus.PASS,
        metrics=SubsystemMetrics(
            safety={"state": "SAFE"},
            latency=LatencyMetrics(total_ms=120.0, p95_ms=85.0),
        ),
    )
    assert record.scenario_id == "SCEN-GEN-001"
    assert record.synthetic_marker == "SYNTHETIC_EVALUATION"
    dumped = record.model_dump()
    assert dumped["evaluation_status"] == "PASS"
    assert dumped["metrics"]["latency"]["p95_ms"] == 85.0


def test_diff_result_structure():
    diff_item = RunDiffItem(
        field="safety_state",
        subsystem="safety",
        baseline_value="SAFE",
        current_value="HIGH",
        is_regression=False,
        message="Severity changed",
    )
    diff_result = RunDiffResult(
        baseline_id="BASE-1",
        current_run_id="RUN-1",
        scenario_id="SCEN-1",
        status="CHANGED",
        has_regression=False,
        differences=[diff_item],
    )
    assert len(diff_result.differences) == 1
    assert not diff_result.has_regression


def test_schemas_requests():
    req = RunEvaluationRequest(scenario_id="SCEN-GEN-001", seed=100)
    assert req.mode == EvaluationMode.OFFLINE
    assert req.seed == 100

    suite_req = SuiteRunRequest(suite_id="smoke")
    assert suite_req.suite_id == "smoke"

    b_req = BaselineCreateRequest(run_id="RUN-123", tag="gold")
    assert b_req.tag == "gold"
