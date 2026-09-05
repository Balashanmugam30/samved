"""Unit tests for SAMVED Phase 12 Follow-up Policy Engine."""

import pytest

from app.followup.models import ContactPreferences, FollowupRecord
from app.followup.policy import (
    check_duplicate_followup,
    check_max_attempts,
    check_safety_precedence,
    validate_consent_for_channel,
    validate_purpose,
    validate_safe_contact_window,
)
from app.schemas.events import ConsentState, ContactChannel, FollowupPriority, FollowupStatus


def test_purpose_validation():
    # Valid explicit purpose
    d1 = validate_purpose("Check on caller intake at regional shelter")
    assert d1.allowed is True

    # Empty
    d2 = validate_purpose("")
    assert d2.allowed is False
    assert d2.reason_code == "PURPOSE_EMPTY"

    # Too short
    d3 = validate_purpose("hi")
    assert d3.allowed is False
    assert d3.reason_code == "PURPOSE_TOO_SHORT"

    # Too vague
    d4 = validate_purpose("check caller")
    assert d4.allowed is False
    assert d4.reason_code == "PURPOSE_TOO_VAGUE"


def test_consent_for_channel_validation():
    prefs = ContactPreferences(safe_to_contact=True)

    # Granted allows operator callback
    d1 = validate_consent_for_channel(ConsentState.GRANTED, ContactChannel.OPERATOR_CALLBACK, prefs)
    assert d1.allowed is True

    # Unknown blocks external callback
    d2 = validate_consent_for_channel(ConsentState.UNKNOWN, ContactChannel.OPERATOR_CALLBACK, prefs)
    assert d2.allowed is False
    assert d2.reason_code == "INSUFFICIENT_CONSENT"

    # Refused blocks external callback
    d3 = validate_consent_for_channel(ConsentState.REFUSED, ContactChannel.OPERATOR_CALLBACK, prefs)
    assert d3.allowed is False
    assert d3.reason_code == "CONSENT_REFUSED"

    # Revoked blocks external callback
    d4 = validate_consent_for_channel(ConsentState.REVOKED, ContactChannel.OPERATOR_CALLBACK, prefs)
    assert d4.allowed is False
    assert d4.reason_code == "CONSENT_REVOKED"

    # Internal task does not require caller consent
    d5 = validate_consent_for_channel(ConsentState.UNKNOWN, ContactChannel.INTERNAL_TASK, prefs)
    assert d5.allowed is True


def test_safe_contact_window_validation():
    # Valid window and scheduled time within window
    d1 = validate_safe_contact_window("18:00-20:00", "2026-09-05T18:30:00Z")
    assert d1.allowed is True

    # Time outside window
    d2 = validate_safe_contact_window("18:00-20:00", "2026-09-05T14:30:00Z")
    assert d2.allowed is False
    assert d2.reason_code == "OUTSIDE_SAFE_WINDOW"

    # Invalid window format
    d3 = validate_safe_contact_window("evening", "2026-09-05T18:30:00Z")
    assert d3.allowed is False
    assert d3.reason_code == "INVALID_WINDOW_FORMAT"


def test_duplicate_followup_detection():
    existing = [
        FollowupRecord(
            followup_id="fol-01",
            case_id="case-1001",
            created_by="op-1",
            status=FollowupStatus.SCHEDULED,
            scheduled_for="2026-09-05T18:30:00Z",
            due_at="2026-09-05T20:30:00Z",
            channel=ContactChannel.OPERATOR_CALLBACK,
            purpose="Verify shelter intake",
        )
    ]

    # Duplicate purpose and channel on same case
    d1 = check_duplicate_followup("case-1001", "Verify shelter intake", ContactChannel.OPERATOR_CALLBACK, existing)
    assert d1.allowed is False
    assert d1.reason_code == "DUPLICATE_FOLLOW_UP"

    # Different purpose allowed
    d2 = check_duplicate_followup("case-1001", "Review medical report", ContactChannel.OPERATOR_CALLBACK, existing)
    assert d2.allowed is True


def test_max_attempts_cap():
    f = FollowupRecord(
        followup_id="fol-01",
        case_id="case-1001",
        created_by="op-1",
        scheduled_for="2026-09-05T18:30:00Z",
        due_at="2026-09-05T20:30:00Z",
        attempt_count=2,
        max_attempts=2,
        purpose="Verify shelter intake",
    )
    d = check_max_attempts(f)
    assert d.allowed is False
    assert d.reason_code == "MAX_ATTEMPTS_EXCEEDED"


def test_safety_precedence_policy():
    # Critical safety with normal priority rejected
    d1 = check_safety_precedence("CRITICAL", FollowupPriority.NORMAL)
    assert d1.allowed is False
    assert d1.reason_code == "CRITICAL_SAFETY_PRIORITY_REQUIRED"

    # Critical safety with HIGH priority allowed
    d2 = check_safety_precedence("CRITICAL", FollowupPriority.HIGH)
    assert d2.allowed is True
