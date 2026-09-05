"""
FastAPI REST Router for District Intelligence & Operational Analytics (Phase 13).
Privacy-Preserving, Non-Predictive, Role-Governed.
"""

import logging
from typing import Optional
from fastapi import APIRouter, Depends, Header, HTTPException, Query, status

from app.schemas.events import AnalyticsRole, TimePeriod
from app.analytics.dimensions import list_districts, normalize_district
from app.analytics.metrics import CATALOG_VERSION, list_metric_definitions
from app.analytics.service import analytics_service
from app.analytics.schemas import (
    AnalyticsQueryRequest,
    AnalyticsQueryResponse,
    AuditListResponse,
    DistrictSummaryResponse,
    DistrictsListResponse,
    FollowupAnalyticsResponse,
    LanguageDistributionResponse,
    MetricDefinitionsListResponse,
    OperationsAnalyticsResponse,
    RecomputeRequest,
    RecomputeResponse,
    SafetyDistributionResponse,
    ServiceDemandResponse,
    SviDistributionResponse,
    TrendsResponse,
)

logger = logging.getLogger("samved.api.analytics")

router = APIRouter(prefix="", tags=["Analytics"])


def get_current_role(
    x_user_role: Optional[str] = Header(None, alias="X-User-Role"),
    role: Optional[str] = Query(None),
) -> AnalyticsRole:
    """Extracts role from X-User-Role header or query parameter, defaulting to DISTRICT_ADMIN."""
    raw = x_user_role or role or "DISTRICT_ADMIN"
    try:
        return AnalyticsRole(raw.upper())
    except ValueError:
        return AnalyticsRole.DISTRICT_ADMIN


def get_current_actor(
    x_user_id: Optional[str] = Header(None, alias="X-User-Id"),
    actor_id: Optional[str] = Query(None),
) -> str:
    return x_user_id or actor_id or "operator-tele-01"


@router.get("/status")
async def get_analytics_status():
    """Returns analytics subsystem operational status and governance parameters."""
    return {
        "status": "HEALTHY",
        "phase": "PHASE_13",
        "service": "District Intelligence & Operational Analytics",
        "catalog_version": CATALOG_VERSION,
        "reporting_timezone": "Asia/Kolkata",
        "minimum_cohort_threshold": analytics_service.privacy.min_cohort_size,
        "predictive_policing_enabled": False,
        "surveillance_mode": False,
        "trust_model": ["OBSERVED", "CALCULATED", "ESTIMATED", "SUPPRESSED", "UNAVAILABLE"],
        "governance_doctrine": "Aggregated operational analytics. Not a predictive risk score. Not for individual enforcement decisions.",
    }


@router.get("/metrics", response_model=MetricDefinitionsListResponse)
async def get_metrics_catalog():
    """Returns the complete versioned catalog of metric definitions, trust levels, and formulas."""
    metrics = list_metric_definitions()
    return MetricDefinitionsListResponse(
        metrics=metrics,
        catalog_version=CATALOG_VERSION,
        total_count=len(metrics),
    )


@router.get("/districts", response_model=DistrictsListResponse)
async def get_districts():
    """Returns the list of normalized district identifiers and state codes."""
    districts = list_districts()
    return DistrictsListResponse(
        districts=districts,
        total_count=len(districts),
    )


@router.get("/districts/{district_code}/summary", response_model=DistrictSummaryResponse)
async def get_district_summary(
    district_code: str,
    period: TimePeriod = Query(TimePeriod.DAY),
    user_role: AnalyticsRole = Depends(get_current_role),
    actor_id: str = Depends(get_current_actor),
):
    """Retrieves aggregated operational summary and KPI metrics for a district."""
    try:
        return analytics_service.get_summary(district_code, period, user_role, actor_id)
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))


@router.get("/districts/{district_code}/trends", response_model=TrendsResponse)
async def get_district_trends(
    district_code: str,
    period: TimePeriod = Query(TimePeriod.DAY),
    user_role: AnalyticsRole = Depends(get_current_role),
    actor_id: str = Depends(get_current_actor),
):
    """Retrieves deterministic period-over-period trend points for a district."""
    try:
        return analytics_service.get_trends(district_code, period, user_role, actor_id)
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))


