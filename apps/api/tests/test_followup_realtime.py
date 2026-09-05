"""Realtime WebSocket event tests for SAMVED Follow-up Subsystem."""

import pytest

from app.followup.events import create_followup_event
from app.followup.models import FollowupAttempt, FollowupRecord
from app.schemas.events import ConsentState, ContactChannel, ContactResult, EventType, FollowupStatus


def test_create_followup_event_envelope():
    record = FollowupRecord(
        followup_id="fol-evt-01",
        case_id="case-1001",
        call_id="call-evt-01",
        created_by="op-evt",
        status=FollowupStatus.SCHEDULED,
        scheduled_for="2026-09-05T18:30:00Z",
        due_at="2026-09-05T20:30:00Z",
        consent_state=ConsentState.GRANTED,
        purpose="Verify shelter intake",
    )

    envelope = create_followup_event(
        EventType.FOLLOWUP_SCHEDULED,
        record,
        actor_id="op-evt",
        reason="Scheduled task",
    )

    assert envelope.event_type == EventType.FOLLOWUP_SCHEDULED
    assert envelope.case_id == "case-1001"
    assert envelope.call_id == "call-evt-01"
    assert envelope.payload["followup_id"] == "fol-evt-01"
    assert envelope.payload["status"] == "SCHEDULED"


def test_create_followup_attempt_event_envelope():
    record = FollowupRecord(
        followup_id="fol-evt-02",
        case_id="case-1001",
        created_by="op-evt",
        status=FollowupStatus.IN_PROGRESS,
        scheduled_for="2026-09-05T18:30:00Z",
        due_at="2026-09-05T20:30:00Z",
        consent_state=ConsentState.GRANTED,
        purpose="Verify shelter intake",
    )
    attempt = FollowupAttempt(
        followup_id="fol-evt-02",
        case_id="case-1001",
        attempt_number=1,
        operator_id="op-evt",
        channel=ContactChannel.OPERATOR_CALLBACK,
        result=ContactResult.NO_ANSWER,
        notes="No answer",
    )

    envelope = create_followup_event(
        EventType.FOLLOWUP_ATTEMPT_RECORDED,
        record,
        actor_id="op-evt",
        attempt=attempt,
    )

    assert envelope.event_type == EventType.FOLLOWUP_ATTEMPT_RECORDED
    assert "attempt" in envelope.payload
    assert envelope.payload["attempt"]["attempt_number"] == 1
    assert envelope.payload["attempt"]["result"] == "NO_ANSWER"
