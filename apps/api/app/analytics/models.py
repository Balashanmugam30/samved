"""
SAMVED Phase 13 — District Intelligence & Operational Analytics Domain Models.
Privacy-Preserving, Explainable, Non-Predictive, Human-Supervised.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
import uuid
from pydantic import BaseModel, Field

from app.schemas.events import (
    DataQualityStatus,
    MetricStatus,
    TimePeriod,
    TrendDirection,
    AnalyticsRole,
    ServiceCategory,
)


class District(BaseModel):
    district_code: str
    district_name: str
    state_code: str
    state_name: str
    aliases: List[str] = Field(default_factory=list)


class State(BaseModel):
    state_code: str
    state_name: str
    districts: List[str] = Field(default_factory=list)


class MetricDefinition(BaseModel):
    metric_id: str
    metric_version: str = "v1.0.0"
    name: str
    category: str
    definition: str
    calculation_method: str
    status: MetricStatus = MetricStatus.OBSERVED
    privacy_level: str = "AGGREGATE"
    source_event_types: List[str] = Field(default_factory=list)


class MetricItem(BaseModel):
    metric_id: str
    metric_version: str = "v1.0.0"
    display_value: str
    raw_value: Optional[float] = None
    unit: Optional[str] = None
    status: MetricStatus = MetricStatus.OBSERVED
    suppressed: bool = False
    trend: Optional[TrendDirection] = None
    trend_pct: Optional[float] = None
    period_start: str
    period_end: str


class DistrictSummary(BaseModel):
    summary_id: str = Field(default_factory=lambda: f"sum-{uuid.uuid4().hex[:8]}")
    district_code: str
    district_name: str
    state_code: str
    state_name: str
    period: TimePeriod = TimePeriod.DAY
    period_start: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    period_end: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
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
    computed_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class LanguageDistribution(BaseModel):
    language: str
    language_name: str
    percentage: float
    count_display: str
    suppressed: bool = False


class ServiceDemand(BaseModel):
    category: ServiceCategory
    category_name: str
    percentage: float
    count_display: str
    suppressed: bool = False


class SafetyDistribution(BaseModel):
    safety_state: str
    percentage: float
    count_display: str
    suppressed: bool = False


class SviDistribution(BaseModel):
    band: str
    percentage: float
    count_display: str
    suppressed: bool = False


class AnalyticsAccessLog(BaseModel):
    audit_id: str = Field(default_factory=lambda: f"aud-{uuid.uuid4().hex[:8]}")
    actor_id: str
    actor_role: AnalyticsRole
    endpoint: str
    district_code: Optional[str] = None
    period: Optional[str] = None
    privacy_status: str = "PASS"
    accessed_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class AggregationJobRun(BaseModel):
    job_id: str = Field(default_factory=lambda: f"job-{uuid.uuid4().hex[:8]}")
    metric_version: str = "v1.0.0"
    period: str
    started_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    completed_at: Optional[str] = None
    status: str = "RUNNING"
    source_event_count: int = 0
    processed_count: int = 0
    suppressed_count: int = 0
    error_count: int = 0
