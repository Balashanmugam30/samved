"""
Pydantic Schemas for REST API endpoints of District Intelligence.
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from app.schemas.events import (
    AnalyticsRole,
    DataQualityStatus,
    MetricStatus,
    ServiceCategory,
    TimePeriod,
    TrendDirection,
)
from app.analytics.models import District, MetricDefinition, MetricItem, AnalyticsAccessLog


class DistrictSummaryResponse(BaseModel):
    summary_id: str
    district_code: str
    district_name: str
    state_code: str
    state_name: str
    period: TimePeriod
    period_start: str
    period_end: str
    timezone: str = "Asia/Kolkata"
    total_calls: MetricItem
    completed_calls: MetricItem
    abandoned_calls: MetricItem
    unique_cases: MetricItem
    active_followups: MetricItem
    avg_response_time_sec: MetricItem
    safety_escalations_count: MetricItem
    privacy_status: str = "PASS"
    data_quality_status: DataQualityStatus = DataQualityStatus.HEALTHY
    metric_version: str = "v1.0.0"
    computed_at: str


class DistrictsListResponse(BaseModel):
    districts: List[District]
    total_count: int


class MetricDefinitionsListResponse(BaseModel):
    metrics: List[MetricDefinition]
    catalog_version: str
    total_count: int


class TrendPoint(BaseModel):
    label: str
    period_start: str
    period_end: str
    calls_received: MetricItem
    calls_completed: MetricItem
    unique_cases: MetricItem
    safety_escalations: MetricItem


class TrendsResponse(BaseModel):
    district_code: str
    period: TimePeriod
    points: List[TrendPoint]
    overall_trend: TrendDirection
    overall_trend_pct: Optional[float] = None
    suppressed: bool = False


class LanguageDistributionResponse(BaseModel):
    district_code: str
    period_start: str
    period_end: str
    items: List[Dict[str, Any]]
    suppressed_count: int = 0
    privacy_status: str = "PASS"


class ServiceDemandResponse(BaseModel):
    district_code: str
    period_start: str
    period_end: str
    items: List[Dict[str, Any]]
    suppressed_count: int = 0
    privacy_status: str = "PASS"


class SafetyDistributionResponse(BaseModel):
    district_code: str
    period_start: str
    period_end: str
    items: List[Dict[str, Any]]
    suppressed_count: int = 0
    privacy_status: str = "PASS"


class SviDistributionResponse(BaseModel):
    district_code: str
    period_start: str
    period_end: str
    items: List[Dict[str, Any]]
    average_svi: MetricItem
    suppressed_count: int = 0
    privacy_status: str = "PASS"


class FollowupAnalyticsResponse(BaseModel):
    district_code: str
    period_start: str
    period_end: str
    created_count: MetricItem
    completed_count: MetricItem
    missed_count: MetricItem
    blocked_count: MetricItem
    completion_rate: MetricItem
    missed_rate: MetricItem
    suppressed: bool = False
    privacy_status: str = "PASS"


class OperationsAnalyticsResponse(BaseModel):
    district_code: str
    period_start: str
    period_end: str
    active_operators_count: MetricItem
    avg_calls_per_operator: MetricItem
    takeovers_count: MetricItem
    handoffs_requested: MetricItem
    handoffs_confirmed: MetricItem
    median_response_time_sec: MetricItem
    knowledge_queries: MetricItem
    system_latency_ms: MetricItem
    stt_failure_rate: MetricItem
    suppressed: bool = False
    privacy_status: str = "PASS"


class AnalyticsQueryRequest(BaseModel):
    district_code: Optional[str] = None
    state_code: Optional[str] = None
    period: TimePeriod = TimePeriod.DAY
    start_date: str
    end_date: str
    language: Optional[str] = None
    service_category: Optional[ServiceCategory] = None
    role: AnalyticsRole = AnalyticsRole.DISTRICT_ADMIN


class AnalyticsQueryResponse(BaseModel):
    query: AnalyticsQueryRequest
    summary: DistrictSummaryResponse
    trends: TrendsResponse
    languages: LanguageDistributionResponse
    services: ServiceDemandResponse
    safety: SafetyDistributionResponse
    svi: SviDistributionResponse
    followups: FollowupAnalyticsResponse
    operations: OperationsAnalyticsResponse
    privacy_status: str = "PASS"


class RecomputeRequest(BaseModel):
    district_code: Optional[str] = None
    period: TimePeriod = TimePeriod.DAY
    start_date: str
    end_date: str


class RecomputeResponse(BaseModel):
    job_id: str
    status: str
    districts_recomputed: List[str]
    message: str


class AuditListResponse(BaseModel):
    logs: List[AnalyticsAccessLog]
    total_count: int
