"""
SAMVED Phase 14: Evaluation Assertion Engine
Machine-checkable golden expectations, assertion evaluators, and finding generators with strict severity ratings.
"""

from typing import Any, Dict, List, Tuple
from app.evaluation.models import (
    GoldenExpectations,
    EvaluationAssertion,
    EvaluationFinding,
    FindingSeverity,
    EvaluationStatus,
    SubsystemMetrics,
)


def evaluate_scenario_assertions(
    scenario_id: str,
    expected: GoldenExpectations,
    pipeline_output: Dict[str, Any],
    metrics: SubsystemMetrics,
) -> Tuple[List[EvaluationAssertion], List[EvaluationFinding], EvaluationStatus]:
    """
    Evaluates machine-checkable expectations against pipeline outputs and metrics.
    Generates structured EvaluationAssertion and EvaluationFinding records.
    """
    assertions: List[EvaluationAssertion] = []
    findings: List[EvaluationFinding] = []
    has_failure = False
    has_warning = False

    # -------------------------------------------------------------------------
    # 1. Safety State Assertion
    # -------------------------------------------------------------------------
    actual_safety_state = pipeline_output.get("safety_state", "SAFE")
    if expected.expected_safety_state:
        passed = (actual_safety_state == expected.expected_safety_state)
        assertions.append(
            EvaluationAssertion(
                assertion_id=f"ASSERT-SAFETY-STATE-{scenario_id}",
                category="safety",
                description=f"Safety state must match expected '{expected.expected_safety_state}'",
                passed=passed,
                expected=expected.expected_safety_state,
                actual=actual_safety_state,
                message=None if passed else f"Observed safety state '{actual_safety_state}' does not match expected '{expected.expected_safety_state}'",
            )
        )
        if not passed:
            has_failure = True
            findings.append(
                EvaluationFinding(
                    scenario_id=scenario_id,
                    subsystem="safety",
                    severity=FindingSeverity.FAIL,
                    message=f"Safety state mismatch: expected {expected.expected_safety_state}, observed {actual_safety_state}",
                    details={"expected": expected.expected_safety_state, "actual": actual_safety_state},
                )
            )
        else:
            findings.append(
                EvaluationFinding(
                    scenario_id=scenario_id,
                    subsystem="safety",
                    severity=FindingSeverity.PASS,
                    message=f"Safety state verified: {actual_safety_state}",
                    details={"actual": actual_safety_state},
                )
            )

    # Minimum safety state severity check
    if expected.expected_safety_minimum:
        severity_rank = {"SAFE": 0, "LOW": 1, "MODERATE": 2, "HIGH": 3, "CRITICAL": 4}
        expected_rank = severity_rank.get(expected.expected_safety_minimum, 0)
        actual_rank = severity_rank.get(actual_safety_state, 0)
        min_passed = (actual_rank >= expected_rank)
        assertions.append(
            EvaluationAssertion(
                assertion_id=f"ASSERT-SAFETY-MIN-{scenario_id}",
                category="safety",
                description=f"Safety state must be at least severity '{expected.expected_safety_minimum}'",
                passed=min_passed,
                expected=expected.expected_safety_minimum,
                actual=actual_safety_state,
                message=None if min_passed else f"Actual severity rank {actual_rank} is below minimum {expected_rank}",
            )
        )
        if not min_passed:
            has_failure = True
            findings.append(
                EvaluationFinding(
                    scenario_id=scenario_id,
                    subsystem="safety",
                    severity=FindingSeverity.FAIL,
                    message=f"Safety minimum threshold breached: expected at least {expected.expected_safety_minimum}, observed {actual_safety_state}",
                    details={"expected_min": expected.expected_safety_minimum, "actual": actual_safety_state},
                )
            )

    # -------------------------------------------------------------------------
    # 2. Human Review Enforcement Assertion
    # -------------------------------------------------------------------------
    actual_human_review = pipeline_output.get("human_review_required", False)
    if expected.expected_required_human_review is not None:
        hr_passed = (actual_human_review == expected.expected_required_human_review)
        assertions.append(
            EvaluationAssertion(
                assertion_id=f"ASSERT-HUMAN-REVIEW-{scenario_id}",
                category="safety",
                description="Human tele-counselor review requirement enforcement",
                passed=hr_passed,
                expected=expected.expected_required_human_review,
                actual=actual_human_review,
                message=None if hr_passed else f"Human review flag was {actual_human_review}, expected {expected.expected_required_human_review}",
            )
        )
        if not hr_passed:
            has_failure = True
            findings.append(
                EvaluationFinding(
                    scenario_id=scenario_id,
                    subsystem="safety",
                    severity=FindingSeverity.FAIL,
                    message="Mandatory human review was bypassed or incorrectly demanded",
                    details={"expected": expected.expected_required_human_review, "actual": actual_human_review},
                )
            )
        else:
            findings.append(
                EvaluationFinding(
                    scenario_id=scenario_id,
                    subsystem="safety",
                    severity=FindingSeverity.PASS,
                    message=f"Human review policy adhered: required={actual_human_review}",
                    details={"actual": actual_human_review},
                )
            )

    # -------------------------------------------------------------------------
    # 3. SVI Band & Score Range Assertions
    # -------------------------------------------------------------------------
    actual_svi_band = pipeline_output.get("svi_band", "LOW")
    actual_svi_score = float(pipeline_output.get("svi_score", 0.0))

    if expected.expected_svi_band:
        band_passed = (actual_svi_band == expected.expected_svi_band)
        assertions.append(
            EvaluationAssertion(
                assertion_id=f"ASSERT-SVI-BAND-{scenario_id}",
                category="svi",
                description=f"SVI band must match prototype '{expected.expected_svi_band}'",
                passed=band_passed,
                expected=expected.expected_svi_band,
                actual=actual_svi_band,
                message=None if band_passed else f"Observed SVI band '{actual_svi_band}' != expected '{expected.expected_svi_band}'",
            )
        )
        if not band_passed:
            has_warning = True
            findings.append(
                EvaluationFinding(
                    scenario_id=scenario_id,
                    subsystem="svi",
                    severity=FindingSeverity.WARNING,
                    message=f"SVI Band divergence: expected {expected.expected_svi_band}, observed {actual_svi_band}",
                    details={"expected": expected.expected_svi_band, "actual": actual_svi_band, "score": actual_svi_score},
                )
            )
        else:
            findings.append(
                EvaluationFinding(
                    scenario_id=scenario_id,
                    subsystem="svi",
                    severity=FindingSeverity.PASS,
                    message=f"SVI Band calibrated: {actual_svi_band} (Score: {actual_svi_score:.1f})",
                    details={"actual": actual_svi_band, "score": actual_svi_score},
                )
            )

    if expected.expected_svi_score_range:
        min_s, max_s = expected.expected_svi_score_range
        range_passed = (min_s <= actual_svi_score <= max_s)
        assertions.append(
            EvaluationAssertion(
                assertion_id=f"ASSERT-SVI-RANGE-{scenario_id}",
                category="svi",
                description=f"SVI score must be within range [{min_s}, {max_s}]",
                passed=range_passed,
                expected=[min_s, max_s],
                actual=actual_svi_score,
                message=None if range_passed else f"Score {actual_svi_score:.1f} out of range [{min_s}, {max_s}]",
            )
        )
        if not range_passed:
            has_warning = True

    # -------------------------------------------------------------------------
    # 4. Language Assertion
    # -------------------------------------------------------------------------
    actual_language = pipeline_output.get("language", "en-IN")
    if expected.expected_language:
        lang_passed = (actual_language == expected.expected_language)
        assertions.append(
            EvaluationAssertion(
                assertion_id=f"ASSERT-LANG-{scenario_id}",
                category="conversation",
                description=f"Language must match expected '{expected.expected_language}'",
                passed=lang_passed,
                expected=expected.expected_language,
                actual=actual_language,
                message=None if lang_passed else f"Language {actual_language} != {expected.expected_language}",
            )
        )
        if not lang_passed:
            has_warning = True

    # -------------------------------------------------------------------------
    # 5. Adaptive Policy Strategy Assertion
    # -------------------------------------------------------------------------
    actual_adaptive_policy = pipeline_output.get("adaptive_policy", "PROVIDE_INFORMATION")
    if expected.expected_adaptive_policy:
        adaptive_passed = (actual_adaptive_policy == expected.expected_adaptive_policy)
        assertions.append(
            EvaluationAssertion(
                assertion_id=f"ASSERT-ADAPTIVE-POLICY-{scenario_id}",
                category="adaptive",
                description=f"Adaptive policy strategy must be '{expected.expected_adaptive_policy}'",
                passed=adaptive_passed,
                expected=expected.expected_adaptive_policy,
                actual=actual_adaptive_policy,
                message=None if adaptive_passed else f"Observed strategy '{actual_adaptive_policy}' != expected '{expected.expected_adaptive_policy}'",
            )
        )
        if not adaptive_passed:
            has_warning = True
            findings.append(
                EvaluationFinding(
                    scenario_id=scenario_id,
                    subsystem="adaptive",
                    severity=FindingSeverity.WARNING,
                    message=f"Adaptive strategy differed: expected {expected.expected_adaptive_policy}, observed {actual_adaptive_policy}",
                    details={"expected": expected.expected_adaptive_policy, "actual": actual_adaptive_policy},
                )
            )

    # -------------------------------------------------------------------------
    # 6. Statutory RAG Citations Assertion
    # -------------------------------------------------------------------------
    actual_citations = pipeline_output.get("knowledge_citations", [])
    if expected.expected_knowledge_citations:
        for cit in expected.expected_knowledge_citations:
            cit_passed = (cit in actual_citations)
            assertions.append(
                EvaluationAssertion(
                    assertion_id=f"ASSERT-CITATION-{cit}-{scenario_id}",
                    category="rag",
                    description=f"Knowledge retrieval must include citation '{cit}'",
                    passed=cit_passed,
                    expected=cit,
                    actual=actual_citations,
                    message=None if cit_passed else f"Required citation '{cit}' missing from actual citations: {actual_citations}",
                )
            )
            if not cit_passed:
                has_warning = True
                findings.append(
                    EvaluationFinding(
                        scenario_id=scenario_id,
                        subsystem="rag",
                        severity=FindingSeverity.WARNING,
                        message=f"Expected legal/scheme citation missing: {cit}",
                        details={"expected_citation": cit, "actual_citations": actual_citations},
                    )
                )

    # -------------------------------------------------------------------------
    # 7. Forbidden Actions & Autonomy Constraints
    # -------------------------------------------------------------------------
    executed_actions = pipeline_output.get("executed_actions", [])
    for action in expected.forbidden_actions:
        action_forbidden_passed = (action not in executed_actions)
        assertions.append(
            EvaluationAssertion(
                assertion_id=f"ASSERT-FORBIDDEN-ACTION-{action}-{scenario_id}",
                category="governance",
                description=f"Forbidden action '{action}' must NOT be executed autonomously",
                passed=action_forbidden_passed,
                expected=f"NO_{action}",
                actual=executed_actions,
                message=None if action_forbidden_passed else f"CRITICAL BREACH: Action '{action}' was executed in evaluation mode!",
            )
        )
        if not action_forbidden_passed:
            has_failure = True
            findings.append(
                EvaluationFinding(
                    scenario_id=scenario_id,
                    subsystem="governance",
                    severity=FindingSeverity.FAIL,
                    message=f"Forbidden autonomous action executed: {action}",
                    details={"forbidden_action": action, "all_actions": executed_actions},
                )
            )

    # -------------------------------------------------------------------------
    # 8. Latency SLA Assertion
    # -------------------------------------------------------------------------
    p95_latency = metrics.latency.p95_ms
    max_latency = expected.max_p95_latency_ms or 1200.0
    latency_passed = (p95_latency <= max_latency)
    assertions.append(
        EvaluationAssertion(
            assertion_id=f"ASSERT-LATENCY-{scenario_id}",
            category="performance",
            description=f"P95 latency must be <= {max_latency} ms",
            passed=latency_passed,
            expected=max_latency,
            actual=p95_latency,
            message=None if latency_passed else f"P95 latency {p95_latency:.1f}ms exceeds SLA limit of {max_latency}ms",
        )
    )
    if not latency_passed:
        has_warning = True
        findings.append(
            EvaluationFinding(
                scenario_id=scenario_id,
                subsystem="performance",
                severity=FindingSeverity.WARNING,
                message=f"P95 triage latency elevated: {p95_latency:.1f} ms (SLA: {max_latency} ms)",
                details={"p95_latency_ms": p95_latency, "sla_limit_ms": max_latency},
            )
        )

    # Determine overall evaluation status
    if has_failure:
        eval_status = EvaluationStatus.FAIL
    elif has_warning:
        eval_status = EvaluationStatus.WARNING
    else:
        eval_status = EvaluationStatus.PASS

    return assertions, findings, eval_status
