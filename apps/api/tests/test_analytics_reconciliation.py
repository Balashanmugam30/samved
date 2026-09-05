"""
Reconciliation & Data Quality tests for Analytics Subsystem.
Validates event tracking, exclusion reconciliation, and quality indicator flags.
"""

import pytest
from app.analytics.aggregation import EventAggregator
from app.analytics.service import AnalyticsService
from app.schemas.events import AnalyticsRole, DataQualityStatus


def test_reconciliation_event_counts():
    aggregator = EventAggregator()
    # 50 unique events
    for i in range(50):
        assert aggregator.register_event(f"call-evt-{i}") is True
    # 5 duplicate events
    for i in range(5):
        assert aggregator.register_event(f"call-evt-{i}") is False

    assert aggregator._processed_event_count == 50
    assert aggregator._excluded_event_count == 5
    # Total attempts = 55, excluded = 5 (9%) -> DEGRADED
    assert aggregator.get_data_quality_status() == DataQualityStatus.DEGRADED


def test_data_quality_override_surfaces_in_summary():
    service = AnalyticsService()
    service.set_data_quality_override("TN-CHE", DataQualityStatus.DEGRADED)
    summary = service.get_summary("TN-CHE", role=AnalyticsRole.DISTRICT_ADMIN)
    assert summary.data_quality_status == DataQualityStatus.DEGRADED

    # Reset
    service.set_data_quality_override("TN-CHE", DataQualityStatus.HEALTHY)
    summary_healthy = service.get_summary("TN-CHE", role=AnalyticsRole.DISTRICT_ADMIN)
    assert summary_healthy.data_quality_status == DataQualityStatus.HEALTHY
