# SAMVED — Phase 14 Milestone Completion Document
**Scenario Simulation Engine & Operator Training Sandbox — Continuous Benchmarking, Indic ASR Quality, Deterministic Safety Verification & Tele-Counselor Sandbox**

- **Date**: September 2026
- **Status**: COMPLETE ✅
- **Repository**: [Balashanmugam30/samved](https://github.com/Balashanmugam30/samved)
- **Branch**: `main`

---

## 1. Executive Summary

Phase 14 delivers the **Scenario Simulation Engine & Operator Training Sandbox** for SAMVED, establishing an automated benchmarking and continuous quality-assurance framework for the National Toll-Free Drug De-Addiction Helpline (NHAA 14566). It guarantees deterministic safety recall ($\text{Recall} = 1.00$ on high-threat triggers), Indic ASR transcript quality via Wagner-Fischer Word Error Rate (WER) and Character Error Rate (CER) calculation, and an interactive tele-counselor training simulator with real-time Standard Operating Procedure (SOP) rubric scoring.

### Core Architectural Pipeline:
$$\text{Synthetic Scenario} \to \text{Noise Distortion} \to \text{Indic Unicode Normalization} \to \text{Safety \& SVI Evaluation} \to \text{Wagner-Fischer Alignment} \to \text{SOP Scoring} \to \text{Run Persistence}$$

### Absolute Operational & Governance Boundaries Verified:
1. **Zero Live Caller Data Contamination**:
   - All conversational scenarios, transcript variants, and training drills are strictly synthetic. No actual helpline audio, live transcripts, or confidential caller records are used.
2. **Zero Live Telephony Trunk Pollution**:
   - Simulation sessions are tagged with `provider = "simulation"` and isolated IDs `call_id = "SIM-*"` and `session_id = "TRN-*"`. They do not initiate carrier trunk calls or enter live operator queues.
3. **Comprehensive Multilingual Coverage**:
   - 24 calibrated synthetic scenarios spanning 11 official Indian languages (`hi-IN`, `ta-IN`, `te-IN`, `kn-IN`, `ml-IN`, `mr-IN`, `bn-IN`, `gu-IN`, `pa-IN`, `or-IN`, `en-IN`) plus code-switching (Hinglish/Tanglish).
4. **Deterministic Safety Recall Verification**:
   - Critical high-threat triggers (`SELF_HARM`, `ACTIVE_THREAT`, `MEDICAL_EMERGENCY`, `CONFINEMENT`) mandate an absolute 100% recall target ($\text{Recall} = 1.00$). Any false negative fails the benchmark run.
5. **Sub-1200ms P95 Turn Latency SLA**:
   - Benchmarks enforce sub-1200ms P95 turn latency across Indic text normalization, safety evaluation, and SVI scoring.

---

## 2. Completed Architecture & Deliverables

### 2.1 Backend Simulation Subsystem (`apps/api/app/simulation/`)
1. **Domain Models & Enums (`models.py`)**:
   - Enums: `BenchmarkSuiteType` (`SMOKE`, `FULL`, `STRESS`, `INDIC_REGRESSION`), `BenchmarkRunStatus` (`PENDING`, `RUNNING`, `COMPLETED`, `FAILED`), `NoiseProfile` (`CLEAN`, `8KHZ_TELEPHONY`, `LOW_SNR_STREET`, `PACKET_LOSS_BURST`), `DrillDifficulty` (`BEGINNER`, `INTERMEDIATE`, `ADVANCED`, `EXPERT`).
   - Domain models: `SyntheticScenario`, `ScenarioResult`, `BenchmarkRun`, `WERResult`, `AlignmentOp`, `TrainingDrill`, `TrainingSession`, `TurnEvaluation`.
2. **Indic Text Normalization & Wagner-Fischer Metrics (`metrics.py`)**:
   - Indic Unicode NFC normalization stripping punctuation, Dandas (`।`, `॥`), and zero-width joiners/non-joiners (`\u200c`, `\u200d`).
   - Exact dynamic programming implementation of Word Error Rate (WER) and Character Error Rate (CER) computing token-by-token alignment (`match`, `sub`, `del`, `ins`).
   - Synthetic noise distortion models simulating 8kHz PCM band-pass, street background noise, and packet loss dropouts.
3. **Calibrated Synthetic Scenario Catalog (`catalog.py`)**:
   - 24 synthetic scenarios across 4 SVI bands (`CRITICAL`, `HIGH`, `MODERATE`, `LOW`) and 11 Indic languages.
   - Includes adversarial edge cases: negation traps (*"I will not hurt myself"*), past ideation disclosures, compound weapon threats, and code-switched cries for help.
4. **Automated Benchmark Harness (`harness.py`)**:
   - Executes test suites against `DeterministicSafetyEngine` and `SVIEngine`.
   - Computes WER against corrupted ASR hypothesis turns, validates SVI prototype band calibration, verifies 100% critical safety recall, and profiles turn latencies.
5. **Operator Training Sandbox Engine (`sandbox.py`)**:
   - 4 curated tele-counselor drills: Overdose Rapid Intake, Withdrawal & Dislocation, Domestic Violence & Coercion, IRCA Referral Navigation.
   - Real-time SOP rubric scoring engine (100 points: Safety Protocol 35 pts, Empathy 25 pts, De-escalation 20 pts, Referral Accuracy 20 pts) with contextual feedback hints.
6. **REST Schemas (`schemas.py`)**:
   - Clean Pydantic schemas for benchmark triggers, WER calculations, drill session lifecycle, and turn submissions.
7. **Simulation Service Singleton (`service.py`)**:
   - Manages benchmark execution history, pre-seeds baseline runs, and handles multi-turn training drill sessions.

### 2.2 Shared Schemas & Contracts
- **`packages/schemas/src/events.ts`**:
   - Added 6 `BENCHMARK_*` and `TRAINING_*` event types to `EventType`.
   - Added `BenchmarkSuiteType`, `BenchmarkRunStatus`, `NoiseProfile`, and `DrillDifficulty` enums.
   - Exported TypeScript interfaces for benchmark runs, scenario results, WER results, and training drills.
- **`apps/api/app/schemas/events.py`**:
   - Mirrored Pydantic schemas matching TypeScript definitions 1:1.

### 2.3 Database Migration (`infra/db/init.sql`)
Created 4 relational tables with indexing and updated role permissions:
- `simulation_scenarios`: Synthetic scenario definitions, expected bands, and safety triggers.
- `simulation_benchmark_runs`: Run history, pass rates, mean WER/CER, and safety recall rates.
- `operator_training_drills`: Practice drill scenarios and expected competencies.
- `operator_training_sessions`: Trainee session records, multi-turn logs, and competency scores.

### 2.4 REST API Endpoints (`apps/api/app/api/v1/simulation.py`)
Mounted at `/v1/simulation`:
- `GET /status` — Subsystem health, scenario/drill counts, supported languages.
- `GET /scenarios` — List scenarios with optional `band` and `language` filters.
- `GET /scenarios/{scenario_id}` — Scenario details by ID.
- `POST /benchmark/run` — Trigger benchmark run (`SMOKE` or `FULL`).
- `GET /benchmark/runs` — Benchmark run history.
- `GET /benchmark/runs/{run_id}` — Benchmark run details.
- `POST /wer/evaluate` — Dynamic programming WER/CER evaluation with token alignment.
- `GET /training/drills` — List training drills.
- `POST /training/session/start` — Start training session.
- `POST /training/session/{session_id}/turn` — Submit trainee turn for SOP evaluation.
- `GET /training/session/{session_id}` — Final training session report.

### 2.5 Next.js Web Console (`apps/web/src/app/simulation/page.tsx`)
- **Navigation**: Sidebar updated with "Simulation & Sandbox" link (`/simulation`, badge "Phase 14", icon `FlaskConical`).
- **Governance Banner**: Displays synthetic benchmark isolation badge and 100% safety recall target.
- **KPI Summary Strip**: Critical Safety Recall (100%), Mean WER, Mean CER, SVI Calibration Accuracy, P95 Triage Latency.
- **Tab 1: Automated Benchmark Runner**: Suite selector (`Smoke` / `Full`), trigger button, risk band filter pills, and detailed scenario table with trigger chips and latency metrics.
- **Tab 2: Indic ASR & WER Lab**: Interactive calculator with Hindi/Tamil presets, computed WER/CER metrics, and color-coded visual token diff (Match, Substitution, Deletion, Insertion).
- **Tab 3: Operator Training Sandbox**: Practice drill picker, conversation timeline, counselor microphone/chat input, and immediate SOP Rubric scorecard pill.

---

### 2.6 Evaluation Lab Subsystem (`apps/api/app/evaluation/`)
1. **Domain Models & Contracts (`models.py`, `schemas.py`)**:
   - `EvaluationMode` (`OFFLINE`, `INTEGRATED`), `FindingSeverity` (`PASS`, `INFO`, `WARNING`, `FAIL`, `CRITICAL`), `EvaluationStatus` (`PASS`, `FAIL`, `WARN`, `ERROR`), `FaultType` (`NONE`, `TIMEOUT`, `PROVIDER_DOWN`, `NETWORK_FAILURE`, `CIRCUIT_BREAKER_TRIGGERED`, `KNOWLEDGE_TIMEOUT`, `ORCHESTRATION_FAILURE`).
   - Pydantic domain models: `ScenarioDefinition`, `CallerProfile`, `ScenarioTurn`, `GoldenExpectations`, `EvaluationAssertionResult`, `EvaluationFinding`, `SubsystemMetrics`, `EvaluationRunRecord`, `BaselineSnapshot`, `RunDiffResult`.
2. **Calibrated Benchmark Corpus (`corpus.py`)**:
   - 19 golden scenarios across categories A through Q:
     - `SCEN-CRIT-001` (A: Hindi acute suicidal crisis)
     - `SCEN-CRIT-002` (B: English active weapon violence threat)
     - `SCEN-CRIT-003` (C: English acute opioid overdose medical emergency)
     - `SCEN-HIGH-001` (D: Hindi severe withdrawal & locked room confinement)
     - `SCEN-HIGH-002` (E: English coerced minor substance consumption)
     - `SCEN-HIGH-003` (F: Hindi life-threatening alcohol withdrawal delirium)
     - `SCEN-MOD-001` (G: English relapse prevention guidance)
     - `SCEN-MOD-002` (H: Hindi family member codependency inquiry)
     - `SCEN-GEN-001` (I: English IRCA de-addiction directory lookup)
     - `SCEN-MULTI-001` (J: Tanglish code-switching acute crisis)
     - `SCEN-MULTI-002` (J: Telugu rural agricultural worker intake)
     - `SCEN-ADAPT-001` (K: Hesitant silent caller pacing adaptation)
     - `SCEN-ADAPT-002` (K: Agitated shouting caller de-escalation)
     - `SCEN-ACOU-001` (L: 8kHz PSTN line noise packet drop recovery)
     - `SCEN-FAULT-001` (M: LLM timeout graceful fallback)
     - `SCEN-RAG-001` (N: NDPS Act legal citation grounding)
     - `SCEN-CASE-001` (O: Repeat caller knowledge graph warm handoff)
     - `SCEN-FLW-001` (P: Scheduled recovery follow-up continuity)
     - `SCEN-PRIV-001` (Q: District analytics small-cell isolation verification)
3. **Machine-Checkable Assertion Engine (`assertions.py`)**:
   - Verifies expected safety state, prohibited safety triggers, expected SVI band, SVI score boundaries, required telemetry, latency P95 SLA, citations validity, and zero autonomous dispatch.
4. **Fault Injection Interceptor (`faults.py`)**:
   - Intercepts calls to simulate timeouts, synthetic latency delays, provider down conditions, or orchestration failures to measure pipeline resilience.
5. **Baseline Snapshot Capture & Regression Diff Engine (`diff.py`)**:
   - Compares current run metrics against established golden baselines.
   - Computes SHA-256 telemetry hash.
   - Detects safety regressions (critical drop), SVI score shifts, latency SLA breaches, and generates structured findings.
6. **Replay Engine (`engine.py`) & Service (`service.py`)**:
   - Replays multi-turn scenarios deterministically through `DeterministicSafetyEngine`, `SVIEngine`, `AcousticEngine`, `AdaptiveEngine`, `MultiAgentOrchestrator`, and `KnowledgeService`.
   - Full persistence across in-memory state and SQL evaluation tables.

### 2.7 Evaluation Lab REST APIs (`apps/api/app/api/v1/evaluation.py`)
Mounted at `/v1/evaluation`:
- `GET /status` — Operational health, total scenarios, baselines, completed runs.
- `GET /scenarios` — Scenario library with tag, band, and locale filters.
- `GET /scenarios/{id}` — Detailed scenario definition with multi-turn narrative.
- `POST /runs` — Executes single scenario evaluation run (`mode`, `seed`, `fault`).
- `GET /runs` — Run execution history.
- `GET /runs/{id}` — Detailed run telemetry, assertions, and findings.
- `GET /runs/{id}/events` — Event trace for run.
- `POST /runs/{id}/cancel` — Cancel ongoing run.
- `POST /suites/run` — Batch suite evaluation (`smoke`, `safety`, `full`, etc.).
- `GET /baselines` — List established golden baseline snapshots.
- `POST /baselines` — Capture run as golden baseline.
- `GET /baselines/{id}` — Baseline details.
- `POST /diff` — Regression diff between run and baseline.

### 2.8 Next.js Evaluation Lab Console (`apps/web/src/app/evaluation/page.tsx`)
- Persistent amber governance banner: `AUTONOMOUS DISPATCH: FALSE`, `ISOLATED SANDBOX`.
- Navigation: Sidebar item "Evaluation Lab" linking to `/evaluation` with `ShieldCheck` icon.
- Scenario Library with search filters, category tags, and Inspect Spec drawer.
- Active Run Telemetry with 5 sub-tabs:
  - **Findings**: Structured findings catalog with severity badges.
  - **Assertions**: Machine-checkable golden expectations vs actual outcomes.
  - **Subsystem Telemetry**: Safety rules, SVI score/band, Adaptive policy, Acoustic frames, Orchestration DAG, RAG citations, Case handoff, Follow-up continuity.
  - **Latency Waterfall**: Per-stage millisecond timing visualization.
  - **Baseline Diff**: Golden baseline regression detector with field-level diff table.
- Suite Runner: Batch benchmark suites (`smoke`, `safety`, `multilingual`, `full`) with mode and seed controls.

---

## 3. Verification & Testing

### 3.1 Backend Test Suite (Pytest)
30 Phase 14 Evaluation Lab unit and integration tests:
- `test_evaluation_schema.py` (6 tests): Domain models, enums, assertion and metrics contracts.
- `test_evaluation_engine.py` (3 tests): Calibrated scenario registration, deterministic offline replay, fault injection.
- `test_evaluation_safety.py` (3 tests): Imminent self-harm detection, active weapon violence, zero autonomous dispatch guarantee.
- `test_evaluation_subsystems.py` (4 tests): Multilingual code-switching, adaptive hesitation pacing, acoustic packet loss, district analytics isolation.
- `test_evaluation_baselines.py` (3 tests): Baseline capture, identical run comparison, safety regression detection.
- `test_evaluation_api.py` (7 tests): All 12 evaluation REST endpoints and validation.
- Plus 23 Phase 14 Simulation & Sandbox tests (`test_simulation_*.py`).

**Full Repository Regression Result**:
```
======================= 382 passed, 4 warnings in 8.87s =======================
```

### 3.2 Frontend End-to-End Test Suites (Playwright)
1. `apps/web/e2e/simulation-dashboard.spec.ts` (16 tests across Desktop and Mobile Chrome):
   - Benchmark runner, Indic WER/CER calculator, Operator training sandbox.
2. `apps/web/e2e/evaluation-lab.spec.ts` (10 tests across Desktop and Mobile Chrome):
   - Governance warning banner & isolation guarantees.
   - Sidebar navigation to `/evaluation`.
   - Scenario library, category filters & Inspect Spec drawer.
   - End-to-end scenario replay, assertions, subsystem telemetry, latency waterfall & baseline diff.
   - Suite runner batch execution controls.

**Playwright Result**:
```
Running 10 tests using 8 workers
  10 passed (8.8s)
```

---

## 4. Operational Sign-off

Phase 14 completes all technical, architectural, and governance milestones:
- [x] Synthetic scenario isolation strictly maintained (`SIM-*` prefix, `SYNTHETIC_EVALUATION` markers, no live Exotel carrier line dialing).
- [x] Zero autonomous dispatch strictly enforced (`autonomous_dispatch = false`).
- [x] Mandatory human supervision enforced on all High/Critical risk evaluations (`human_review_required = true`).
- [x] Calibrated benchmark corpus (19 scenarios across categories A-Q) and simulation catalog (24 scenarios across 11 Indic languages).
- [x] Machine-checkable golden expectations and automated assertion engine operational.
- [x] Fault injection interceptor for subsystem timeouts, provider outages, and delays.
- [x] Baseline snapshot capture and automated regression diff detector operational.
- [x] Evaluation Lab web console (`/evaluation`) and Simulation Sandbox (`/simulation`) fully interactive and responsive across desktop and mobile.
- [x] Full test suite (382 backend tests, 26 Playwright E2E tests) passing cleanly with zero failures.
- [x] Phase 14 marked COMPLETE in repository roadmap. Phase 15 (Security & Privacy Hardening) is Next.

