"""
Privacy & Suppression Engine for District Intelligence.
Enforces K-Anonymity (k >= 10), small-cell suppression, complementary suppression,
and role-based access governance.
"""

from typing import Any, Dict, List, Optional, Tuple
from app.schemas.events import AnalyticsRole, MetricStatus, TrendDirection
from app.analytics.models import MetricItem

DEFAULT_MINIMUM_COHORT_SIZE = 10


class PrivacyEngine:
    def __init__(self, min_cohort_size: int = DEFAULT_MINIMUM_COHORT_SIZE):
        self.min_cohort_size = min_cohort_size

    def check_cohort(self, count: Optional[float]) -> bool:
        """Returns True if count satisfies minimum cohort size requirement (k >= 10)."""
        if count is None:
            return False
        return count >= self.min_cohort_size

    def format_metric_item(
        self,
        metric_id: str,
        raw_count: Optional[float],
        unit: Optional[str] = None,
        trend: Optional[TrendDirection] = None,
        trend_pct: Optional[float] = None,
        period_start: str = "",
        period_end: str = "",
        force_suppress: bool = False,
        status: MetricStatus = MetricStatus.OBSERVED,
    ) -> MetricItem:
        """
        Creates a MetricItem, enforcing suppression if raw_count < min_cohort_size.
        When suppressed, raw_value is scrubbed to None, preventing PII leakage.
        """
        if force_suppress or not self.check_cohort(raw_count):
            return MetricItem(
                metric_id=metric_id,
                display_value="SUPPRESSED",
                raw_value=None,
                unit=unit,
                status=MetricStatus.SUPPRESSED,
                suppressed=True,
                trend=TrendDirection.INSUFFICIENT_DATA if trend else None,
                trend_pct=None,
                period_start=period_start,
                period_end=period_end,
            )

        # Non-suppressed formatting
        val = raw_count if raw_count is not None else 0.0
        if unit == "%":
            display = f"{val:.1f}%"
        elif unit == "s":
            display = f"{val:.1f}s"
        elif unit == "ms":
            display = f"{val:.0f}ms"
        elif val >= 1000:
            display = f"~{val/1000:.1f}K"
        else:
            display = str(int(val) if val.is_integer() else f"{val:.1f}")

        return MetricItem(
            metric_id=metric_id,
            display_value=display,
            raw_value=val,
            unit=unit,
            status=status,
            suppressed=False,
            trend=trend,
            trend_pct=trend_pct,
            period_start=period_start,
            period_end=period_end,
        )

    def apply_complementary_suppression(
        self,
        items: List[Dict[str, Any]],
        count_key: str = "count",
        suppressed_key: str = "suppressed",
        display_key: str = "count_display",
    ) -> List[Dict[str, Any]]:
        """
        Prevents difference / subtraction attacks:
        If exactly 1 cell is suppressed out of N cells and the total is known,
        an adversary could subtract the other cells from the total to derive the suppressed count.
        Therefore, we suppress a second cell (the second smallest) to preserve privacy.
        """
        if len(items) <= 1:
            return items

        suppressed_indices = [
            i for i, item in enumerate(items) if item.get(suppressed_key, False)
        ]

        # If exactly 1 cell is suppressed, find the next smallest non-suppressed cell and suppress it
        if len(suppressed_indices) == 1:
            unsuppressed = [
                (i, items[i].get(count_key, 0.0))
                for i in range(len(items))
                if i not in suppressed_indices
            ]
            if unsuppressed:
                # Sort by count ascending to pick the smallest non-suppressed
                unsuppressed.sort(key=lambda x: x[1])
                target_idx = unsuppressed[0][0]
                items[target_idx][suppressed_key] = True
                items[target_idx][display_key] = "SUPPRESSED"
                if count_key in items[target_idx]:
                    items[target_idx][count_key] = None

        return items

    @staticmethod
    def verify_role_access(
        role: AnalyticsRole,
        requested_district: str,
        user_assigned_district: Optional[str] = None,
    ) -> Tuple[bool, str]:
        """
        Validates role-based permissions for district analytics access:
        - OPERATOR: Denied macro district analytics (restricted to live call workstation).
        - SUPERVISOR: Permitted team/operational views.
        - DISTRICT_ADMIN: Permitted for their assigned district(s) or standard reporting.
        - SYSTEM_ADMIN: Permitted cross-district and national views.
        """
        if role == AnalyticsRole.OPERATOR:
            return False, "Access denied: OPERATOR role is restricted from macro district intelligence."

        if role == AnalyticsRole.DISTRICT_ADMIN:
            if user_assigned_district and user_assigned_district != requested_district and user_assigned_district != "ALL":
                return False, f"Access denied: DISTRICT_ADMIN assigned to '{user_assigned_district}' cannot access '{requested_district}'."

        return True, "Access granted."
