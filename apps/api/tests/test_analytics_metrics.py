"""
Unit tests for Versioned Metric Catalog.
Validates metric definitions, trust levels, mathematical formulas, and event linkages.
"""

import pytest
from app.analytics.metrics import (
    CATALOG_VERSION,
    METRIC_DEFINITIONS,
    get_metric_definition,
    list_metric_definitions,
)
from app.schemas.events import MetricStatus


def test_catalog_version():
    assert CATALOG_VERSION == "v1.0.0"


def test_required_metrics_present():
    required = [
        "calls_received",
        "calls_completed",
        "calls_abandoned",
        "unique_case_count",
        "safety_state_distribution",
        "safety_escalations_count",
        "average_svi",
        "svi_band_distribution",
        "calls_by_language",
        "service_category_demand",
        "human_takeovers_count",
        "operator_response_time_sec",
        "active_followups",
        "followup_completion_rate",
        "knowledge_queries",
        "system_stt_failure_rate",
        "system_api_latency_p95_ms",
    ]
    for m in required:
        defn = get_metric_definition(m)
        assert defn is not None, f"Metric '{m}' missing from catalog"
        assert len(defn.definition) > 10
        assert len(defn.calculation_method) > 0
        assert defn.status in [MetricStatus.OBSERVED, MetricStatus.CALCULATED, MetricStatus.ESTIMATED]


def test_no_predictive_danger_metrics_in_catalog():
    # Verify strict non-predictive governance: no danger/risk scores or offender predictions
    for m_id, defn in METRIC_DEFINITIONS.items():
        assert "danger" not in m_id.lower()
        assert "offender" not in m_id.lower()
        assert "predict" not in m_id.lower()
        assert "crime" not in m_id.lower()


def test_list_metric_definitions():
    all_metrics = list_metric_definitions()
    assert len(all_metrics) >= 15
    assert all(isinstance(m.metric_id, str) for m in all_metrics)
