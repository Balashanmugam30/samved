"""Unit and lifecycle tests for Tele-Counselor warm handoff workflow."""

import pytest
from app.operator.models import HandoffStatus, OperatorOwnershipState
from app.operator.service import OperatorService


@pytest.fixture
def service():
    return OperatorService()


@pytest.mark.asyncio
async def test_full_warm_handoff_lifecycle(service):
    """Call transitions: AI_ASSISTED -> HUMAN_ACTIVE -> HANDOFF_PENDING -> CONFIRMED."""
    call_id = "handoff-lifecycle-call"

    # Step 1: Initial state
    state0 = await service.get_or_create_state(call_id)
    assert state0.ownership_state == OperatorOwnershipState.AI_ASSISTED
    assert state0.handoff_status == HandoffStatus.AVAILABLE

    # Step 2: Operator takeover
    state1 = await service.takeover(call_id, operator_id="op-1", reason="Intake complete")
    assert state1.ownership_state == OperatorOwnershipState.HUMAN_ACTIVE

    # Step 3: Handoff requested
    state2 = await service.request_handoff(
        call_id,
        operator_id="op-1",
        target_department="legal_aid",
        notes="Victim requesting protection order guidance",
    )
    assert state2.ownership_state == OperatorOwnershipState.HANDOFF_PENDING
    assert state2.handoff_status == HandoffStatus.REQUESTED
    assert state2.handoff_target == "legal_aid"
    assert state2.handoff_requested_at is not None

    # Step 4: Transfer confirmed
    state3 = await service.confirm_handoff(
        call_id,
        transfer_confirmed_by="sup-01",
        target_agent="counselor-advocate",
    )
    assert state3.handoff_status == HandoffStatus.CONFIRMED
    assert state3.active_operator_id == "counselor-advocate"
    assert state3.handoff_confirmed_at is not None


@pytest.mark.asyncio
async def test_handoff_cancellation_reverts_state(service):
    """Cancelling a handoff request safely reverts control to the initiating operator."""
    call_id = "handoff-cancel-call"

    await service.takeover(call_id, operator_id="op-1")
    await service.request_handoff(call_id, operator_id="op-1", target_department="shelter_services")
    cancelled = await service.cancel_handoff(call_id, operator_id="op-1", reason="Shelter capacity full")

    assert cancelled.handoff_status == HandoffStatus.CANCELLED
    assert cancelled.ownership_state == OperatorOwnershipState.HUMAN_ACTIVE
