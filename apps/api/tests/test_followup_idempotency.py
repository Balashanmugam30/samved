"""Idempotency and retry safety tests for SAMVED Follow-up Subsystem."""

import pytest

from app.followup.schemas import (
    ApproveFollowupRequest,
    CompleteFollowupRequest,
    CreateFollowupRequest,
    StartFollowupRequest,
)
from app.followup.service import FollowupService
from app.schemas.events import ConsentState, FollowupStatus


@pytest.mark.asyncio
async def test_repeated_completion_is_idempotent():
    svc = FollowupService(auto_seed=False)
    req = CreateFollowupRequest(
        purpose="Verify idempotent completion",
        scheduled_for="2026-09-05T18:30:00Z",
        safe_contact_window="18:00-20:00",
        consent_state=ConsentState.GRANTED,
    )
    fol, _ = await svc.create_followup("case-1001", req)
    await svc.start_followup(fol.followup_id, StartFollowupRequest())

    # First completion
    comp1 = await svc.complete_followup(
        fol.followup_id, CompleteFollowupRequest(outcome="CONTACTED_SUCCESSFULLY")
    )
    assert comp1.status == FollowupStatus.COMPLETED

    # Repeated completion should return same record safely without error
    comp2 = await svc.complete_followup(
        fol.followup_id, CompleteFollowupRequest(outcome="CONTACTED_SUCCESSFULLY")
    )
    assert comp2.status == FollowupStatus.COMPLETED
    assert comp2.followup_id == comp1.followup_id
