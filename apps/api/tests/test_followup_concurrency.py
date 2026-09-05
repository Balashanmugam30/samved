"""Concurrency and race-condition tests for SAMVED Follow-up Subsystem."""

import asyncio
import pytest

from app.followup.schemas import CreateFollowupRequest, RecordAttemptRequest
from app.followup.service import FollowupService
from app.schemas.events import ConsentState, ContactChannel, ContactResult


@pytest.mark.asyncio
async def test_concurrent_attempt_recording():
    svc = FollowupService(auto_seed=False)
    req = CreateFollowupRequest(
        purpose="Verify concurrent attempt recording",
        scheduled_for="2026-09-05T18:30:00Z",
        safe_contact_window="18:00-20:00",
        consent_state=ConsentState.GRANTED,
        recurrence_max=1,
    )
    fol, _ = await svc.create_followup("case-1001", req)

    # Launch two concurrent attempts
    async def record():
        return await svc.record_attempt(
            fol.followup_id,
            RecordAttemptRequest(
                channel=ContactChannel.OPERATOR_CALLBACK,
                result=ContactResult.NO_ANSWER,
                operator_id="op-concurrent",
            ),
        )

    results = await asyncio.gather(record(), record(), return_exceptions=True)
    # Both should be serialized cleanly by the lock
    successes = [r for r in results if not isinstance(r, Exception)]
    assert len(successes) == 2

    # Check that final attempt_count is exactly 2
    f_final = await svc.get_followup(fol.followup_id)
    assert f_final.attempt_count == 2
    attempts = await svc.get_attempts(fol.followup_id)
    assert len(attempts) == 2


@pytest.mark.asyncio
async def test_concurrent_duplicate_creation_rejected():
    svc = FollowupService(auto_seed=False)
    req = CreateFollowupRequest(
        purpose="Identical concurrent purpose",
        scheduled_for="2026-09-05T18:30:00Z",
        safe_contact_window="18:00-20:00",
        consent_state=ConsentState.GRANTED,
    )

    # Launch two concurrent creations with identical purpose and channel
    async def create():
        return await svc.create_followup("case-1001", req)

    results = await asyncio.gather(create(), create(), return_exceptions=True)
    # One should succeed, the other should be rejected as a duplicate
    successes = [r for r in results if not isinstance(r, Exception)]
    failures = [r for r in results if isinstance(r, Exception)]

    assert len(successes) == 1
    assert len(failures) == 1
    assert "DUPLICATE_FOLLOW_UP" in str(failures[0])
