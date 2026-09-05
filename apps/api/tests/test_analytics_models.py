"""
Unit tests for Analytics Domain Models.
Validates Pydantic schemas, field validations, and trust classification enum mappings.
"""

import pytest
from app.analytics.models import District, State, MetricDefinition, MetricItem, DistrictSummary
from app.schemas.events import MetricStatus, TimePeriod, TrendDirection, DataQualityStatus


def test_district_model_instantiation():
    d = District(
        district_code="TN-CHE",
        district_name="Chennai",
        state_code="TN",
        state_name="Tamil Nadu",
        aliases=["chennai", "madras"],
    )
    assert d.district_code == "TN-CHE"
    assert "madras" in d.aliases


def test_metric_definition_defaults():
    defn = MetricDefinition(
        metric_id="test_metric",
        name="Test Metric",
        category="VOLUME",
        definition="Test definition",
        calculation_method="COUNT(*)",
    )
    assert defn.metric_version == "v1.0.0"
    assert defn.status == MetricStatus.OBSERVED
    assert defn.privacy_level == "AGGREGATE"


def test_metric_item_suppressed_state():
    item = MetricItem(
        metric_id="calls_received",
        display_value="SUPPRESSED",
        raw_value=None,
        status=MetricStatus.SUPPRESSED,
        suppressed=True,
        period_start="2026-09-01T00:00:00Z",
        period_end="2026-09-01T23:59:59Z",
    )
    assert item.suppressed is True
    assert item.raw_value is None
    assert item.display_value == "SUPPRESSED"


def test_district_summary_creation():
    item = MetricItem(
        metric_id="dummy",
        display_value="50",
        raw_value=50.0,
        status=MetricStatus.OBSERVED,
        suppressed=False,
        period_start="2026-09-01T00:00:00Z",
        period_end="2026-09-01T23:59:59Z",
    )
    summary = DistrictSummary(
        district_code="DL-CEN",
        district_name="Central Delhi",
        state_code="DL",
        state_name="Delhi",
        total_calls=item,
        completed_calls=item,
        abandoned_calls=item,
        unique_cases=item,
        active_followups=item,
        avg_response_time_sec=item,
        safety_escalations_count=item,
    )
    assert summary.district_code == "DL-CEN"
    assert summary.timezone == "Asia/Kolkata"
    assert summary.data_quality_status == DataQualityStatus.HEALTHY
