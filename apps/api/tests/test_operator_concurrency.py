"""Concurrency and race-condition tests for Operator Workstation."""

import asyncio
import pytest
from app.operator.models import OperatorNoteCategory, OperatorOwnershipState
from app.operator.service import OperatorService


@pytest.fixture
def service():
    return OperatorService()


@pytest.mark.asyncio
async def test_concurrent_takeovers(service):
    """Simultaneous takeover requests on the same call resolve cleanly without race conditions."""
    call_id = "concurrent-takeover-call"

    # Launch 5 concurrent takeover attempts
    tasks = [
        service.takeover(call_id, operator_id=f"op-{i}", reason=f"Concurrent takeover {i}")
        for i in range(5)
    ]
    results = await asyncio.gather(*tasks)

    for state in results:
        assert state.ownership_state == OperatorOwnershipState.HUMAN_ACTIVE

    final_state = await service.get_or_create_state(call_id)
    assert final_state.ownership_state == OperatorOwnershipState.HUMAN_ACTIVE


@pytest.mark.asyncio
async def test_concurrent_notes_addition(service):
    """Simultaneous note additions do not overwrite one another."""
    call_id = "concurrent-notes-call"

    tasks = [
        service.add_note(call_id, operator_id=f"op-{i}", category=OperatorNoteCategory.GENERAL, text=f"Note {i}")
        for i in range(10)
    ]
    notes = await asyncio.gather(*tasks)
    assert len(notes) == 10

    stored = await service.get_notes(call_id)
    assert len(stored) == 10
    texts = [n.text for n in stored]
    for i in range(10):
        assert f"Note {i}" in texts


@pytest.mark.asyncio
async def test_multi_call_isolation(service):
    """Actions on Call A do NOT affect Call B state, notes, or ownership."""
    call_a = "call-alpha"
    call_b = "call-beta"

    # Take over call A, pause call B
    await service.takeover(call_a, operator_id="op-1", reason="A takeover")
    await service.pause_adaptive(call_b, operator_id="op-2", reason="B pause")

    # Add note to call A only
    await service.add_note(call_a, "op-1", OperatorNoteCategory.SAFETY, "Victim in room A")

    state_a = await service.get_or_create_state(call_a)
    state_b = await service.get_or_create_state(call_b)

    assert state_a.ownership_state == OperatorOwnershipState.HUMAN_ACTIVE
    assert state_a.adaptive_paused is False

    assert state_b.ownership_state == OperatorOwnershipState.AI_ASSISTED
    assert state_b.adaptive_paused is True

    notes_a = await service.get_notes(call_a)
    notes_b = await service.get_notes(call_b)

    assert len(notes_a) == 1
    assert len(notes_b) == 0
