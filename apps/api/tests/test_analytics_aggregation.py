"""
Unit tests for Event Aggregation & Deduplication Engine.
Validates duplicate event exclusion, data quality thresholds, and late event handling.
"""

import pytest
from app.analytics.aggregation import EventAggregator
from app.schemas.events import DataQualityStatus
from app.analytics.dimensions import normalize_district


def test_event_deduplication():
    aggregator = EventAggregator()
    # First time seeing event
    assert aggregator.register_event("evt-1001") is True
    # Duplicate event
    assert aggregator.register_event("evt-1001") is False
    assert aggregator._excluded_event_count == 1
    assert aggregator._processed_event_count == 1


def test_data_quality_status_thresholds():
    aggregator = EventAggregator()
    # No events -> HEALTHY
    assert aggregator.get_data_quality_status() == DataQualityStatus.HEALTHY

    # Add 100 valid events
    for i in range(100):
        aggregator.register_event(f"evt-{i}")
    assert aggregator.get_data_quality_status() == DataQualityStatus.HEALTHY

    # Add 10 duplicates (10 / 110 ~ 9% -> DEGRADED)
    for i in range(10):
        aggregator.register_event("evt-0")
    assert aggregator.get_data_quality_status() == DataQualityStatus.DEGRADED

    # Add 40 more duplicates (50 / 150 ~ 33% -> INCOMPLETE)
    for i in range(40):
        aggregator.register_event("evt-0")
    assert aggregator.get_data_quality_status() == DataQualityStatus.INCOMPLETE


def test_district_normalization_in_aggregation():
    assert normalize_district("Chennai") == "TN-CHE"
    assert normalize_district("Madras") == "TN-CHE"
    assert normalize_district("New Delhi") == "DL-CEN"
    assert normalize_district("Mumbai City") == "MH-MUM"
    assert normalize_district("Bangalore Urban") == "KA-BLR"
    assert normalize_district("Karaikal") == "PY-KKL"
    assert normalize_district("Unknown") == "UNKNOWN"
    assert normalize_district(None) == "UNKNOWN"
    assert normalize_district("Random Unmapped Town") == "UNKNOWN"
