"""Unit tests for SAMVED Phase 12 Follow-up domain models."""

from datetime import datetime, timezone
import pytest

from app.followup.models import (
    ContactPreferences,
    FollowupAttempt,
    FollowupConsent,
    FollowupEvent,
    FollowupRecord,
    FollowupWorkqueueSummary,
)
from app.schemas.events import (
    ConsentState,
    ContactChannel,
    ContactResult,
    FollowupOutcome,
    FollowupPriority,
    FollowupStatus,
    FollowupType,
    RecurrenceRule,
)


def test_contact_preferences_defaults():
    prefs = ContactPreferences()
    assert prefs.preferred_channel == ContactChannel.OPERATOR_CALLBACK
    assert prefs.safe_to_contact is True
    assert prefs.human_only is True
    assert prefs.no_voicemail is False
    assert prefs.no_text is False
    assert "MON" in prefs.days_allowed


def test_followup_record_creation():
    record = FollowupRecord(
        followup_id="fol-test-01",
        case_id="case-1001",
        created_by="operator-1",
        scheduled_for="2026-09-05T18:30:00Z",
        due_at="2026-09-05T20:30:00Z",
        consent_state=ConsentState.GRANTED,
        safe_contact_window="18:00-20:00",
        channel=ContactChannel.OPERATOR_CALLBACK,
        purpose="Verify shelter intake with caller",
    )
    assert record.followup_id == "fol-test-01"
    assert record.status == FollowupStatus.DRAFT
    assert record.priority == FollowupPriority.NORMAL
    assert record.attempt_count == 0
    assert record.max_attempts == 2


def test_followup_attempt_model():
    attempt = FollowupAttempt(
        followup_id="fol-test-01",
        case_id="case-1001",
        attempt_number=1,
        operator_id="operator-1",
        channel=ContactChannel.OPERATOR_CALLBACK,
        result=ContactResult.NO_ANSWER,
        notes="No pickup after 4 rings.",
    )
    assert attempt.attempt_number == 1
    assert attempt.result == ContactResult.NO_ANSWER
    assert attempt.operator_id == "operator-1"


def test_followup_consent_model():
    consent = FollowupConsent(
        case_id="case-1001",
        consent_state=ConsentState.GRANTED,
        purpose="Shelter follow-up",
        recorded_by="operator-1",
    )
    assert consent.consent_state == ConsentState.GRANTED
    assert consent.revoked_at is None


def test_workqueue_summary_model():
    summary = FollowupWorkqueueSummary(
        total_active=5,
        due_today=3,
        overdue=1,
        blocked=1,
        completed_today=2,
    )
    assert summary.total_active == 5
    assert summary.overdue == 1
