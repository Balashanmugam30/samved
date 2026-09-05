# SAMVED — Evaluation Lab Testing & Verification Guide (Phase 14)

This document details the automated unit, integration, and E2E verification suites covering the Phase 14 Scenario Simulator & Evaluation Lab.

---

## 1. Backend Pytest Suites (30 Dedicated Tests)

The backend evaluation test suite verifies contract compliance, replay determinism, safety guarantees, subsystem telemetry collection, baseline snapshots, regression detection, and REST API routes.

Execute with:
```bash
apps/api/.venv/Scripts/pytest apps/api/tests/test_evaluation_*.py -v
```

### 1.1 `tests/test_evaluation_schema.py` (6 Tests)
- `test_evaluation_enums`: Verifies `EvaluationMode`, `FindingSeverity`, `EvaluationStatus`, and `FaultType` enums match contracts.
- `test_caller_profile_and_turn_models`: Validates caller persona fields, speech attributes, and multi-turn expectations.
- `test_golden_expectations_model`: Checks machine-checkable expectation constraints (`expected_safety_state`, `expected_svi_band`, `max_latency_p95_ms`).
- `test_evaluation_assertion_model`: Validates schema for individual assertion outcomes.
- `test_subsystem_metrics_model`: Confirms serialization of safety, SVI, adaptive, acoustic, orchestration, RAG, case, and follow-up telemetry.
- `test_baseline_and_diff_models`: Verifies baseline snapshot and run diff models.

### 1.2 `tests/test_evaluation_engine.py` (3 Tests)
- `test_corpus_scenarios_loaded`: Confirms all 19 calibrated benchmark scenarios are registered across categories A through Q.
- `test_offline_engine_replay_general_info`: Replays `SCEN-GEN-001` in `OFFLINE` mode with deterministic seed `42`. Asserts status is `PASS`, `SAFE` state, and P95 latency within SLA.
- `test_fault_injection_interceptor`: Injects `KNOWLEDGE_TIMEOUT` and verifies the engine records the injected fault without crashing.

### 1.3 `tests/test_evaluation_safety.py` (3 Tests)
- `test_critical_self_harm_scenario`: Replays `SCEN-CRIT-001` (Hindi suicidal ideation); asserts `CRITICAL` safety state, `SELF_HARM` detection, and `human_review_required = True`.
- `test_critical_violence_scenario`: Replays `SCEN-CRIT-002` (Physical violence and knife threat); asserts `CRITICAL` state and weapon detection.
- `test_zero_autonomous_dispatch_guarantee`: Replays all critical emergencies; verifies `autonomous_dispatch` remains strictly `False` across every turn and subsystem metric.

### 1.4 `tests/test_evaluation_subsystems.py` (4 Tests)
- `test_multilingual_code_switch_replay`: Replays `SCEN-MULTI-001` (Tanglish code-switching); validates language tag and withdrawal detection.
- `test_adaptive_hesitant_replay`: Replays `SCEN-ADAPT-001` (Hesitant caller with prolonged silence); asserts adaptive policy adjusts to hesitant pacing.
- `test_acoustic_packet_loss_replay`: Replays `SCEN-ACOU-001` (8kHz telephony packet loss); validates degraded audio flag.
- `test_privacy_district_isolation_replay`: Replays `SCEN-PRIV-001`; asserts `isolated_from_analytics = True` and synthetic isolation markers.

### 1.5 `tests/test_evaluation_baselines.py` (3 Tests)
- `test_capture_and_retrieve_baseline`: Captures a completed evaluation run as a golden baseline snapshot and verifies persistence.
- `test_diff_identical_runs`: Compares identical runs and asserts `status = "IDENTICAL"` and `has_regression = False`.
- `test_diff_detects_safety_regression`: Simulates a safety degradation from `CRITICAL` to `SAFE` and asserts `has_regression = True`.

### 1.6 `tests/test_evaluation_api.py` (7 Tests)
- `test_evaluation_status_endpoint`: `GET /v1/evaluation/status` returns operational health and scenario counts.
- `test_list_scenarios_endpoint`: `GET /v1/evaluation/scenarios` returns scenario catalog with filtering.
- `test_get_scenario_by_id`: `GET /v1/evaluation/scenarios/{id}` returns scenario details and turns.
- `test_execute_evaluation_run_endpoint`: `POST /v1/evaluation/runs` initiates replay and returns assertions.
- `test_run_suite_endpoint`: `POST /v1/evaluation/suites/run` executes a batch benchmark suite.
- `test_baseline_lifecycle_endpoints`: Tests capture and listing of baseline snapshots.
- `test_diff_endpoint`: `POST /v1/evaluation/diff` computes regression diff between run and baseline.

---

## 2. Frontend Playwright E2E Suite (10/10 Passed)

The end-to-end browser test suite covers all interactive capabilities of the Evaluation Lab at `/evaluation` across both Desktop Chrome and Mobile Chrome viewports.

Execute with:
```bash
pnpm --filter @samved/web exec playwright test e2e/evaluation-lab.spec.ts
```

### Coverage in `apps/web/e2e/evaluation-lab.spec.ts`:
1. **Governance & Isolation Banner**: Confirms persistent amber warning banner displaying `AUTONOMOUS DISPATCH: FALSE` and `ISOLATED SANDBOX`.
2. **Sidebar Navigation**: Verifies sidebar navigation item "Evaluation Lab" with `ShieldCheck` icon navigating cleanly to `/evaluation`.
3. **Scenario Library & Filtering**: Validates 19 scenario benchmark cards, category tags, search bar filtering, and detailed specification inspect drawer.
4. **Interactive Run Replay & Telemetry**:
   - Executes offline replay for a scenario.
   - Verifies `STATUS: PASS` badge and latency cards.
   - Inspects Machine-Checkable Golden Expectations assertions sub-tab.
   - Inspects Subsystem Telemetry sub-tab (Safety, SVI, Acoustic, Adaptive, Orchestration).
   - Computes Baseline Regression Diff and verifies `NO REGRESSION` badge.
5. **Suite Runner**: Verifies selection of benchmark suites (`smoke`, `safety`, `full`), replay mode toggle (`OFFLINE` / `INTEGRATED`), and deterministic seed inputs.
