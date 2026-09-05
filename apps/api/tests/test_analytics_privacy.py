"""
Unit tests for Privacy & Suppression Engine.
Validates K-Anonymity (k >= 10), raw count scrubbing, and complementary suppression.
"""

import pytest
from app.analytics.privacy import PrivacyEngine
from app.schemas.events import AnalyticsRole, MetricStatus


def test_cohort_threshold_check():
    engine = PrivacyEngine(min_cohort_size=10)
    assert engine.check_cohort(9.9) is False
    assert engine.check_cohort(10.0) is True
    assert engine.check_cohort(15.0) is True
    assert engine.check_cohort(None) is False


def test_metric_item_scrubbing_under_k():
    engine = PrivacyEngine(min_cohort_size=10)
    item = engine.format_metric_item("calls_received", 4.0)
    assert item.suppressed is True
    assert item.display_value == "SUPPRESSED"
    assert item.raw_value is None
    assert item.status == MetricStatus.SUPPRESSED


def test_metric_item_formatting_above_k():
    engine = PrivacyEngine(min_cohort_size=10)
    item = engine.format_metric_item("calls_received", 142.0)
    assert item.suppressed is False
    assert item.display_value == "142"
    assert item.raw_value == 142.0


def test_display_rounding_for_thousands():
    engine = PrivacyEngine(min_cohort_size=10)
    item = engine.format_metric_item("calls_received", 1240.0)
    assert item.suppressed is False
    assert item.display_value == "~1.2K"


def test_complementary_suppression_difference_attack():
    engine = PrivacyEngine(min_cohort_size=10)
    # 3 categories: A=20 (ok), B=15 (ok), C=4 (suppressed < 10)
    items = [
        {"name": "Cat A", "count": 20.0, "suppressed": False, "count_display": "20"},
        {"name": "Cat B", "count": 15.0, "suppressed": False, "count_display": "15"},
        {"name": "Cat C", "count": 4.0, "suppressed": True, "count_display": "SUPPRESSED"},
    ]
    # Because exactly 1 cell is suppressed, complementary suppression should suppress Cat B (the next smallest)
    processed = engine.apply_complementary_suppression(items)
    suppressed_count = sum(1 for i in processed if i["suppressed"])
    assert suppressed_count == 2
    assert processed[1]["suppressed"] is True
    assert processed[1]["count_display"] == "SUPPRESSED"
    assert processed[1]["count"] is None
