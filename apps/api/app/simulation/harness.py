"""Benchmark evaluation harness for SAMVED Phase 14 Scenario Simulation Engine.

Executes synthetic scenarios through the deterministic safety engine, SVI scoring,
WER/CER speech evaluation, and profiles turn latencies.
"""

import logging
import time
from datetime import datetime, timezone
from typing import Dict, List, Optional
import uuid

from app.services.safety_engine import safety_engine
from app.services.svi_engine import svi_engine
from app.simulation.catalog import scenario_catalog
from app.simulation.metrics import calculate_wer_cer, simulate_noise_distortion
from app.simulation.models import (
    BenchmarkRun,
    BenchmarkRunStatus,
    BenchmarkSuiteType,
    ScenarioEvaluationResult,
    SimulationScenario,
    WERMetricResult,
)

logger = logging.getLogger("samved.simulation.harness")


def evaluate_single_scenario(scenario: SimulationScenario) -> ScenarioEvaluationResult:
    """Executes a single synthetic scenario through the deterministic triage pipeline."""
    caller_turns = [
        t for t in scenario.synthetic_dialogue
        if t.speaker.lower() in ("caller", "victim", "user")
    ]
    if not caller_turns:
        caller_turns = scenario.synthetic_dialogue

    fired_signals = []
    fired_trigger_names = set()
    turn_latencies: List[float] = []

    full_ref_text = []
    full_hyp_text = []

    # 1. Evaluate each turn
    for turn in caller_turns:
        start_t = time.perf_counter()

        # Distort if scenario has a noise profile
        hyp_text = simulate_noise_distortion(turn.text, scenario.noise_profile)
        full_ref_text.append(turn.text)
        full_hyp_text.append(hyp_text)

        # Evaluate safety
        assessment = safety_engine.evaluate_turn(
            utterance_text=hyp_text,
            language=turn.language or scenario.language,
            call_id=f"SIM-{scenario.scenario_id}",
            session_id=f"SESS-{scenario.scenario_id}",
        )

        for sig in assessment.signals:
            fired_signals.append(sig)
            # Map both signal_type and rule_id
            if hasattr(sig, "signal_type"):
                st = sig.signal_type.value if hasattr(sig.signal_type, "value") else str(sig.signal_type)
                fired_trigger_names.add(st)
            if hasattr(sig, "category") and sig.category:
                cat = sig.category.value if hasattr(sig.category, "value") else str(sig.category)
                fired_trigger_names.add(cat)
            if hasattr(sig, "rule_id") and sig.rule_id:
                fired_trigger_names.add(sig.rule_id)

        latency_ms = round((time.perf_counter() - start_t) * 1000.0, 2)
        turn_latencies.append(latency_ms)

    # 2. Evaluate SVI Assessment across all turns
    turns_payload = [
        {"speaker": t.speaker, "text": t.text, "language": t.language or scenario.language}
        for t in scenario.synthetic_dialogue
    ]
    svi_res = svi_engine.evaluate_session(
        call_id=f"SIM-{scenario.scenario_id}",
        session_id=f"SESS-{scenario.scenario_id}",
        turns=turns_payload,
        safety_signals=fired_signals,
    )

    actual_svi_band = svi_res.band.value if hasattr(svi_res.band, "value") else str(svi_res.band)
    actual_svi_score = float(svi_res.score)

    # 3. Compute ASR WER / CER
    ref_combined = " ".join(full_ref_text)
    hyp_combined = " ".join(full_hyp_text)
    wer_res = calculate_wer_cer(ref_combined, hyp_combined)

    # 4. Verify Deterministic Safety Triggers & Negation
    actual_triggers = sorted(list(fired_trigger_names))
    expected_triggers = scenario.expected_safety_triggers
    prohibited_triggers = scenario.prohibited_safety_triggers

    # Safety recall check
    false_negative = False
    if expected_triggers:
        for exp in expected_triggers:
            exp_clean = exp.rstrip("s").lower()
            matched = any(
                exp_clean in act.rstrip("s").lower() or act.rstrip("s").lower() in exp_clean
                for act in actual_triggers
            )
            if not matched:
                false_negative = True
                break

    # Prohibited triggers check (negation trap verification)
    negation_violated = False
    if prohibited_triggers:
        for pro in prohibited_triggers:
            pro_clean = pro.rstrip("s").lower()
            if any(
                pro_clean in act.rstrip("s").lower() or act.rstrip("s").lower() in pro_clean
                for act in actual_triggers
            ):
                negation_violated = True
                break

    # Safety recall: 1.0 if zero false negatives and no negation violation, else 0.0
    safety_recall = 1.0 if (not false_negative and not negation_violated) else 0.0

    # 5. Calibration check: band match or within expected range
    expected_mid = (scenario.expected_score_range[0] + scenario.expected_score_range[1]) / 2.0
    band_matches = (
        actual_svi_band.upper() == scenario.expected_svi_band.upper()
        or (scenario.expected_score_range[0] <= actual_svi_score <= scenario.expected_score_range[1])
        or (abs(actual_svi_score - expected_mid) <= 25.0)
    )

    # P95 latency
    sorted_latencies = sorted(turn_latencies)
    p95_lat = sorted_latencies[int(len(sorted_latencies) * 0.95)] if sorted_latencies else 0.0

    passed = (safety_recall == 1.0) and band_matches

    return ScenarioEvaluationResult(
        scenario_id=scenario.scenario_id,
        passed=passed,
        language=scenario.language,
        expected_svi_band=scenario.expected_svi_band,
        actual_svi_band=actual_svi_band,
        svi_score=actual_svi_score,
        expected_safety_triggers=expected_triggers,
        actual_safety_triggers=actual_triggers,
        safety_recall=safety_recall,
        false_negative_hazard=false_negative,
        wer_result=wer_res,
        turn_latencies_ms=turn_latencies,
        p95_latency_ms=p95_lat,
        error_message=None if passed else ("Safety trigger mismatch or band calibration error"),
    )


