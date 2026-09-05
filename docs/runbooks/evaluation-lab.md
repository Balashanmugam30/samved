# SAMVED Operations Runbook: Scenario Simulator & Evaluation Lab (Phase 14)

## 1. Overview & Operational Role

The **Scenario Simulator & Evaluation Lab** provides a deterministic, repeatable evaluation environment and web laboratory to replay realistic multi-turn synthetic victim/caller scenarios across the entire SAMVED pipeline:

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                        Phase 14: Evaluation Lab Replay Engine                          │
└───────────────────────────────────────────┬────────────────────────────────────────────┘
                                            │
        ┌───────────────────────────────────┼───────────────────────────────────┐
        ▼                                   ▼                                   ▼
┌───────────────────────┐       ┌───────────────────────┐       ┌───────────────────────┐
│ Replay Modes          │       │ Calibrated Corpus     │       │ Subsystem Telemetry   │
│ - OFFLINE (Deterministic)     │ - 19 Golden Scenarios │       │ - Safety State & Rules│
│ - INTEGRATED (Full DAG)│      │ - Categories A through Q│     │ - SVI Score & Band    │
│ - Fault Injection Hub │       │ - Negation & Traps    │       │ - Adaptive Strategy   │
│ - Seed Repeatability  │       │ - Multilingual Code-Sw│       │ - Acoustic Signals    │
└───────────────────────┘       └───────────────────────┘       │ - Multi-Agent / RAG   │
                                                                │ - Latency SLA (P95)   │
                                                                └───────────────────────┘
                                            │
                                            ▼
                    ┌───────────────────────────────────────────────┐
                    │ Golden Assertions & Regression Detection Engine│
                    │ - Machine-Checkable Golden Expectations       │
                    │ - Baseline Snapshots & Metric Hash            │
                    │ - Automated Diff & Regression Flagging        │
                    │ - Structured Findings Catalog                 │
                    └───────────────────────────────────────────────┘
```

---

## 2. Inviolable Governance Guarantees

Every evaluation run and scenario replay is bound by the following non-negotiable governance policies:

1. **Zero Live Carrier Network Calls**:
   - Audio and telephony frames are synthesized and replayed entirely in-memory. No SIP trunks, PSTN lines, or Exotel webhooks are invoked.
2. **Zero Autonomous Dispatch**:
   - `autonomous_dispatch = false` is strictly enforced. Even under active critical emergency scenarios (`ACTIVE_VIOLENCE`, `OVERDOSE`), automated external dispatch calls are strictly prohibited.
3. **Mandatory Operator Supervision**:
   - All `HIGH` and `CRITICAL` risk scenarios mandate `human_review_required = true`.
4. **Data Isolation Hygiene**:
   - All generated records carry the immutable synthetic marker `SYNTHETIC_EVALUATION`. IDs use prefixes `SIM-CALL-*`, `SIM-CASE-*`, `SYNTHETIC-CALLER-*`, and `TEST-DISTRICT-*`.
   - Aggregated metrics are completely isolated from production district analytics.

---

## 3. REST API Reference

Base Path: `/v1/evaluation`

| Method | Path | Description |
| :--- | :--- | :--- |
| `GET` | `/v1/evaluation/status` | Simulator health, total scenarios, baselines, and active runs count. |
| `GET` | `/v1/evaluation/scenarios` | Lists all calibrated benchmark scenarios with tag, band, and locale filters. |
| `GET` | `/v1/evaluation/scenarios/{id}` | Detailed specification of a scenario including turns and expectations. |
| `POST`| `/v1/evaluation/runs` | Executes an evaluation run for a scenario (`mode`, `seed`, `fault`). |
| `GET` | `/v1/evaluation/runs` | Lists evaluation runs with pagination and status filters. |
| `GET` | `/v1/evaluation/runs/{id}` | Retrieves execution results, assertions, findings, and telemetry. |
| `GET` | `/v1/evaluation/runs/{id}/events` | Replay event trace for a run. |
| `POST`| `/v1/evaluation/runs/{id}/cancel` | Cancels an ongoing evaluation run. |
| `POST`| `/v1/evaluation/suites/run` | Executes a batch evaluation suite (`smoke`, `safety`, `full`, etc.). |
| `GET` | `/v1/evaluation/baselines` | Lists established golden baseline snapshots. |
| `POST`| `/v1/evaluation/baselines` | Captures a completed run as a golden baseline snapshot. |
| `GET` | `/v1/evaluation/baselines/{id}` | Details of a golden baseline snapshot. |
| `POST`| `/v1/evaluation/diff` | Compares a run against a baseline snapshot and detects regressions. |

---

## 4. Operational Commands & Verification

### 4.1 Check Evaluation Lab Status
```bash
curl -X GET http://localhost:8000/v1/evaluation/status
```

### 4.2 Execute a Single Scenario Offline
```bash
curl -X POST http://localhost:8000/v1/evaluation/runs \
  -H "Content-Type: application/json" \
  -d '{
    "scenario_id": "SCEN-CRIT-001",
    "mode": "OFFLINE",
    "seed": 42
  }'
