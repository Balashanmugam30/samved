"""
Deterministic Event Aggregation & Data Quality Engine.
Deduplicates events by event_id, tracks late-arriving events,
and reconciles counts against data quality indicators.
"""

from typing import Any, Dict, List, Optional, Set
from datetime import datetime, timezone

from app.schemas.events import DataQualityStatus
from app.analytics.dimensions import normalize_district


class EventAggregator:
    def __init__(self):
        self._seen_event_ids: Set[str] = set()
        self._excluded_event_count: int = 0
        self._processed_event_count: int = 0

    def is_duplicate(self, event_id: str) -> bool:
        """Returns True if the event has already been processed in this aggregation cycle."""
        return event_id in self._seen_event_ids

    def register_event(self, event_id: str) -> bool:
        """
        Attempts to register an event.
        Returns False if duplicate (excluded), True if newly registered.
        """
        if event_id in self._seen_event_ids:
            self._excluded_event_count += 1
            return False
        self._seen_event_ids.add(event_id)
        self._processed_event_count += 1
        return True

    def get_data_quality_status(self) -> DataQualityStatus:
        """
        Determines data quality status based on excluded/dropped ratio:
        - HEALTHY: < 5% excluded
        - DEGRADED: 5% - 20% excluded
        - INCOMPLETE: > 20% excluded
        """
        total = self._processed_event_count + self._excluded_event_count
        if total == 0:
            return DataQualityStatus.HEALTHY

        ratio = self._excluded_event_count / total
        if ratio > 0.20:
            return DataQualityStatus.INCOMPLETE
        elif ratio > 0.05:
            return DataQualityStatus.DEGRADED
        return DataQualityStatus.HEALTHY

    def reset(self):
        """Clears seen event cache for new aggregation batch."""
        self._seen_event_ids.clear()
        self._excluded_event_count = 0
        self._processed_event_count = 0
