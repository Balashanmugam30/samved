"""Unit tests for Structured Operator Notes."""

import pytest
from app.operator.models import OperatorNoteCategory
from app.operator.service import OperatorService


@pytest.fixture
def service():
    return OperatorService()


@pytest.mark.asyncio
async def test_operator_notes_categories_and_ordering(service):
    """Verifies all note categories can be created and are ordered chronologically."""
    call_id = "test-notes-categories-call"

    categories = [
        (OperatorNoteCategory.GENERAL, "General triage intake completed"),
        (OperatorNoteCategory.SAFETY, "Perpetrator not in immediate vicinity"),
        (OperatorNoteCategory.FOLLOW_UP_NOTE, "Schedule check-in call in 24 hours"),
        (OperatorNoteCategory.HANDOFF_NOTE, "Transferring to Tier-2 trauma counselor"),
        (OperatorNoteCategory.TECHNICAL, "Audio latency increased briefly during cell switch"),
    ]

    for cat, text in categories:
        note = await service.add_note(call_id, operator_id="op-1", category=cat, text=text)
        assert note.category == cat
        assert note.text == text
        assert note.is_structured is True

    stored = await service.get_notes(call_id)
    assert len(stored) == 5
    for i, (cat, text) in enumerate(categories):
        assert stored[i].category == cat
        assert stored[i].text == text


@pytest.mark.asyncio
async def test_notes_call_isolation(service):
    """Notes added to Call X never appear in Call Y."""
    call_x = "call-x"
    call_y = "call-y"

    await service.add_note(call_x, "op-1", OperatorNoteCategory.SAFETY, "Note for X")
    await service.add_note(call_y, "op-2", OperatorNoteCategory.GENERAL, "Note for Y")

    notes_x = await service.get_notes(call_x)
    notes_y = await service.get_notes(call_y)

    assert len(notes_x) == 1
    assert notes_x[0].text == "Note for X"

    assert len(notes_y) == 1
    assert notes_y[0].text == "Note for Y"
