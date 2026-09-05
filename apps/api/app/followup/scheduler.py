"""Deterministic Scheduler for SAMVED Follow-up Workflow with TimeProvider testability."""

from datetime import datetime, timedelta, timezone
import logging
from typing import List, Optional, Protocol, Tuple

from app.followup.models import FollowupRecord
from app.schemas.events import FollowupStatus, RecurrenceRule

logger = logging.getLogger("samved.followup.scheduler")


class TimeProvider(Protocol):
    """Protocol enabling dependency injection of time for deterministic unit tests."""
    def now(self) -> datetime:
        ...


class SystemTimeProvider:
    """Standard system clock returning real UTC datetime."""
    def now(self) -> datetime:
        return datetime.now(timezone.utc)


class FrozenTimeProvider:
    """Mock time provider allowing tests to freeze and advance clock deterministically."""
    def __init__(self, initial_time: Optional[datetime] = None):
        self._current_time = initial_time or datetime(2026, 9, 5, 10, 0, 0, tzinfo=timezone.utc)

    def now(self) -> datetime:
        return self._current_time

    def set_time(self, new_time: datetime) -> None:
        if new_time.tzinfo is None:
            new_time = new_time.replace(tzinfo=timezone.utc)
        self._current_time = new_time

    def advance_minutes(self, minutes: int) -> None:
        self._current_time += timedelta(minutes=minutes)

    def advance_hours(self, hours: int) -> None:
        self._current_time += timedelta(hours=hours)

    def advance_days(self, days: int) -> None:
        self._current_time += timedelta(days=days)


class FollowupScheduler:
    """Evaluates task timelines, overdue states, ready transitions, and bounded recurrences."""

    def __init__(self, time_provider: Optional[TimeProvider] = None):
        self.time_provider = time_provider or SystemTimeProvider()

    def parse_utc(self, iso_str: str) -> datetime:
        """Parses an ISO-8601 string into a timezone-aware UTC datetime."""
        dt = datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt

    def is_within_safe_window(self, dt: datetime, safe_window: Optional[str]) -> bool:
        """Checks if a given datetime falls within the caller's safe contact window HH:MM-HH:MM."""
        if not safe_window:
            return True
        try:
            start_str, end_str = safe_window.strip().split("-")
            time_str = dt.strftime("%H:%M")
            return start_str <= time_str <= end_str
        except Exception:
            return True

    def calculate_default_due_at(self, scheduled_for_iso: str, window_hours: int = 2) -> str:
        """Calculates a sensible task deadline (scheduled_for + window_hours)."""
        dt = self.parse_utc(scheduled_for_iso)
        due_dt = dt + timedelta(hours=window_hours)
        return due_dt.isoformat()

    def evaluate_task_readiness(self, followup: FollowupRecord) -> Tuple[FollowupStatus, Optional[str]]:
        """Determines the correct temporal status for a follow-up task based on current time."""
        now = self.time_provider.now()
        scheduled_dt = self.parse_utc(followup.scheduled_for)
        due_dt = self.parse_utc(followup.due_at)

        # Non-scheduled tasks retain their status
        if followup.status not in (FollowupStatus.SCHEDULED, FollowupStatus.READY):
            return followup.status, None

        # Check if due deadline has elapsed
        if now > due_dt:
            logger.info(f"Task {followup.followup_id} deadline passed; marking MISSED.")
            return FollowupStatus.MISSED, "Task execution deadline passed without completion."

        # Check if scheduled start has arrived
        if now >= scheduled_dt:
            # Verify caller's safe window
            if self.is_within_safe_window(now, followup.safe_contact_window):
                return FollowupStatus.READY, None
            else:
                logger.info(f"Task {followup.followup_id} is due, but outside safe window {followup.safe_contact_window}.")
                return FollowupStatus.SCHEDULED, "Awaiting caller safe contact window."

        return FollowupStatus.SCHEDULED, None

    def calculate_next_recurrence(self, followup: FollowupRecord) -> Optional[Tuple[str, str]]:
        """Calculates next (scheduled_for, due_at) for bounded recurring tasks.
        
        Returns None if maximum recurrence is reached or rule is ONCE.
        """
        if not followup.recurrence or followup.recurrence == RecurrenceRule.ONCE:
            return None
        
        if followup.recurrence_count >= followup.recurrence_max:
            logger.info(f"Task {followup.followup_id} reached maximum recurrence limit ({followup.recurrence_max}).")
            return None

        current_scheduled = self.parse_utc(followup.scheduled_for)
        current_due = self.parse_utc(followup.due_at)
        delta_duration = current_due - current_scheduled

        if followup.recurrence == RecurrenceRule.DAILY:
            next_scheduled = current_scheduled + timedelta(days=1)
        elif followup.recurrence == RecurrenceRule.WEEKLY:
            next_scheduled = current_scheduled + timedelta(weeks=1)
        else:
            next_scheduled = current_scheduled + timedelta(days=1)

        next_due = next_scheduled + delta_duration
        return next_scheduled.isoformat(), next_due.isoformat()
