"""
AnalyticsService singleton orchestrating Phase 13 District Intelligence.
Thread-safe in-memory precomputation, deterministic queries, suppression filters,
and audit logging.
"""

from datetime import datetime, timezone, timedelta
import threading
from typing import Any, Dict, List, Optional, Tuple

from app.schemas.events import (
    AnalyticsRole,
    DataQualityStatus,
    MetricStatus,
    ServiceCategory,
    TimePeriod,
    TrendDirection,
)
from app.analytics.dimensions import (
    DISTRICTS,
    get_district,
    list_districts,
    normalize_district,
)
from app.analytics.metrics import CATALOG_VERSION, METRIC_DEFINITIONS
from app.analytics.models import (
    AggregationJobRun,
    AnalyticsAccessLog,
    DistrictSummary,
    MetricItem,
)
from app.analytics.privacy import DEFAULT_MINIMUM_COHORT_SIZE, PrivacyEngine
from app.analytics.trends import calculate_deterministic_trend
from app.analytics.schemas import (
    AnalyticsQueryRequest,
    AnalyticsQueryResponse,
    AuditListResponse,
    DistrictSummaryResponse,
    FollowupAnalyticsResponse,
    LanguageDistributionResponse,
    OperationsAnalyticsResponse,
    RecomputeRequest,
    RecomputeResponse,
    SafetyDistributionResponse,
    ServiceDemandResponse,
    SviDistributionResponse,
    TrendPoint,
    TrendsResponse,
)


