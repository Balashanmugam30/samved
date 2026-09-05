"""
Unit tests for Deterministic Period-over-Period Trend Calculations.
Validates RISING, FALLING, STABLE, and INSUFFICIENT_DATA outcomes based on exact percentage thresholds.
"""

import pytest
from app.analytics.trends import calculate_deterministic_trend
from app.schemas.events import TrendDirection


def test_trend_rising():
    # 120 vs 100 -> +20.0% -> RISING
    direction, pct = calculate_deterministic_trend(120.0, 100.0)
    assert direction == TrendDirection.RISING
    assert pct == 20.0


def test_trend_falling():
    # 80 vs 100 -> -20.0% -> FALLING
    direction, pct = calculate_deterministic_trend(80.0, 100.0)
    assert direction == TrendDirection.FALLING
    assert pct == -20.0


def test_trend_stable():
    # 102 vs 100 -> +2.0% -> STABLE
    direction, pct = calculate_deterministic_trend(102.0, 100.0)
    assert direction == TrendDirection.STABLE
    assert pct == 2.0


def test_trend_insufficient_data_due_to_small_cohort():
    # Current value is 6 (< 10)
    direction, pct = calculate_deterministic_trend(6.0, 20.0, min_cohort_size=10)
    assert direction == TrendDirection.INSUFFICIENT_DATA
    assert pct is None

    # Previous value is 5 (< 10)
    direction, pct = calculate_deterministic_trend(30.0, 5.0, min_cohort_size=10)
    assert direction == TrendDirection.INSUFFICIENT_DATA
    assert pct is None


def test_trend_zero_previous_value():
    direction, pct = calculate_deterministic_trend(25.0, 0.0)
    assert direction == TrendDirection.INSUFFICIENT_DATA
    assert pct is None
