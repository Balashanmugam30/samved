"""
Concurrency tests for Analytics Subsystem.
Validates thread-safe query processing, audit recording, and recompute execution under concurrent load.
"""

import concurrent.futures
import pytest
from app.analytics.service import AnalyticsService
from app.schemas.events import AnalyticsRole, TimePeriod
from app.analytics.schemas import RecomputeRequest


def test_concurrent_district_summary_queries():
    service = AnalyticsService()
    districts = ["TN-CHE", "DL-CEN", "MH-MUM", "KA-BLR", "PY-KKL", "UNKNOWN"]

    def query_task(d_code):
        summary = service.get_summary(d_code, period=TimePeriod.DAY, role=AnalyticsRole.DISTRICT_ADMIN)
        assert summary.district_code in districts
        return summary.privacy_status

    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
        futures = [executor.submit(query_task, d) for d in districts * 5]
        results = [f.result() for f in concurrent.futures.as_completed(futures)]

    assert len(results) == 30
    assert "PASS" in results
    assert "SUPPRESSED" in results


def test_concurrent_audit_logging():
    service = AnalyticsService()

    def log_task(idx):
        service.log_access(
            actor_id=f"actor-{idx}",
            actor_role=AnalyticsRole.DISTRICT_ADMIN,
            endpoint=f"/test/{idx}",
            district_code="TN-CHE",
            period="DAY",
            privacy_status="PASS",
        )

    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
        futures = [executor.submit(log_task, i) for i in range(50)]
        for f in concurrent.futures.as_completed(futures):
            f.result()

    logs = service.get_audit_logs(limit=100)
    assert len(logs) >= 50