class AnalyticsService:
    def __init__(self, min_cohort_size: int = DEFAULT_MINIMUM_COHORT_SIZE):
        self._lock = threading.Lock()
        self.privacy = PrivacyEngine(min_cohort_size=min_cohort_size)
        self._audit_logs: List[AnalyticsAccessLog] = []
        self._job_runs: List[AggregationJobRun] = []
        self._data_quality_overrides: Dict[str, DataQualityStatus] = {}

    def log_access(
        self,
        actor_id: str,
        actor_role: AnalyticsRole,
        endpoint: str,
        district_code: Optional[str] = None,
        period: Optional[str] = None,
        privacy_status: str = "PASS",
    ):
        with self._lock:
            log_item = AnalyticsAccessLog(
                actor_id=actor_id,
                actor_role=actor_role,
                endpoint=endpoint,
                district_code=district_code,
                period=period,
                privacy_status=privacy_status,
            )
            self._audit_logs.append(log_item)
            # Ring buffer cap at 1000
            if len(self._audit_logs) > 1000:
                self._audit_logs.pop(0)

    def get_audit_logs(self, limit: int = 50) -> List[AnalyticsAccessLog]:
        with self._lock:
            return list(reversed(self._audit_logs[-limit:]))

    def _get_district_base_stats(self, code: str) -> Dict[str, Any]:
        """Provides deterministic seeded stats for known districts."""
        # PY-KKL is deliberately low-volume (<10) to test and verify privacy suppression
        if code == "PY-KKL":
            return {
                "calls_received": 6.0,
                "calls_completed": 5.0,
                "calls_abandoned": 1.0,
                "unique_cases": 4.0,
                "active_followups": 2.0,
                "avg_response_time": 4.2,
                "safety_escalations": 1.0,
                "avg_svi": 52.0,
                "languages": [
                    {"lang": "ta-IN", "name": "Tamil", "count": 5.0},
                    {"lang": "en-IN", "name": "English", "count": 1.0},
                ],
                "services": [
                    {"cat": ServiceCategory.COUNSELING_REFERRAL, "name": "Counseling Referral", "count": 4.0},
                    {"cat": ServiceCategory.LEGAL_INFORMATION, "name": "Legal Information", "count": 2.0},
                ],
                "safety": [
                    {"state": "NONE", "count": 3.0},
                    {"state": "WATCH", "count": 2.0},
                    {"state": "HIGH", "count": 1.0},
                ],
                "svi_bands": [
                    {"band": "LOW", "count": 1.0},
                    {"band": "MODERATE", "count": 3.0},
                    {"band": "HIGH", "count": 1.0},
                ],
                "followup_created": 3.0,
                "followup_completed": 2.0,
                "followup_missed": 1.0,
                "followup_blocked": 0.0,
                "operators_count": 2.0,
                "takeovers": 1.0,
                "handoffs_req": 1.0,
                "handoffs_conf": 1.0,
            }

        # Healthy districts with sufficient cohort size (>= 10)
        multipliers = {
            "TN-CHE": 1.0,
            "DL-CEN": 1.35,
            "MH-MUM": 1.2,
            "KA-BLR": 0.9,
            "UNKNOWN": 0.7,
        }
        m = multipliers.get(code, 1.0)

        return {
            "calls_received": round(142.0 * m),
            "calls_completed": round(128.0 * m),
            "calls_abandoned": round(14.0 * m),
            "unique_cases": round(85.0 * m),
            "active_followups": round(24.0 * m),
            "avg_response_time": 3.4,
            "safety_escalations": round(16.0 * m),
            "avg_svi": 46.5,
            "languages": [
                {"lang": "hi-IN", "name": "Hindi", "count": round(65.0 * m)},
                {"lang": "ta-IN", "name": "Tamil", "count": round(45.0 * m)},
                {"lang": "en-IN", "name": "English", "count": round(22.0 * m)},
                {"lang": "te-IN", "name": "Telugu", "count": round(10.0 * m)},
            ],
            "services": [
                {"cat": ServiceCategory.COUNSELING_REFERRAL, "name": "Counseling Referral", "count": round(52.0 * m)},
                {"cat": ServiceCategory.SAFETY_SUPPORT, "name": "Safety Support", "count": round(36.0 * m)},
                {"cat": ServiceCategory.HEALTH_SUPPORT, "name": "Health / Medical", "count": round(24.0 * m)},
                {"cat": ServiceCategory.LEGAL_INFORMATION, "name": "Legal Information", "count": round(18.0 * m)},
                {"cat": ServiceCategory.FOLLOW_UP, "name": "Follow-up Care", "count": round(12.0 * m)},
            ],
            "safety": [
                {"state": "NONE", "count": round(88.0 * m)},
                {"state": "WATCH", "count": round(26.0 * m)},
                {"state": "ELEVATED", "count": round(16.0 * m)},
                {"state": "HIGH", "count": round(9.0 * m)},
                {"state": "CRITICAL", "count": round(3.0 * m)},
            ],
            "svi_bands": [
                {"band": "LOW", "count": round(45.0 * m)},
                {"band": "MODERATE", "count": round(58.0 * m)},
                {"band": "HIGH", "count": round(27.0 * m)},
                {"band": "CRITICAL", "count": round(12.0 * m)},
            ],
            "followup_created": round(34.0 * m),
            "followup_completed": round(28.0 * m),
            "followup_missed": round(4.0 * m),
            "followup_blocked": round(2.0 * m),
            "operators_count": round(12.0 * m),
            "takeovers": round(18.0 * m),
            "handoffs_req": round(22.0 * m),
            "handoffs_conf": round(20.0 * m),
        }

    def get_summary(
        self,
        district_code: str,
        period: TimePeriod = TimePeriod.DAY,
        role: AnalyticsRole = AnalyticsRole.DISTRICT_ADMIN,
        actor_id: str = "counselor-01",
    ) -> DistrictSummaryResponse:
        canonical_code = normalize_district(district_code)
        d = get_district(canonical_code) or DISTRICTS["UNKNOWN"]

        # Role verification
        allowed, msg = self.privacy.verify_role_access(role, canonical_code)
        if not allowed:
            self.log_access(actor_id, role, f"/summary/{canonical_code}", canonical_code, period.value, "DENIED")
            raise PermissionError(msg)

        stats = self._get_district_base_stats(canonical_code)
        now_utc = datetime.now(timezone.utc)
        p_end = now_utc.isoformat()
        p_start = (now_utc - timedelta(days=1)).isoformat()

        # Check total calls cohort
        total_calls_val = stats["calls_received"]
        is_suppressed = not self.privacy.check_cohort(total_calls_val)

        # Trends (deterministic vs prior day baseline)
        trend_calls, pct_calls = calculate_deterministic_trend(total_calls_val, total_calls_val * 0.92)

        tot_calls = self.privacy.format_metric_item(
            "calls_received", total_calls_val, trend=trend_calls, trend_pct=pct_calls, period_start=p_start, period_end=p_end
        )
        comp_calls = self.privacy.format_metric_item(
            "calls_completed", stats["calls_completed"], period_start=p_start, period_end=p_end, force_suppress=is_suppressed
        )
        ab_calls = self.privacy.format_metric_item(
            "calls_abandoned", stats["calls_abandoned"], period_start=p_start, period_end=p_end, force_suppress=is_suppressed
        )
        cases = self.privacy.format_metric_item(
            "unique_case_count", stats["unique_cases"], period_start=p_start, period_end=p_end, force_suppress=is_suppressed
        )
        followups = self.privacy.format_metric_item(
            "active_followups", stats["active_followups"], period_start=p_start, period_end=p_end, force_suppress=is_suppressed
        )
        resp_time = self.privacy.format_metric_item(
            "operator_response_time_sec", stats["avg_response_time"], unit="s", status=MetricStatus.CALCULATED, period_start=p_start, period_end=p_end, force_suppress=is_suppressed
        )
        safety_esc = self.privacy.format_metric_item(
            "safety_escalations_count", stats["safety_escalations"], period_start=p_start, period_end=p_end, force_suppress=is_suppressed
        )

        quality = self._data_quality_overrides.get(canonical_code, DataQualityStatus.HEALTHY)
        priv_status = "SUPPRESSED" if is_suppressed else "PASS"

        self.log_access(actor_id, role, f"/summary/{canonical_code}", canonical_code, period.value, priv_status)

        return DistrictSummaryResponse(
            summary_id=f"sum-{canonical_code.lower()}-{period.value.lower()}",
            district_code=d.district_code,
            district_name=d.district_name,
            state_code=d.state_code,
            state_name=d.state_name,
            period=period,
            period_start=p_start,
            period_end=p_end,
            timezone="Asia/Kolkata",
            total_calls=tot_calls,
            completed_calls=comp_calls,
            abandoned_calls=ab_calls,
            unique_cases=cases,
            active_followups=followups,
            avg_response_time_sec=resp_time,
            safety_escalations_count=safety_esc,
            privacy_status=priv_status,
            data_quality_status=quality,
            metric_version=CATALOG_VERSION,
            computed_at=now_utc.isoformat(),
        )

    def get_trends(
        self,
        district_code: str,
        period: TimePeriod = TimePeriod.DAY,
        role: AnalyticsRole = AnalyticsRole.DISTRICT_ADMIN,
        actor_id: str = "counselor-01",
    ) -> TrendsResponse:
        canonical_code = normalize_district(district_code)
        allowed, msg = self.privacy.verify_role_access(role, canonical_code)
        if not allowed:
            self.log_access(actor_id, role, f"/trends/{canonical_code}", canonical_code, period.value, "DENIED")
            raise PermissionError(msg)

        stats = self._get_district_base_stats(canonical_code)
        is_suppressed = not self.privacy.check_cohort(stats["calls_received"])

        # Create 7 historical points
        points: List[TrendPoint] = []
        now = datetime.now(timezone.utc)
        base_calls = stats["calls_received"]

        # Deterministic multi-day factors
        factors = [0.85, 0.90, 0.88, 0.95, 1.02, 0.98, 1.0]
        day_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

        for i, factor in enumerate(factors):
            p_end = (now - timedelta(days=6 - i)).isoformat()
            p_start = (now - timedelta(days=7 - i)).isoformat()
            c_val = round(base_calls * factor)

            points.append(
                TrendPoint(
                    label=day_names[i],
                    period_start=p_start,
                    period_end=p_end,
                    calls_received=self.privacy.format_metric_item(
                        "calls_received", c_val, period_start=p_start, period_end=p_end, force_suppress=is_suppressed
                    ),
                    calls_completed=self.privacy.format_metric_item(
                        "calls_completed", round(c_val * 0.9), period_start=p_start, period_end=p_end, force_suppress=is_suppressed
                    ),
                    unique_cases=self.privacy.format_metric_item(
                        "unique_cases", round(c_val * 0.6), period_start=p_start, period_end=p_end, force_suppress=is_suppressed
                    ),
                    safety_escalations=self.privacy.format_metric_item(
                        "safety_escalations_count", round(c_val * 0.12), period_start=p_start, period_end=p_end, force_suppress=is_suppressed
                    ),
                )
            )

        overall_trend, trend_pct = calculate_deterministic_trend(
            base_calls, base_calls * 0.92, min_cohort_size=self.privacy.min_cohort_size
        )

        priv_status = "SUPPRESSED" if is_suppressed else "PASS"
        self.log_access(actor_id, role, f"/trends/{canonical_code}", canonical_code, period.value, priv_status)

        return TrendsResponse(
            district_code=canonical_code,
            period=period,
            points=points,
            overall_trend=overall_trend,
            overall_trend_pct=trend_pct,
            suppressed=is_suppressed,
        )

    def get_languages(
        self,
        district_code: str,
        role: AnalyticsRole = AnalyticsRole.DISTRICT_ADMIN,
        actor_id: str = "counselor-01",
    ) -> LanguageDistributionResponse:
        canonical_code = normalize_district(district_code)
        allowed, msg = self.privacy.verify_role_access(role, canonical_code)
        if not allowed:
            self.log_access(actor_id, role, f"/languages/{canonical_code}", canonical_code, "DAY", "DENIED")
            raise PermissionError(msg)

        stats = self._get_district_base_stats(canonical_code)
        raw_langs = stats["languages"]
        total_count = sum(l["count"] for l in raw_langs)

        items = []
        suppressed_count = 0
        for l in raw_langs:
            cnt = l["count"]
            supp = not self.privacy.check_cohort(cnt)
            if supp:
                suppressed_count += 1
            pct = round((cnt / total_count * 100.0), 1) if total_count > 0 else 0.0
            items.append({
                "language": l["lang"],
                "language_name": l["name"],
                "percentage": pct if not supp else 0.0,
                "count_display": "SUPPRESSED" if supp else str(int(cnt)),
                "suppressed": supp,
                "count": cnt,
            })

        # Apply complementary suppression to protect against difference attacks
        items = self.privacy.apply_complementary_suppression(items)

        now = datetime.now(timezone.utc)
        priv_status = "SUPPRESSED" if any(i["suppressed"] for i in items) else "PASS"
        self.log_access(actor_id, role, f"/languages/{canonical_code}", canonical_code, "DAY", priv_status)

        return LanguageDistributionResponse(
            district_code=canonical_code,
            period_start=(now - timedelta(days=1)).isoformat(),
            period_end=now.isoformat(),
            items=items,
            suppressed_count=suppressed_count,
            privacy_status=priv_status,
        )

    def get_services(
        self,
        district_code: str,
        role: AnalyticsRole = AnalyticsRole.DISTRICT_ADMIN,
        actor_id: str = "counselor-01",
    ) -> ServiceDemandResponse:
        canonical_code = normalize_district(district_code)
        allowed, msg = self.privacy.verify_role_access(role, canonical_code)
        if not allowed:
            self.log_access(actor_id, role, f"/services/{canonical_code}", canonical_code, "DAY", "DENIED")
            raise PermissionError(msg)

        stats = self._get_district_base_stats(canonical_code)
        raw_srv = stats["services"]
        total_count = sum(s["count"] for s in raw_srv)

        items = []
        suppressed_count = 0
        for s in raw_srv:
            cnt = s["count"]
            supp = not self.privacy.check_cohort(cnt)
            if supp:
                suppressed_count += 1
            pct = round((cnt / total_count * 100.0), 1) if total_count > 0 else 0.0
            items.append({
                "category": s["cat"].value,
                "category_name": s["name"],
                "percentage": pct if not supp else 0.0,
                "count_display": "SUPPRESSED" if supp else str(int(cnt)),
                "suppressed": supp,
                "count": cnt,
            })

        items = self.privacy.apply_complementary_suppression(items)
        now = datetime.now(timezone.utc)
        priv_status = "SUPPRESSED" if any(i["suppressed"] for i in items) else "PASS"
        self.log_access(actor_id, role, f"/services/{canonical_code}", canonical_code, "DAY", priv_status)

        return ServiceDemandResponse(
            district_code=canonical_code,
            period_start=(now - timedelta(days=1)).isoformat(),
            period_end=now.isoformat(),
            items=items,
            suppressed_count=suppressed_count,
            privacy_status=priv_status,
        )

    def get_safety(
        self,
        district_code: str,
        role: AnalyticsRole = AnalyticsRole.DISTRICT_ADMIN,
        actor_id: str = "counselor-01",
    ) -> SafetyDistributionResponse:
        canonical_code = normalize_district(district_code)
        allowed, msg = self.privacy.verify_role_access(role, canonical_code)
        if not allowed:
            self.log_access(actor_id, role, f"/safety/{canonical_code}", canonical_code, "DAY", "DENIED")
            raise PermissionError(msg)

        stats = self._get_district_base_stats(canonical_code)
        raw_safe = stats["safety"]
        total_count = sum(s["count"] for s in raw_safe)

        items = []
        suppressed_count = 0
        for s in raw_safe:
            cnt = s["count"]
            supp = not self.privacy.check_cohort(cnt)
            if supp:
                suppressed_count += 1
            pct = round((cnt / total_count * 100.0), 1) if total_count > 0 else 0.0
            items.append({
                "safety_state": s["state"],
                "percentage": pct if not supp else 0.0,
                "count_display": "SUPPRESSED" if supp else str(int(cnt)),
                "suppressed": supp,
                "count": cnt,
            })

        items = self.privacy.apply_complementary_suppression(items)
        now = datetime.now(timezone.utc)
        priv_status = "SUPPRESSED" if any(i["suppressed"] for i in items) else "PASS"
        self.log_access(actor_id, role, f"/safety/{canonical_code}", canonical_code, "DAY", priv_status)

        return SafetyDistributionResponse(
            district_code=canonical_code,
            period_start=(now - timedelta(days=1)).isoformat(),
            period_end=now.isoformat(),
            items=items,
            suppressed_count=suppressed_count,
            privacy_status=priv_status,
        )

    def get_svi(
        self,
        district_code: str,
        role: AnalyticsRole = AnalyticsRole.DISTRICT_ADMIN,
        actor_id: str = "counselor-01",
    ) -> SviDistributionResponse:
        canonical_code = normalize_district(district_code)
        allowed, msg = self.privacy.verify_role_access(role, canonical_code)
        if not allowed:
            self.log_access(actor_id, role, f"/svi/{canonical_code}", canonical_code, "DAY", "DENIED")
            raise PermissionError(msg)

        stats = self._get_district_base_stats(canonical_code)
        raw_svi = stats["svi_bands"]
        total_count = sum(s["count"] for s in raw_svi)

        items = []
        suppressed_count = 0
        for s in raw_svi:
            cnt = s["count"]
            supp = not self.privacy.check_cohort(cnt)
            if supp:
                suppressed_count += 1
            pct = round((cnt / total_count * 100.0), 1) if total_count > 0 else 0.0
            items.append({
                "band": s["band"],
                "percentage": pct if not supp else 0.0,
                "count_display": "SUPPRESSED" if supp else str(int(cnt)),
                "suppressed": supp,
                "count": cnt,
            })

        items = self.privacy.apply_complementary_suppression(items)
        now = datetime.now(timezone.utc)
        is_avg_suppressed = not self.privacy.check_cohort(total_count)
        avg_svi_item = self.privacy.format_metric_item(
            "average_svi", stats["avg_svi"], status=MetricStatus.CALCULATED, force_suppress=is_avg_suppressed
        )

        priv_status = "SUPPRESSED" if any(i["suppressed"] for i in items) else "PASS"
        self.log_access(actor_id, role, f"/svi/{canonical_code}", canonical_code, "DAY", priv_status)

        return SviDistributionResponse(
            district_code=canonical_code,
            period_start=(now - timedelta(days=1)).isoformat(),
            period_end=now.isoformat(),
            items=items,
            average_svi=avg_svi_item,
            suppressed_count=suppressed_count,
            privacy_status=priv_status,
        )

    def get_followups(
        self,
        district_code: str,
        role: AnalyticsRole = AnalyticsRole.DISTRICT_ADMIN,
        actor_id: str = "counselor-01",
    ) -> FollowupAnalyticsResponse:
        canonical_code = normalize_district(district_code)
        allowed, msg = self.privacy.verify_role_access(role, canonical_code)
        if not allowed:
            self.log_access(actor_id, role, f"/followups/{canonical_code}", canonical_code, "DAY", "DENIED")
            raise PermissionError(msg)

        stats = self._get_district_base_stats(canonical_code)
        c_created = stats["followup_created"]
        c_comp = stats["followup_completed"]
        c_miss = stats["followup_missed"]
        c_block = stats["followup_blocked"]
        total_closed = c_comp + c_miss

        is_supp = not self.privacy.check_cohort(c_created)
        comp_rate = (c_comp / total_closed * 100.0) if total_closed > 0 else 0.0
        miss_rate = (c_miss / total_closed * 100.0) if total_closed > 0 else 0.0

        now = datetime.now(timezone.utc)
        p_end = now.isoformat()
        p_start = (now - timedelta(days=1)).isoformat()

        priv_status = "SUPPRESSED" if is_supp else "PASS"
        self.log_access(actor_id, role, f"/followups/{canonical_code}", canonical_code, "DAY", priv_status)

        return FollowupAnalyticsResponse(
            district_code=canonical_code,
            period_start=p_start,
            period_end=p_end,
            created_count=self.privacy.format_metric_item("followups_created", c_created, force_suppress=is_supp),
            completed_count=self.privacy.format_metric_item("followups_completed", c_comp, force_suppress=is_supp),
            missed_count=self.privacy.format_metric_item("followups_missed", c_miss, force_suppress=is_supp),
            blocked_count=self.privacy.format_metric_item("followups_blocked", c_block, force_suppress=is_supp),
            completion_rate=self.privacy.format_metric_item(
                "followup_completion_rate", comp_rate, unit="%", status=MetricStatus.CALCULATED, force_suppress=is_supp
            ),
            missed_rate=self.privacy.format_metric_item(
                "followup_missed_rate", miss_rate, unit="%", status=MetricStatus.CALCULATED, force_suppress=is_supp
            ),
            suppressed=is_supp,
            privacy_status=priv_status,
        )

    def get_operations(
        self,
        district_code: str,
        role: AnalyticsRole = AnalyticsRole.DISTRICT_ADMIN,
        actor_id: str = "counselor-01",
    ) -> OperationsAnalyticsResponse:
        canonical_code = normalize_district(district_code)
        allowed, msg = self.privacy.verify_role_access(role, canonical_code)
        if not allowed:
            self.log_access(actor_id, role, f"/operations/{canonical_code}", canonical_code, "DAY", "DENIED")
            raise PermissionError(msg)

        stats = self._get_district_base_stats(canonical_code)
        is_supp = not self.privacy.check_cohort(stats["calls_received"])

        now = datetime.now(timezone.utc)
        p_end = now.isoformat()
        p_start = (now - timedelta(days=1)).isoformat()

        priv_status = "SUPPRESSED" if is_supp else "PASS"
        self.log_access(actor_id, role, f"/operations/{canonical_code}", canonical_code, "DAY", priv_status)

        return OperationsAnalyticsResponse(
            district_code=canonical_code,
            period_start=p_start,
            period_end=p_end,
            active_operators_count=self.privacy.format_metric_item(
                "active_operators_count", stats["operators_count"], force_suppress=is_supp
            ),
            avg_calls_per_operator=self.privacy.format_metric_item(
                "avg_calls_per_operator",
                round(stats["calls_received"] / max(stats["operators_count"], 1), 1),
                status=MetricStatus.CALCULATED,
                force_suppress=is_supp,
            ),
            takeovers_count=self.privacy.format_metric_item(
                "human_takeovers_count", stats["takeovers"], force_suppress=is_supp
            ),
            handoffs_requested=self.privacy.format_metric_item(
                "handoffs_requested", stats["handoffs_req"], force_suppress=is_supp
            ),
            handoffs_confirmed=self.privacy.format_metric_item(
                "handoffs_confirmed", stats["handoffs_conf"], force_suppress=is_supp
            ),
            median_response_time_sec=self.privacy.format_metric_item(
                "operator_response_time_sec", stats["avg_response_time"], unit="s", status=MetricStatus.CALCULATED, force_suppress=is_supp
            ),
            knowledge_queries=self.privacy.format_metric_item(
                "knowledge_queries", round(stats["calls_received"] * 1.8), force_suppress=is_supp
            ),
            system_latency_ms=self.privacy.format_metric_item(
                "system_api_latency_p95_ms", 28.0, unit="ms", status=MetricStatus.CALCULATED, force_suppress=False
            ),
            stt_failure_rate=self.privacy.format_metric_item(
                "system_stt_failure_rate", 0.4, unit="%", status=MetricStatus.CALCULATED, force_suppress=False
            ),
            suppressed=is_supp,
            privacy_status=priv_status,
        )

    def execute_query(
        self,
        query: AnalyticsQueryRequest,
        actor_id: str = "counselor-01",
    ) -> AnalyticsQueryResponse:
        target_district = query.district_code or "TN-CHE"
        summary = self.get_summary(target_district, query.period, query.role, actor_id)
        trends = self.get_trends(target_district, query.period, query.role, actor_id)
        languages = self.get_languages(target_district, query.role, actor_id)
        services = self.get_services(target_district, query.role, actor_id)
        safety = self.get_safety(target_district, query.role, actor_id)
        svi = self.get_svi(target_district, query.role, actor_id)
        followups = self.get_followups(target_district, query.role, actor_id)
        operations = self.get_operations(target_district, query.role, actor_id)

        priv_status = "SUPPRESSED" if summary.privacy_status == "SUPPRESSED" else "PASS"

        return AnalyticsQueryResponse(
            query=query,
            summary=summary,
            trends=trends,
            languages=languages,
            services=services,
            safety=safety,
            svi=svi,
            followups=followups,
            operations=operations,
            privacy_status=priv_status,
        )

    def trigger_recompute(self, req: RecomputeRequest, actor_id: str = "admin-01") -> RecomputeResponse:
        with self._lock:
            job = AggregationJobRun(
                period=req.period.value,
                source_event_count=450,
                processed_count=442,
                suppressed_count=8,
                status="COMPLETED",
                completed_at=datetime.now(timezone.utc).isoformat(),
            )
            self._job_runs.append(job)

        target_districts = [req.district_code] if req.district_code else list(DISTRICTS.keys())
        self.log_access(actor_id, AnalyticsRole.SYSTEM_ADMIN, "/recompute", req.district_code or "ALL", req.period.value, "PASS")

        return RecomputeResponse(
            job_id=job.job_id,
            status="COMPLETED",
            districts_recomputed=target_districts,
            message=f"Deterministic recomputation finished cleanly for {len(target_districts)} district(s).",
        )

    def set_data_quality_override(self, district_code: str, status: DataQualityStatus):
        with self._lock:
            self._data_quality_overrides[district_code] = status


# Global singleton instance
analytics_service = AnalyticsService()
