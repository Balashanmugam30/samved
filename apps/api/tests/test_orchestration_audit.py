"""Tests for OrchestrationAuditLogger in SAMVED Phase 9."""

import pytest
from app.orchestration.audit import OrchestrationAuditLogger
from app.orchestration.models import OrchestrationResult, OrchestrationState


def test_audit_logger_run_and_query():
    logger = OrchestrationAuditLogger(max_runs=10, max_runs_per_call=5)
    call_id = "test-call-audit"

    r1 = OrchestrationResult(
        call_id=call_id,
        turn_id="turn-1",
        state=OrchestrationState.COMPLETED,
        total_latency_ms=120.0,
    )
    r2 = OrchestrationResult(
        call_id=call_id,
        turn_id="turn-2",
        state=OrchestrationState.DEGRADED,
        total_latency_ms=180.0,
    )

    logger.log_run(r1)
    logger.log_run(r2)

    history = logger.get_runs_for_call(call_id)
    assert len(history) == 2
    assert history[0].turn_id == "turn-1"
    assert history[1].turn_id == "turn-2"

    latest = logger.get_latest_run_for_call(call_id)
    assert latest is not None
    assert latest.turn_id == "turn-2"
    assert latest.state == OrchestrationState.DEGRADED


def test_audit_logger_bounded_queue():
    logger = OrchestrationAuditLogger(max_runs=3, max_runs_per_call=2)
    call_id = "test-call-bounded"

    for i in range(5):
        logger.log_run(
            OrchestrationResult(call_id=call_id, turn_id=f"turn-{i}")
        )

    history = logger.get_runs_for_call(call_id)
    assert len(history) == 2
    assert history[0].turn_id == "turn-3"
    assert history[1].turn_id == "turn-4"
