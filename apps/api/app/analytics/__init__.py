"""
SAMVED Phase 13 — District Intelligence & Operational Analytics Subsystem.
Privacy-Preserving, Explainable, Non-Predictive, Human-Supervised.
"""

from app.analytics.service import AnalyticsService, analytics_service
from app.analytics.privacy import PrivacyEngine
from app.analytics.dimensions import normalize_district, get_district, list_districts
from app.analytics.metrics import METRIC_DEFINITIONS, CATALOG_VERSION

__all__ = [
    "AnalyticsService",
    "analytics_service",
    "PrivacyEngine",
    "normalize_district",
    "get_district",
    "list_districts",
    "METRIC_DEFINITIONS",
    "CATALOG_VERSION",
]
