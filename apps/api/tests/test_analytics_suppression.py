"""
Unit tests specifically validating small-cell suppression behavior and privacy guarantees.
Ensures zero PII leakage when querying low-cohort districts.
"""

import pytest
from app.analytics.service import AnalyticsService
from app.schemas.events import AnalyticsRole, MetricStatus


def test_small_cell_district_suppressed_kpis():
    service = AnalyticsService(min_cohort_size=10)
    # PY-KKL is seeded with 6 calls (< 10)
    summary = service.get_summary("PY-KKL", role=AnalyticsRole.DISTRICT_ADMIN)

    assert summary.privacy_status == "SUPPRESSED"
    assert summary.total_calls.suppressed is True
    assert summary.total_calls.display_value == "SUPPRESSED"
    assert summary.total_calls.raw_value is None

    assert summary.completed_calls.suppressed is True
    assert summary.completed_calls.display_value == "SUPPRESSED"
    assert summary.completed_calls.raw_value is None

    assert summary.unique_cases.suppressed is True
    assert summary.active_followups.suppressed is True


def test_healthy_district_not_suppressed():
    service = AnalyticsService(min_cohort_size=10)
    # TN-CHE is seeded with 142 calls (>= 10)
    summary = service.get_summary("TN-CHE", role=AnalyticsRole.DISTRICT_ADMIN)

    assert summary.privacy_status == "PASS"
    assert summary.total_calls.suppressed is False
    assert summary.total_calls.display_value == "142"
    assert summary.total_calls.raw_value == 142.0
    assert summary.unique_cases.suppressed is False


def test_small_cell_trends_suppression():
    service = AnalyticsService(min_cohort_size=10)
    trends = service.get_trends("PY-KKL", role=AnalyticsRole.DISTRICT_ADMIN)
    assert trends.suppressed is True
    for pt in trends.points:
        assert pt.calls_received.suppressed is True
        assert pt.calls_received.display_value == "SUPPRESSED"