class BenchmarkHarness:
    """Automated benchmark test harness."""

    def run_suite(
        self,
        suite_type: BenchmarkSuiteType = BenchmarkSuiteType.SMOKE,
        custom_scenarios: Optional[List[SimulationScenario]] = None,
    ) -> BenchmarkRun:
        """Executes a benchmark suite and aggregates evaluation metrics."""
        started_at = datetime.now(timezone.utc)
        run_id = f"RUN-{uuid.uuid4().hex[:8].upper()}"

        if custom_scenarios:
            scenarios = custom_scenarios
        else:
            scenarios = scenario_catalog.get_suite(suite_type.value)

        results: List[ScenarioEvaluationResult] = []
        for sc in scenarios:
            try:
                res = evaluate_single_scenario(sc)
                results.append(res)
            except Exception as e:
                logger.error(f"Error evaluating scenario {sc.scenario_id}: {e}")
                results.append(
                    ScenarioEvaluationResult(
                        scenario_id=sc.scenario_id,
                        passed=False,
                        language=sc.language,
                        expected_svi_band=sc.expected_svi_band,
                        actual_svi_band="UNKNOWN",
                        svi_score=0.0,
                        expected_safety_triggers=sc.expected_safety_triggers,
                        actual_safety_triggers=[],
                        safety_recall=0.0,
                        false_negative_hazard=True,
                        turn_latencies_ms=[0.0],
                        p95_latency_ms=0.0,
                        error_message=str(e),
                    )
                )

        completed_at = datetime.now(timezone.utc)
        total = len(results)
        passed_count = sum(1 for r in results if r.passed)
        failed_count = total - passed_count
        pass_rate = round(passed_count / max(total, 1), 4)

        # Aggregate WER & CER
        wer_values = [r.wer_result.wer for r in results if r.wer_result]
        cer_values = [r.wer_result.cer for r in results if r.wer_result]
        mean_wer = round(sum(wer_values) / max(len(wer_values), 1), 4)
        mean_cer = round(sum(cer_values) / max(len(cer_values), 1), 4)

        # Safety recall rate
        recall_values = [r.safety_recall for r in results]
        safety_recall_rate = round(sum(recall_values) / max(len(recall_values), 1), 4)

        # SVI band accuracy
        matching_bands = sum(
            1 for r, sc in zip(results, scenarios)
            if r.actual_svi_band.upper() == sc.expected_svi_band.upper()
        )
        svi_band_accuracy = round(matching_bands / max(total, 1), 4)

        # Overall P95 latency
        all_latencies = [lat for r in results for lat in r.turn_latencies_ms]
        sorted_all = sorted(all_latencies)
        p95_lat = sorted_all[int(len(sorted_all) * 0.95)] if sorted_all else 0.0

        # Critical safety check: zero false negatives on CRITICAL band
        critical_false_negatives = any(
            r.false_negative_hazard
            for r, sc in zip(results, scenarios)
            if sc.expected_svi_band.upper() == "CRITICAL"
        )

        return BenchmarkRun(
            run_id=run_id,
            suite=suite_type,
            status=BenchmarkRunStatus.COMPLETED,
            started_at=started_at,
            completed_at=completed_at,
            total_scenarios=total,
            passed_scenarios=passed_count,
            failed_scenarios=failed_count,
            pass_rate=pass_rate,
            mean_wer=mean_wer,
            mean_cer=mean_cer,
            safety_recall_rate=safety_recall_rate,
            svi_band_accuracy=svi_band_accuracy,
            p95_latency_ms=p95_lat,
            critical_safety_passed=not critical_false_negatives,
            results=results,
        )


benchmark_harness = BenchmarkHarness()
