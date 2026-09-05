"""Unit tests for SAMVED Follow-up State Machine transitions."""

import pytest

from app.followup.scheduler import FrozenTimeProvider
from app.followup.schemas import (
    CancelFollowupRequest,
    CompleteFollowupRequest,
    CreateFollowupRequest,
    RecordAttemptRequest,
    RescheduleFollowupRequest,
    StartFollowupRequest,
)
from app.followup.service import FollowupService
from app.schemas.events import ConsentState, ContactChannel, ContactResult, FollowupStatus


@pytest.mark.asyncio
async def test_legal_state_machine_flow():
    svc = FollowupService(auto_seed=False)
    req = CreateFollowupRequest(
        purpose="Comprehensive follow-up state transition check",
        scheduled_for="2026-09-05T18:30:00Z",
        safe_contact_window="18:00-20:00",
        consent_state=ConsentState.GRANTED,
    )
    fol, _ = await svc.create_followup("case-1001", req)
    assert fol.status == FollowupStatus.SCHEDULED

    # Start -> IN_PROGRESS
    fol = await svc.start_followup(fol.followup_id, StartFollowupRequest())
    assert fol.status == FollowupStatus.IN_PROGRESS

    # Complete -> COMPLETED
    fol = await svc.complete_followup(fol.followup_id, CompleteFollowupRequest(outcome="CONTACTED_SUCCESSFULLY"))
    assert fol.status == FollowupStatus.COMPLETED


@pytest.mark.asyncio
async def test_illegal_state_transitions_rejected():
    svc = FollowupService(auto_seed=False)
    req = CreateFollowupRequest(
        purpose="Verify illegal transition rejection",
        scheduled_for="2026-09-05T18:30:00Z",
        safe_contact_window="18:00-20:00",
        consent_state=ConsentState.GRANTED,
    )
    fol, _ = await svc.create_followup("case-1001", req)
    await svc.start_followup(fol.followup_id, StartFollowupRequest())
    await svc.complete_followup(fol.followup_id, CompleteFollowupRequest(outcome="CONTACTED_SUCCESSFULLY"))

    # Cannot cancel completed task
    with pytest.raises(ValueError, match="Cannot cancel"):
        await svc.cancel_followup(fol.followup_id, CancelFollowupRequest(reason="Trying to cancel"))

    # Cannot reschedule completed task
    with pytest.raises(ValueError, match="Cannot reschedule"):
        await svc.reschedule_followup(
            fol.followup_id,
            RescheduleFollowupRequest(
                scheduled_for="2026-09-05T19:00:00Z",
                safe_contact_window="18:00-20:00",
                reason="Trying to reschedule",
            ),
        )

    # Cannot start completed task
    with pytest.raises(ValueError, match="Cannot start"):
        await svc.start_followup(fol.followup_id, StartFollowupRequest())


@pytest.mark.asyncio
async def test_caller_declined_blocks_task():
    svc = FollowupService(auto_seed=False)
    req = CreateFollowupRequest(
        purpose="Verify caller refusal blocks task",
        scheduled_for="2026-09-05T18:30:00Z",
        safe_contact_window="18:00-20:00",
        consent_state=ConsentState.GRANTED,
    )
    fol, _ = await svc.create_followup("case-1001", req)
    await svc.start_followup(fol.followup_id, StartFollowupRequest())

    # Record attempt where caller declines
    fol, att = await svc.record_attempt(
        fol.followup_id,
        RecordAttemptRequest(
            channel=ContactChannel.OPERATOR_CALLBACK,
            result=ContactResult.CALLER_DECLINED,
            notes="Caller said please do not call back",
        ),
    )
    assert fol.status == FollowupStatus.BLOCKED
    assert fol.consent_state == ConsentState.REFUSED
    assert "CALLER_DECLINED" in fol.blocked_reason
