"""Unit tests for SAMVED Phase 12 Follow-up Scheduler with FrozenTimeProvider."""

from datetime import datetime, timezone
import pytest

from app.followup.models import FollowupRecord
from app.followup.scheduler import FollowupScheduler, FrozenTimeProvider
from app.schemas.events import FollowupStatus, RecurrenceRule


def test_frozen_time_provider_advancement():
    start = datetime(2026, 9, 5, 10, 0, 0, tzinfo=timezone.utc)
    clock = FrozenTimeProvider(start)
    assert clock.now() == start

    clock.advance_minutes(30)
    assert clock.now() == datetime(2026, 9, 5, 10, 30, 0, tzinfo=timezone.utc)

    clock.advance_hours(2)
    assert clock.now() == datetime(2026, 9, 5, 12, 30, 0, tzinfo=timezone.utc)


def test_scheduler_readiness_evaluation():
    # Freeze time at 10:00
    clock = FrozenTimeProvider(datetime(2026, 9, 5, 10, 0, 0, tzinfo=timezone.utc))
    scheduler = FollowupScheduler(time_provider=clock)

    f = FollowupRecord(
        followup_id="fol-01",
        case_id="case-1001",
        created_by="op-1",
        status=FollowupStatus.SCHEDULED,
        scheduled_for="2026-09-05T11:00:00Z",
        due_at="2026-09-05T13:00:00Z",
        safe_contact_window="10:00-14:00",
        purpose="Verify shelter intake",
    )

    # At 10:00 (before 11:00 scheduled), status is still SCHEDULED
    st1, _ = scheduler.evaluate_task_readiness(f)
    assert st1 == FollowupStatus.SCHEDULED

    # Advance clock by 60 minutes to 11:00 -> becomes READY
    clock.advance_minutes(60)
    st2, _ = scheduler.evaluate_task_readiness(f)
    assert st2 == FollowupStatus.READY

    # Advance clock by 150 minutes to 13:30 (past 13:00 due date) -> becomes MISSED
    clock.advance_minutes(150)
    st3, reason = scheduler.evaluate_task_readiness(f)
    assert st3 == FollowupStatus.MISSED
    assert "deadline" in reason.lower()


def test_safe_contact_window_delay():
    # Clock at 11:00, task scheduled at 11:00, but safe window is 18:00-20:00
    clock = FrozenTimeProvider(datetime(2026, 9, 5, 11, 0, 0, tzinfo=timezone.utc))
    scheduler = FollowupScheduler(time_provider=clock)

    f = FollowupRecord(
        followup_id="fol-01",
        case_id="case-1001",
        created_by="op-1",
        status=FollowupStatus.SCHEDULED,
        scheduled_for="2026-09-05T11:00:00Z",
        due_at="2026-09-05T21:00:00Z",
        safe_contact_window="18:00-20:00",
        purpose="Evening safe callback",
    )

    # At 11:00, outside window -> remains SCHEDULED awaiting window
    st, reason = scheduler.evaluate_task_readiness(f)
    assert st == FollowupStatus.SCHEDULED
    assert "safe contact window" in reason.lower()

    # Advance clock to 18:30 (inside safe window) -> becomes READY
    clock.set_time(datetime(2026, 9, 5, 18, 30, 0, tzinfo=timezone.utc))
    st2, _ = scheduler.evaluate_task_readiness(f)
    assert st2 == FollowupStatus.READY


def test_bounded_recurrence_calculation():
    clock = FrozenTimeProvider(datetime(2026, 9, 5, 10, 0, 0, tzinfo=timezone.utc))
    scheduler = FollowupScheduler(time_provider=clock)

    f = FollowupRecord(
        followup_id="fol-01",
        case_id="case-1001",
        created_by="op-1",
        status=FollowupStatus.COMPLETED,
        scheduled_for="2026-09-05T10:00:00Z",
        due_at="2026-09-05T12:00:00Z",
        recurrence=RecurrenceRule.DAILY,
        recurrence_max=2,
        recurrence_count=0,
        purpose="Daily check-in",
    )

    next_times = scheduler.calculate_next_recurrence(f)
    assert next_times is not None
    next_sched, next_due = next_times
    assert next_sched.startswith("2026-09-06T10:00:00")
    assert next_due.startswith("2026-09-06T12:00:00")

    # If recurrence max reached, return None
    f.recurrence_count = 2
    assert scheduler.calculate_next_recurrence(f) is None
