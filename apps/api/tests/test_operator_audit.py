"""Unit tests for Operator Audit Logger integrity and immutability."""

import pytest
from app.operator.audit import OperatorAuditLogger
from app.operator.models import OperatorActionType


@pytest.fixture
def audit_logger():
    return OperatorAuditLogger(max_history_per_call=10)


@pytest.mark.asyncio
async def test_audit_log_append_only(audit_logger):
    """Audit events are strictly appended and cannot overwrite previous records."""
    call_id = "test-audit-call"

    e1 = await audit_logger.log_action(
        call_id=call_id,
        action=OperatorActionType.TAKEOVER,
        actor_id="op-1",
        summary="Takeover 1",
    )
    e2 = await audit_logger.log_action(
        call_id=call_id,
        action=OperatorActionType.PAUSE_ADAPTIVE,
        actor_id="op-1",
        summary="Pause 1",
    )

    trail = await audit_logger.get_audit_trail(call_id)
    assert len(trail) == 2
    assert trail[0].event_id == e1.event_id
    assert trail[1].event_id == e2.event_id
    assert trail[0].action == OperatorActionType.TAKEOVER
    assert trail[1].action == OperatorActionType.PAUSE_ADAPTIVE


@pytest.mark.asyncio
async def test_audit_log_bounded_memory(audit_logger):
    """Audit records are bounded to max_history_per_call preventing unbounded memory leaks."""
    call_id = "test-bounded-call"

    for i in range(15):
        await audit_logger.log_action(
            call_id=call_id,
            action=OperatorActionType.ADD_NOTE,
            actor_id="op-1",
            summary=f"Note {i}",
        )

    trail = await audit_logger.get_audit_trail(call_id, limit=50)
    assert len(trail) == 10
    # Last item should be Note 14
    assert trail[-1].summary == "Note 14"