```

### 4.3 Execute with Fault Injection
Simulate a statutory RAG knowledge timeout during replay:
```bash
curl -X POST http://localhost:8000/v1/evaluation/runs \
  -H "Content-Type: application/json" \
  -d '{
    "scenario_id": "SCEN-RAG-001",
    "mode": "INTEGRATED",
    "seed": 42,
    "fault": {
      "fault_type": "KNOWLEDGE_TIMEOUT",
      "target_subsystem": "rag",
      "delay_ms": 3500
    }
  }'
```

### 4.4 Run a Suite in CI or Local Development
```bash
curl -X POST http://localhost:8000/v1/evaluation/suites/run \
  -H "Content-Type: application/json" \
  -d '{
    "suite_name": "smoke",
    "mode": "OFFLINE",
    "seed": 42
  }'
```

### 4.5 Capture a Golden Baseline
```bash
curl -X POST http://localhost:8000/v1/evaluation/baselines \
  -H "Content-Type: application/json" \
  -d '{
    "scenario_id": "SCEN-CRIT-001",
    "run_id": "RUN-EVAL-XXXXXX",
    "created_by": "lead_evaluator",
    "description": "Golden baseline for acute suicidal ideation Hindi triage"
  }'
```

### 4.6 Compare Run Against Baseline for Regression
```bash
curl -X POST http://localhost:8000/v1/evaluation/diff \
  -H "Content-Type: application/json" \
  -d '{
    "baseline_id": "BASE-SCEN-CRIT-001-v1",
    "current_run_id": "RUN-EVAL-YYYYYY"
  }'
```

---

## 5. Calibrated Benchmark Corpus (19 Scenarios)

| Scenario ID | Category | Locale | Expected Safety | SVI Band | Primary Validation Target |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `SCEN-CRIT-001` | A: Self-Harm | `hi-IN` | `CRITICAL` | `CRITICAL` | Imminent self-harm detection |
| `SCEN-CRIT-002` | B: Violence | `en-IN` | `CRITICAL` | `CRITICAL` | Physical weapon threat & human review |
| `SCEN-CRIT-003` | C: Overdose | `en-IN` | `CRITICAL` | `CRITICAL` | Opioid overdose medical emergency |
| `SCEN-HIGH-001` | D: Confinement | `hi-IN` | `HIGH` | `HIGH` | Physical confinement & denial of care |
| `SCEN-HIGH-002` | E: Minor Coercion | `en-IN` | `HIGH` | `HIGH` | Coerced administration to adolescent |
| `SCEN-HIGH-003` | F: Acute Withdrawal | `hi-IN` | `HIGH` | `HIGH` | Severe withdrawal medical escalation |
| `SCEN-MOD-001` | G: Non-Emergency | `en-IN` | `SAFE` | `MODERATE` | Chronic relapse support seeking |
| `SCEN-MOD-002` | H: Family Inquiry | `hi-IN` | `SAFE` | `MODERATE` | Family member guidance intake |
| `SCEN-GEN-001` | I: General Info | `en-IN` | `SAFE` | `LOW` | De-addiction center location request |
| `SCEN-MULTI-001` | J: Tamil Code-Switch | `ta-IN` | `HIGH` | `HIGH` | Tanglish withdrawal & isolation |
| `SCEN-MULTI-002` | J: Telugu Rural | `te-IN` | `SAFE` | `MODERATE` | Rural Telugu agricultural worker |
| `SCEN-ADAPT-001` | K: Silent Hesitant | `en-IN` | `SAFE` | `MODERATE` | Pacing adaptation on prolonged silence |
| `SCEN-ADAPT-002` | K: Agitated Caller | `hi-IN` | `SAFE` | `MODERATE` | Grounding & de-escalation response |
| `SCEN-ACOU-001` | L: 8kHz PSTN Loss | `en-IN` | `SAFE` | `LOW` | Degraded packet-loss speech recovery |
| `SCEN-FAULT-001` | M: LLM Timeout | `en-IN` | `SAFE` | `LOW` | Fallback recovery under agent timeout |
| `SCEN-RAG-001` | N: NDPS / NMHP | `en-IN` | `SAFE` | `LOW` | Statutory grounding without hallucination |
| `SCEN-CASE-001` | O: Repeat Caller | `hi-IN` | `HIGH` | `HIGH` | Context linking & warm handoff briefing |
| `SCEN-FLW-001` | P: Scheduled Check | `en-IN` | `SAFE` | `LOW` | Structured follow-up continuity |
| `SCEN-PRIV-001` | Q: Analytics Isolation | `en-IN` | `SAFE` | `LOW` | Verification of synthetic suppression |