@router.get("/districts/{district_code}/languages", response_model=LanguageDistributionResponse)
async def get_district_languages(
    district_code: str,
    user_role: AnalyticsRole = Depends(get_current_role),
    actor_id: str = Depends(get_current_actor),
):
    """Retrieves language demand distribution with small-cell and complementary suppression."""
    try:
        return analytics_service.get_languages(district_code, user_role, actor_id)
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))


@router.get("/districts/{district_code}/services", response_model=ServiceDemandResponse)
async def get_district_services(
    district_code: str,
    user_role: AnalyticsRole = Depends(get_current_role),
    actor_id: str = Depends(get_current_actor),
):
    """Retrieves standardized service category demand distribution."""
    try:
        return analytics_service.get_services(district_code, user_role, actor_id)
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))


@router.get("/districts/{district_code}/safety", response_model=SafetyDistributionResponse)
async def get_district_safety(
    district_code: str,
    user_role: AnalyticsRole = Depends(get_current_role),
    actor_id: str = Depends(get_current_actor),
):
    """Retrieves safety state distribution percentages."""
    try:
        return analytics_service.get_safety(district_code, user_role, actor_id)
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))


@router.get("/districts/{district_code}/svi", response_model=SviDistributionResponse)
async def get_district_svi(
    district_code: str,
    user_role: AnalyticsRole = Depends(get_current_role),
    actor_id: str = Depends(get_current_actor),
):
    """Retrieves SVI severity band distribution and average SVI score."""
    try:
        return analytics_service.get_svi(district_code, user_role, actor_id)
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))


@router.get("/districts/{district_code}/followups", response_model=FollowupAnalyticsResponse)
async def get_district_followups(
    district_code: str,
    user_role: AnalyticsRole = Depends(get_current_role),
    actor_id: str = Depends(get_current_actor),
):
    """Retrieves follow-up care continuity workload, completion rates, and missed contact counts."""
    try:
        return analytics_service.get_followups(district_code, user_role, actor_id)
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))


@router.get("/districts/{district_code}/operations", response_model=OperationsAnalyticsResponse)
async def get_district_operations(
    district_code: str,
    user_role: AnalyticsRole = Depends(get_current_role),
    actor_id: str = Depends(get_current_actor),
):
    """Retrieves counselor workload, handoffs, median response times, and system reliability metrics."""
    try:
        return analytics_service.get_operations(district_code, user_role, actor_id)
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))


@router.post("/query", response_model=AnalyticsQueryResponse)
async def query_analytics(
    query: AnalyticsQueryRequest,
    user_role: AnalyticsRole = Depends(get_current_role),
    actor_id: str = Depends(get_current_actor),
):
    """Executes a composite analytics query across multiple dimensions with boundary checks."""
    try:
        query.role = user_role
        return analytics_service.execute_query(query, actor_id)
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))


@router.post("/recompute", response_model=RecomputeResponse)
async def recompute_analytics(
    request: RecomputeRequest,
    user_role: AnalyticsRole = Depends(get_current_role),
    actor_id: str = Depends(get_current_actor),
):
    """Triggers deterministic batch recomputation for a district or period (System Admin / Supervisor only)."""
    if user_role not in [AnalyticsRole.SYSTEM_ADMIN, AnalyticsRole.SUPERVISOR]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: Only SYSTEM_ADMIN or SUPERVISOR can trigger recomputations.",
        )
    return analytics_service.trigger_recompute(request, actor_id)


@router.get("/audit", response_model=AuditListResponse)
async def get_analytics_audit(
    limit: int = Query(50, ge=1, le=200),
    user_role: AnalyticsRole = Depends(get_current_role),
    actor_id: str = Depends(get_current_actor),
):
    """Retrieves immutable audit trail of analytics dashboard access."""
    if user_role not in [AnalyticsRole.SYSTEM_ADMIN, AnalyticsRole.SUPERVISOR]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: Audit log is restricted to SUPERVISOR and SYSTEM_ADMIN roles.",
        )
    logs = analytics_service.get_audit_logs(limit)
    return AuditListResponse(logs=logs, total_count=len(logs))
