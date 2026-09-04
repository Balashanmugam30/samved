"""Unit tests for Operator Workstation data models and schemas."""

import pytest
from app.operator.models import (
    CallOperatorState,
    HandoffStatus,
    OperatorActionType,
    OperatorAuditEvent,
    OperatorNote,
    OperatorNoteCategory,
    OperatorOwnershipState,
)


def test_operator_ownership_states():
    """All expected ownership states exist and map to string representations."""
    assert OperatorOwnershipState.UNASSIGNED.value == "UNASSIGNED"
    assert OperatorOwnershipState.AI_ASSISTED.value == "AI_ASSISTED"
    assert OperatorOwnershipState.HUMAN_ASSIGNED.value == "HUMAN_ASSIGNED"
    assert OperatorOwnershipState.HUMAN_ACTIVE.value == "HUMAN_ACTIVE"
    assert OperatorOwnershipState.HANDOFF_PENDING.value == "HANDOFF_PENDING"
    assert OperatorOwnershipState.ENDED.value == "ENDED"


def test_handoff_status_values():
    """Handoff lifecycle states are complete and distinct."""
    assert HandoffStatus.AVAILABLE.value == "AVAILABLE"
    assert HandoffStatus.REQUESTED.value == "REQUESTED"
    assert HandoffStatus.PENDING.value == "PENDING"
    assert HandoffStatus.CONFIRMED.value == "CONFIRMED"
    assert HandoffStatus.CANCELLED.value == "CANCELLED"
    assert HandoffStatus.FAILED.value == "FAILED"


def test_operator_note_category_values():
    """All structured note categories are defined."""
    assert OperatorNoteCategory.GENERAL.value == "GENERAL"
    assert OperatorNoteCategory.SAFETY.value == "SAFETY"
    assert OperatorNoteCategory.FOLLOW_UP_NOTE.value == "FOLLOW_UP_NOTE"
    assert OperatorNoteCategory.HANDOFF_NOTE.value == "HANDOFF_NOTE"
    assert OperatorNoteCategory.TECHNICAL.value == "TECHNICAL"


def test_operator_note_instantiation():
    """OperatorNote initializes with default UUID and timestamp."""
    note = OperatorNote(
        call_id="call-123",
        text="Caller safe inside locked room",
        category=OperatorNoteCategory.SAFETY,
    )
    assert note.note_id is not None
    assert len(note.note_id) > 10
    assert note.call_id == "call-123"
    assert note.category == OperatorNoteCategory.SAFETY
    assert note.text == "Caller safe inside locked room"
    assert note.is_structured is True
    assert note.timestamp is not None


def test_operator_audit_event():
    """OperatorAuditEvent serializes correctly with structured details."""
    event = OperatorAuditEvent(
        call_id="call-456",
        action=OperatorActionType.TAKEOVER,
        actor_id="operator-01",
        summary="Human operator took over call",
        previous_state="AI_ASSISTED",
        new_state="HUMAN_ACTIVE",
        details={"reason": "Critical safety escalation"},
    )
    dumped = event.model_dump()
    assert dumped["event_id"] is not None
    assert dumped["action"] == "TAKEOVER"
    assert dumped["category"] == "OPERATOR"
    assert dumped["previous_state"] == "AI_ASSISTED"
    assert dumped["new_state"] == "HUMAN_ACTIVE"
    assert dumped["details"]["reason"] == "Critical safety escalation"


def test_call_operator_state_defaults():
    """CallOperatorState initializes with safe defaults."""
    state = CallOperatorState(call_id="call-789")
    assert state.call_id == "call-789"
    assert state.ownership_state == OperatorOwnershipState.AI_ASSISTED
    assert state.handoff_status == HandoffStatus.AVAILABLE
    assert state.adaptive_paused is False
    assert state.active_operator_id is None
