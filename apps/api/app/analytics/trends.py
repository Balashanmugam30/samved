"""
Deterministic Period-over-Period Trend Calculation.
Calculates percentage change between current and previous reporting periods.
Strictly non-predictive; never uses speculative machine learning models.
"""

from typing import Optional, Tuple
from app.schemas.events import TrendDirection

DEFAULT_TREND_THRESHOLD_PCT = 5.0  # +/- 5% change threshold for RISING/FALLING


def calculate_deterministic_trend(
    current_value: Optional[float],
    previous_value: Optional[float],
    min_cohort_size: int = 10,
    threshold_pct: float = DEFAULT_TREND_THRESHOLD_PCT,
) -> Tuple[TrendDirection, Optional[float]]:
    """
    Computes deterministic period-over-period trend:
    - If either value is None or below min_cohort_size: returns INSUFFICIENT_DATA.
    - If previous_value == 0: returns STABLE or INSUFFICIENT_DATA.
    - If pct_change >= +threshold_pct: RISING.
    - If pct_change <= -threshold_pct: FALLING.
    - Otherwise: STABLE.
    """
    if current_value is None or previous_value is None:
        return TrendDirection.INSUFFICIENT_DATA, None

    if current_value < min_cohort_size or previous_value < min_cohort_size:
        return TrendDirection.INSUFFICIENT_DATA, None

    if previous_value == 0:
        return TrendDirection.INSUFFICIENT_DATA, None

    pct_change = ((current_value - previous_value) / previous_value) * 100.0
    rounded_pct = round(pct_change, 1)

    if pct_change >= threshold_pct:
        return TrendDirection.RISING, rounded_pct
    elif pct_change <= -threshold_pct:
        return TrendDirection.FALLING, rounded_pct
    else:
        return TrendDirection.STABLE, rounded_pct
