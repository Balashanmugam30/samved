"""
SAMVED Phase 14: Baseline & Run-to-Run Diff Engine
Detects regressions across safety, SVI, adaptive strategy, citations, latency, and findings.
"""

from typing import Any, Dict, List
from app.evaluation.models import (
    BaselineSnapshot,
    EvaluationRunRecord,
    RunDiffItem,
    RunDiffResult,
)


def compute_baseline_diff(
    baseline: BaselineSnapshot,
    current_run: EvaluationRunRecord,
) -> RunDiffResult:
    """
    Compares an evaluation run against an established baseline snapshot.
    Identifies semantic differences and flags regressions.
    """
    differences: List[RunDiffItem] = []
    has_regression = False

    b_metrics = baseline.metrics
    c_metrics = current_run.metrics

    # 1. Safety State Diff
    b_safety = b_metrics.safety.get("state", "SAFE")
    c_safety = c_metrics.safety.get("state", "SAFE")
    if b_safety != c_safety:
        # A drop in severity is a regression
        severity_rank = {"SAFE": 0, "LOW": 1, "MODERATE": 2, "HIGH": 3, "CRITICAL": 4}
        is_reg = severity_rank.get(c_safety, 0) < severity_rank.get(b_safety, 0)
        if is_reg:
            has_regression = True
        differences.append(
            RunDiffItem(
                field="safety_state",
                subsystem="safety",
                baseline_value=b_safety,
                current_value=c_safety,
                is_regression=is_reg,
                message=f"Safety state changed from {b_safety} to {c_safety} (Regression: {is_reg})",
            )
        )

    # 2. SVI Score & Band Diff
    b_svi_band = b_metrics.svi.get("band", "LOW")
    c_svi_band = c_metrics.svi.get("band", "LOW")
    b_svi_score = float(b_metrics.svi.get("score", 0.0))
    c_svi_score = float(c_metrics.svi.get("score", 0.0))

    if b_svi_band != c_svi_band:
        differences.append(
            RunDiffItem(
                field="svi_band",
                subsystem="svi",
                baseline_value=b_svi_band,
                current_value=c_svi_band,
                is_regression=False,
                message=f"SVI Band shifted from {b_svi_band} ({b_svi_score:.1f}) to {c_svi_band} ({c_svi_score:.1f})",
            )
        )

    # 3. Adaptive Policy Strategy Diff
    b_adaptive = b_metrics.adaptive.get("strategy", "PROVIDE_INFORMATION")
    c_adaptive = c_metrics.adaptive.get("strategy", "PROVIDE_INFORMATION")
    if b_adaptive != c_adaptive:
        differences.append(
            RunDiffItem(
                field="adaptive_strategy",
                subsystem="adaptive",
                baseline_value=b_adaptive,
                current_value=c_adaptive,
                is_regression=False,
                message=f"Adaptive conversational strategy changed from {b_adaptive} to {c_adaptive}",
            )
        )

    # 4. Latency SLA Diff
    b_lat = b_metrics.latency.p95_ms
    c_lat = c_metrics.latency.p95_ms
    # Flag regression if latency grew by > 50% AND > 50ms
    if c_lat > b_lat * 1.5 and c_lat > 50.0:
        has_regression = True
        differences.append(
            RunDiffItem(
                field="p95_latency_ms",
                subsystem="latency",
                baseline_value=b_lat,
                current_value=c_lat,
                is_regression=True,
                message=f"P95 latency regressed significantly from {b_lat:.1f}ms to {c_lat:.1f}ms",
            )
        )

    # 5. Overall Status Diff
    b_status = baseline.status
    c_status = current_run.evaluation_status
    if b_status == "PASS" and c_status in ["FAIL", "BLOCKED"]:
        has_regression = True
        differences.append(
            RunDiffItem(
                field="evaluation_status",
                subsystem="overall",
                baseline_value=b_status,
                current_value=c_status,
                is_regression=True,
                message=f"Overall evaluation status regressed from {b_status} to {c_status}",
            )
        )

    if not differences:
        status_label = "IDENTICAL"
    elif has_regression:
        status_label = "REGRESSED"
    elif b_status != "PASS" and c_status == "PASS":
        status_label = "IMPROVED"
    else:
        status_label = "CHANGED"

    return RunDiffResult(
        baseline_id=baseline.baseline_id,
        current_run_id=current_run.run_id,
        scenario_id=baseline.scenario_id,
        status=status_label,
        has_regression=has_regression,
        differences=differences,
    )
