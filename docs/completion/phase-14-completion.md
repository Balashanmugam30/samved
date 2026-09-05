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

## 3. Verification & Testing

### 3.1 Backend Test Suite (Pytest)
23 Phase 14 simulation unit and integration tests:
- `test_simulation_metrics.py` (6 tests): Unicode NFC normalization, Wagner-Fischer WER/CER, token diff alignment, telephony noise distortion.
- `test_simulation_catalog.py` (3 tests): 24 scenarios, 11 languages, 4 SVI bands, negation traps.
- `test_simulation_harness.py` (3 tests): Smoke/Full benchmark runs, 100% safety recall, sub-1200ms latency SLA.
- `test_simulation_sandbox.py` (2 tests): Training session lifecycle, multi-turn state machine, SOP scoring.
- `test_simulation_api.py` (6 tests): REST endpoint responses, input validations, error handling.
- `test_simulation_scenarios.py` (3 tests): Edge case triggers and SVI band verification.

**Full Repository Regression Result**:
```
======================= 356 passed, 4 warnings in 7.97s =======================
```

### 3.2 Frontend End-to-End Test Suite (Playwright)
`apps/web/e2e/simulation-dashboard.spec.ts` (16 tests across Desktop Chrome and Mobile Chrome):
- Direct navigation & governance banner
- Top KPI summary cards (100% safety recall)
- Benchmark results table rendering & pass badges
- Risk band filter buttons (`ALL`, `CRITICAL`, `HIGH`, `MODERATE`, `LOW`)
- Benchmark run trigger execution
- Indic ASR & WER calculator with token diff visualization
- Operator Training Sandbox drill selection and turn evaluation with SOP scorecard
- Sidebar navigation link verification

**Playwright Result**:
```
Running 16 tests using 8 workers
  16 passed (7.7s)
```

---

## 4. Operational Sign-off

Phase 14 completes all technical and governance milestones:
- [x] Synthetic scenario isolation strictly maintained (`SIM-*` prefix, no live Exotel carrier line dialing).
- [x] 11 Indic languages covered with Unicode NFC normalization and Wagner-Fischer WER/CER metrics.
- [x] Deterministic safety recall verified at 100% on high-threat triggers with zero false negatives.
- [x] Sub-1200ms P95 triage latency SLA verified across all 24 scenarios.
- [x] Operator training sandbox operational with real-time SOP scoring rubric.
- [x] Full test suite (356 backend tests, 16 Playwright E2E tests) passing cleanly.
- [x] Phase 14 marked COMPLETE in repository roadmap. Phase 15 (Security & Privacy Hardening) is Next.
