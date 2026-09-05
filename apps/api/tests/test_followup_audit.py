"""Audit logging and immutability tests for SAMVED Follow-up Subsystem."""

import pytest

from app.followup.audit import get_audit_logger
from app.followup.schemas import (
    CancelFollowupRequest,
    CompleteFollowupRequest,
    CreateFollowupRequest,
    RecordAttemptRequest,
    StartFollowupRequest,
)
from app.followup.service import FollowupService
from app.schemas.events import ConsentState, ContactChannel, ContactResult, FollowupStatus


@pytest.mark.asyncio
async def test_audit_records_generated_for_every_action():
    audit_logger = get_audit_logger()
    audit_logger.clear()

    svc = FollowupService(auto_seed=False)
    req = CreateFollowupRequest(
        purpose="Verify audit trail fidelity",
        scheduled_for="2026-09-05T18:30:00Z",
        safe_contact_window="18:00-20:00",
        consent_state=ConsentState.GRANTED,
        operator_id="operator-audit-test",
    )
    fol, _ = await svc.create_followup("case-1001", req)
    await svc.start_followup(fol.followup_id, StartFollowupRequest(operator_id="operator-audit-test"))
    await svc.record_attempt(
        fol.followup_id,
        RecordAttemptRequest(
            channel=ContactChannel.OPERATOR_CALLBACK,
            result=ContactResult.NO_ANSWER,
            operator_id="operator-audit-test",
        ),
    )
    await svc.complete_followup(
        fol.followup_id,
        CompleteFollowupRequest(outcome="CONTACTED_SUCCESSFULLY", operator_id="operator-audit-test"),
    )

    logs = audit_logger.get_logs_for_followup(fol.followup_id)
    assert len(logs) >= 4

    actions = [l.action for l in logs]
    assert "CREATED" in actions
    assert "STARTED" in actions
    assert "ATTEMPTED" in actions
    assert "COMPLETED" in actions

    for log in logs:
        assert log.actor_id == "operator-audit-test"
        assert log.timestamp is not None
        assert log.case_id == "case-1001"
