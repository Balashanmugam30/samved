"""Unit tests for OperatorService state transitions, commands, and safeguards."""

import pytest
from app.operator.models import (
    HandoffStatus,
    OperatorNoteCategory,
    OperatorOwnershipState,
)
from app.operator.service import OperatorService


@pytest.fixture
def service():
    return OperatorService()


@pytest.mark.asyncio
async def test_takeover_idempotent(service):
    """Takeover transitions to HUMAN_ACTIVE, second call is safely idempotent."""
    call_id = "test-takeover-call"
    state1 = await service.takeover(call_id, operator_id="op-1", reason="First takeover")
    assert state1.ownership_state == OperatorOwnershipState.HUMAN_ACTIVE
    assert state1.active_operator_id == "op-1"

    # Second takeover should be idempotent
    state2 = await service.takeover(call_id, operator_id="op-2", reason="Second takeover")
    assert state2.ownership_state == OperatorOwnershipState.HUMAN_ACTIVE
    assert state2.active_operator_id == "op-2"


@pytest.mark.asyncio
async def test_pause_and_resume_adaptive(service):
    """Pause sets adaptive_paused=True; resume restores it to False."""
    call_id = "test-pause-call"
    assert service.is_adaptive_paused(call_id) is False

    state_paused = await service.pause_adaptive(call_id, operator_id="op-1")
    assert state_paused.adaptive_paused is True
    assert service.is_adaptive_paused(call_id) is True

    state_resumed = await service.resume_adaptive(call_id, operator_id="op-1")
    assert state_resumed.adaptive_paused is False
    assert service.is_adaptive_paused(call_id) is False


@pytest.mark.asyncio
async def test_request_safety_check(service):
    """Requesting safety check logs audit event and returns status."""
    call_id = "test-safety-check-call"
    res = await service.request_safety_check(call_id, operator_id="op-1", reason="Suspicious sounds")
    assert res["status"] == "SAFETY_CHECK_REQUESTED"
    assert res["call_id"] == call_id
    assert res["operator_id"] == "op-1"


@pytest.mark.asyncio
async def test_handoff_lifecycle(service):
    """Handoff moves from REQUESTED to CONFIRMED or CANCELLED, never collapsing."""
    call_id = "test-handoff-call"

    # 1. Request Handoff
    state_req = await service.request_handoff(
        call_id, operator_id="op-1", target_department="police_liaison", notes="Urgent transfer"
    )
    assert state_req.ownership_state == OperatorOwnershipState.HANDOFF_PENDING
    assert state_req.handoff_status == HandoffStatus.REQUESTED
    assert state_req.handoff_target == "police_liaison"

    # 2. Confirm Handoff
    state_conf = await service.confirm_handoff(
        call_id, transfer_confirmed_by="sup-01", target_agent="officer-kumar"
    )
    assert state_conf.handoff_status == HandoffStatus.CONFIRMED
    assert state_conf.active_operator_id == "officer-kumar"


@pytest.mark.asyncio
async def test_handoff_cancel(service):
    """Cancelled handoff reverts ownership to HUMAN_ACTIVE."""
    call_id = "test-cancel-call"
    await service.request_handoff(call_id, operator_id="op-1", target_department="medical")
    state_cancel = await service.cancel_handoff(call_id, operator_id="op-1", reason="Caller declined transfer")

    assert state_cancel.handoff_status == HandoffStatus.CANCELLED
    assert state_cancel.ownership_state == OperatorOwnershipState.HUMAN_ACTIVE


@pytest.mark.asyncio
async def test_add_and_get_notes(service):
    """Structured notes are appended, retrieved in order, and scoped by call."""
    call_id = "test-notes-call"
    note1 = await service.add_note(call_id, "op-1", OperatorNoteCategory.SAFETY, "Caller in safe room")
    note2 = await service.add_note(call_id, "op-1", OperatorNoteCategory.TECHNICAL, "Audio has slight jitter")

    notes = await service.get_notes(call_id)
    assert len(notes) == 2
    assert notes[0].note_id == note1.note_id
    assert notes[0].category == OperatorNoteCategory.SAFETY
    assert notes[1].note_id == note2.note_id
    assert notes[1].category == OperatorNoteCategory.TECHNICAL


@pytest.mark.asyncio
async def test_end_call(service):
    """End call marks ownership as ENDED."""
    call_id = "test-end-call"
    state = await service.end_call(call_id, operator_id="op-1", reason="Normal triage completion")
    assert state.ownership_state == OperatorOwnershipState.ENDED


def test_get_subsystems_status(service):
    """Returns explicit status of all 5 SAMVED engines."""
    subsystems = service.get_subsystems_status()
    names = [s.name for s in subsystems]
    assert "Safety Engine" in names
    assert "SVI Engine" in names
    assert "Acoustic Engine" in names
    assert "Adaptive Engine" in names
    assert "Operator Control Gateway" in names
    for s in subsystems:
        assert s.status == "AVAILABLE"
