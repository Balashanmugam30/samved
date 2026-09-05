"""Unit tests for SAMVED Follow-up Consent Engine & Revocation Cascades."""

import pytest

from app.followup.consent import apply_consent_revocation, validate_consent_transition
from app.followup.models import FollowupRecord
from app.schemas.events import ConsentState, ContactChannel, FollowupStatus


def test_consent_transition_validation():
    # Valid transitions
    r1 = validate_consent_transition(ConsentState.UNKNOWN, ConsentState.REQUESTED)
    assert r1.valid is True

    r2 = validate_consent_transition(ConsentState.REQUESTED, ConsentState.GRANTED)
    assert r2.valid is True

    r3 = validate_consent_transition(ConsentState.GRANTED, ConsentState.REVOKED)
    assert r3.valid is True

    # Invalid transitions
    r4 = validate_consent_transition(ConsentState.UNKNOWN, ConsentState.REVOKED)
    assert r4.valid is False


def test_consent_revocation_cascade():
    f1 = FollowupRecord(
        followup_id="fol-01",
        case_id="case-1001",
        created_by="op-1",
        status=FollowupStatus.SCHEDULED,
        scheduled_for="2026-09-05T18:30:00Z",
        due_at="2026-09-05T20:30:00Z",
        consent_state=ConsentState.GRANTED,
        purpose="Verify shelter intake",
    )
    f2 = FollowupRecord(
        followup_id="fol-02",
        case_id="case-1001",
        created_by="op-1",
        status=FollowupStatus.IN_PROGRESS,
        scheduled_for="2026-09-05T18:30:00Z",
        due_at="2026-09-05T20:30:00Z",
        consent_state=ConsentState.GRANTED,
        purpose="Counselor callback",
    )
    f3 = FollowupRecord(
        followup_id="fol-03",
        case_id="case-1001",
        created_by="op-1",
        status=FollowupStatus.COMPLETED,
        scheduled_for="2026-09-05T10:00:00Z",
        due_at="2026-09-05T12:00:00Z",
        consent_state=ConsentState.GRANTED,
        purpose="Prior check-in",
    )

    all_followups = [f1, f2, f3]
    blocked, consent_rec = apply_consent_revocation(
        case_id="case-1001",
        followups=all_followups,
        reason="Caller withdrew consent during call turn 8",
        operator_id="operator-1",
    )

    assert len(blocked) == 2
    assert f1.status == FollowupStatus.BLOCKED
    assert f1.consent_state == ConsentState.REVOKED
    assert "CONSENT_REVOKED" in f1.blocked_reason

    assert f2.status == FollowupStatus.BLOCKED
    assert f2.consent_state == ConsentState.REVOKED

    # Completed task is NOT mutated into blocked
    assert f3.status == FollowupStatus.COMPLETED

    assert consent_rec.consent_state == ConsentState.REVOKED
    assert consent_rec.case_id == "case-1001"
