"""
Versioned Metric Catalog for District Intelligence & Operational Analytics.
Catalog Version: v1.0.0.
Every metric carries an explicit trust classification (OBSERVED, CALCULATED, ESTIMATED, SUPPRESSED, UNAVAILABLE).
"""

from typing import Dict, List, Optional
from app.analytics.models import MetricDefinition
from app.schemas.events import MetricStatus

CATALOG_VERSION = "v1.0.0"

METRIC_DEFINITIONS: Dict[str, MetricDefinition] = {
    # 1. Volume Metrics
    "calls_received": MetricDefinition(
        metric_id="calls_received",
        metric_version=CATALOG_VERSION,
        name="Calls Received",
        category="VOLUME",
        definition="Total number of initiated telephony call sessions in the reporting period.",
        calculation_method="COUNT(CALL_STARTED events)",
        status=MetricStatus.OBSERVED,
        privacy_level="AGGREGATE",
        source_event_types=["CALL_STARTED"],
    ),
    "calls_completed": MetricDefinition(
        metric_id="calls_completed",
        metric_version=CATALOG_VERSION,
        name="Calls Completed",
        category="VOLUME",
        definition="Number of telephony call sessions that completed triage and closed naturally.",
        calculation_method="COUNT(CALL_ENDED events WHERE reason != 'ABANDONED')",
        status=MetricStatus.OBSERVED,
        privacy_level="AGGREGATE",
        source_event_types=["CALL_ENDED"],
    ),
    "calls_abandoned": MetricDefinition(
        metric_id="calls_abandoned",
        metric_version=CATALOG_VERSION,
        name="Calls Abandoned",
        category="VOLUME",
        definition="Calls disconnected before completing initial triage.",
        calculation_method="COUNT(CALL_ENDED events WHERE duration < 10s)",
        status=MetricStatus.OBSERVED,
        privacy_level="AGGREGATE",
        source_event_types=["CALL_ENDED"],
    ),
    "unique_case_count": MetricDefinition(
        metric_id="unique_case_count",
        metric_version=CATALOG_VERSION,
        name="Unique Cases",
        category="VOLUME",
        definition="Distinct case records active or created within the district in the reporting period.",
        calculation_method="COUNT(DISTINCT case_id)",
        status=MetricStatus.OBSERVED,
        privacy_level="AGGREGATE",
        source_event_types=["CASE_CREATED", "CASE_UPDATED"],
    ),

    # 2. Safety State Distribution
    "safety_state_distribution": MetricDefinition(
        metric_id="safety_state_distribution",
        metric_version=CATALOG_VERSION,
        name="Safety State Distribution",
        category="SAFETY",
        definition="Percentage of calls in each deterministic safety band (NONE, WATCH, ELEVATED, HIGH, CRITICAL).",
        calculation_method="COUNT(band) / TOTAL * 100.0",
        status=MetricStatus.CALCULATED,
        privacy_level="AGGREGATE",
        source_event_types=["SAFETY_STATE_UPDATED", "SAFETY_SIGNAL"],
    ),
    "safety_escalations_count": MetricDefinition(
        metric_id="safety_escalations_count",
        metric_version=CATALOG_VERSION,
        name="Safety Escalations",
        category="SAFETY",
        definition="Number of calls requiring supervisor/counselor safety escalation intervention.",
        calculation_method="COUNT(SAFETY_STATE_UPDATED WHERE state IN ('HIGH', 'CRITICAL'))",
        status=MetricStatus.OBSERVED,
        privacy_level="AGGREGATE",
        source_event_types=["SAFETY_STATE_UPDATED"],
    ),

    # 3. SVI Metrics
    "average_svi": MetricDefinition(
        metric_id="average_svi",
        metric_version=CATALOG_VERSION,
        name="Average SVI Score",
        category="SVI",
        definition="Average Stress Vulnerability Index (0–100) across evaluated calls.",
        calculation_method="AVG(svi_score)",
        status=MetricStatus.CALCULATED,
        privacy_level="AGGREGATE",
        source_event_types=["SVI_UPDATED"],
    ),
    "svi_band_distribution": MetricDefinition(
        metric_id="svi_band_distribution",
        metric_version=CATALOG_VERSION,
        name="SVI Band Distribution",
        category="SVI",
        definition="Percentage of evaluated cases in Low (0–25), Moderate (26–50), High (51–75), and Critical (76–100) bands.",
        calculation_method="COUNT(svi_band) / TOTAL * 100.0",
        status=MetricStatus.CALCULATED,
        privacy_level="AGGREGATE",
        source_event_types=["SVI_UPDATED"],
    ),

    # 4. Multilingual Demand
    "calls_by_language": MetricDefinition(
        metric_id="calls_by_language",
        metric_version=CATALOG_VERSION,
        name="Language Mix Demand",
        category="LANGUAGE",
        definition="Percentage of calls conducted in each detected language (Hindi, Tamil, English, etc.).",
        calculation_method="COUNT(language) / TOTAL * 100.0",
        status=MetricStatus.OBSERVED,
        privacy_level="AGGREGATE",
        source_event_types=["LANGUAGE_DETECTED", "LANGUAGE_CHANGED"],
    ),

    # 5. Service Category Demand
    "service_category_demand": MetricDefinition(
        metric_id="service_category_demand",
        metric_version=CATALOG_VERSION,
        name="Service Category Demand",
        category="SERVICES",
        definition="Distribution of primary caller requests across standardized support categories.",
        calculation_method="COUNT(category) / TOTAL * 100.0",
        status=MetricStatus.CALCULATED,
        privacy_level="AGGREGATE",
        source_event_types=["CASE_ENTITY_CREATED", "FOLLOWUP_CREATED"],
    ),

    # 6. Operator Workload & Response Time
    "human_takeovers_count": MetricDefinition(
        metric_id="human_takeovers_count",
        metric_version=CATALOG_VERSION,
        name="Human Takeovers",
        category="OPERATOR",
        definition="Number of calls where human tele-counselor assumed manual call control.",
        calculation_method="COUNT(OPERATOR_TAKEOVER events)",
        status=MetricStatus.OBSERVED,
        privacy_level="AGGREGATE",
        source_event_types=["OPERATOR_TAKEOVER"],
    ),
    "operator_response_time_sec": MetricDefinition(
        metric_id="operator_response_time_sec",
        metric_version=CATALOG_VERSION,
        name="Average Operator Response Time",
        category="OPERATOR",
        definition="Median elapsed seconds from call connection to human operator note/action.",
        calculation_method="MEDIAN(operator_action_timestamp - call_connect_timestamp)",
        status=MetricStatus.CALCULATED,
        privacy_level="AGGREGATE",
        source_event_types=["CALL_CONNECTED", "OPERATOR_NOTE_ADDED", "OPERATOR_TAKEOVER"],
    ),

    # 7. Follow-up Workload & Continuity
    "active_followups": MetricDefinition(
        metric_id="active_followups",
        metric_version=CATALOG_VERSION,
        name="Active Follow-ups",
        category="FOLLOWUP",
        definition="Current scheduled, due, or in-progress care continuity tasks in district.",
        calculation_method="COUNT(followups WHERE status IN ('SCHEDULED', 'DUE', 'IN_PROGRESS'))",
        status=MetricStatus.OBSERVED,
        privacy_level="AGGREGATE",
        source_event_types=["FOLLOWUP_CREATED", "FOLLOWUP_SCHEDULED", "FOLLOWUP_COMPLETED"],
    ),
    "followup_completion_rate": MetricDefinition(
        metric_id="followup_completion_rate",
        metric_version=CATALOG_VERSION,
        name="Follow-up Completion Rate",
        category="FOLLOWUP",
        definition="Percentage of closed follow-up tasks successfully completed by counselor.",
        calculation_method="COMPLETED / (COMPLETED + MISSED + CANCELLED) * 100.0",
        status=MetricStatus.CALCULATED,
        privacy_level="AGGREGATE",
        source_event_types=["FOLLOWUP_COMPLETED", "FOLLOWUP_MISSED", "FOLLOWUP_CANCELLED"],
    ),

    # 8. Knowledge Demand
    "knowledge_queries": MetricDefinition(
        metric_id="knowledge_queries",
        metric_version=CATALOG_VERSION,
        name="Knowledge Grounding Queries",
        category="KNOWLEDGE",
        definition="Total statutory and scheme RAG searches executed to support call triage.",
        calculation_method="COUNT(KNOWLEDGE_SEARCH_COMPLETED events)",
        status=MetricStatus.OBSERVED,
        privacy_level="AGGREGATE",
        source_event_types=["KNOWLEDGE_SEARCH_COMPLETED"],
    ),

    # 9. System Health & Operational Reliability
    "system_stt_failure_rate": MetricDefinition(
        metric_id="system_stt_failure_rate",
        metric_version=CATALOG_VERSION,
        name="STT Failure Rate",
        category="SYSTEM",
        definition="Percentage of speech recognition turns experiencing streaming errors.",
        calculation_method="COUNT(STT_ERROR) / TOTAL_TURNS * 100.0",
        status=MetricStatus.CALCULATED,
        privacy_level="AGGREGATE",
        source_event_types=["STT_ERROR"],
    ),
    "system_api_latency_p95_ms": MetricDefinition(
        metric_id="system_api_latency_p95_ms",
        metric_version=CATALOG_VERSION,
        name="P95 API Latency",
        category="SYSTEM",
        definition="95th percentile response latency for REST and WebSocket gateway turns.",
        calculation_method="PERCENTILE_95(turn_latency_ms)",
        status=MetricStatus.CALCULATED,
        privacy_level="AGGREGATE",
        source_event_types=["TURN_LATENCY"],
    ),
}


def get_metric_definition(metric_id: str) -> Optional[MetricDefinition]:
    return METRIC_DEFINITIONS.get(metric_id)


def list_metric_definitions() -> List[MetricDefinition]:
    return list(METRIC_DEFINITIONS.values())
