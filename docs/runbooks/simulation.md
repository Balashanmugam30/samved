# SAMVED Operations Runbook: Scenario Simulation Engine & Operator Training Sandbox (Phase 14)

## 1. Overview & Operational Role

The **Scenario Simulation Engine & Operator Training Sandbox** provides continuous automated benchmarking, Indic speech recognition (WER/CER) quality evaluation, deterministic safety recall verification, and tele-counselor training for the SAMVED helpline (**NHAA 14566**).

```
                 ┌─────────────────────────────────────────────────────────┐
                 │       Phase 14: Scenario Simulation Subsystem           │
                 └───────────────────────────┬─────────────────────────────┘
                                             │
               ┌─────────────────────────────┼─────────────────────────────┐
               ▼                             ▼                             ▼
    ┌──────────────────────┐    ┌─────────────────────────┐   ┌─────────────────────────┐
    │  Automated Benchmark │    │   Indic ASR & WER Lab   │   │     Operator Training   │
    │  - 24+ Scenarios     │    │   - Unicode NFC Normalizer│   │     - 4 Curated Drills  │
    │  - 11 Languages      │    │   - Wagner-Fischer DP   │   │     - Real-Time SOP     │
    │  - 100% Safety Recall│    │   - Noise Distortion    │   │     - Empathy & Pacing  │
    │  - SVI Calibration   │    │   - Token Diff Alignment│   │     - Scorecard Cert    │
    └──────────────────────┘    └─────────────────────────┘   └─────────────────────────┘
```

---

## 2. API Endpoints Reference

Base path: `/v1/simulation`

| Method | Path | Description |
| :--- | :--- | :--- |
| `GET` | `/v1/simulation/status` | Operational health, scenario & drill counts, supported languages. |
| `GET` | `/v1/simulation/scenarios` | Lists benchmark scenarios with optional `band`, `language`, `tag` filters. |
| `GET` | `/v1/simulation/scenarios/{id}` | Full dialogue turns and metadata for a scenario. |
| `POST`| `/v1/simulation/benchmark/run` | Triggers benchmark run (`suite="SMOKE"` or `"FULL"`). |
| `GET` | `/v1/simulation/benchmark/runs` | Lists historical benchmark runs with aggregated metrics. |
| `GET` | `/v1/simulation/benchmark/runs/{id}` | Detailed results per scenario for a specific run. |
| `POST`| `/v1/simulation/wer/evaluate` | Evaluates WER and CER on reference vs. hypothesis text. |
| `GET` | `/v1/simulation/training/drills` | Lists curated training drills (`difficulty` filter). |
| `POST`| `/v1/simulation/training/session/start` | Initiates an interactive trainee counseling session. |
| `GET` | `/v1/simulation/training/session/{id}` | Retrieves session progress, scores, and scorecard. |
| `POST`| `/v1/simulation/training/session/{id}/turn` | Submits trainee turn and receives instant SOP feedback. |

---

## 3. Command-Line Runbook & Verification

### 3.1 Run Automated Benchmark (Smoke Suite)
```bash
curl -X POST http://localhost:8000/v1/simulation/benchmark/run \
  -H "Content-Type: application/json" \
  -d '{"suite": "SMOKE"}'
```

### 3.2 Compute Indic WER & CER
```bash
curl -X POST http://localhost:8000/v1/simulation/wer/evaluate \
  -H "Content-Type: application/json" \
  -d '{
    "reference": "नमस्ते मुझे तुरंत सहायता चाहिए",
    "hypothesis": "नमस्ते तुरंत सहायता चाहिए"
  }'
```

### 3.3 Start an Operator Practice Drill
```bash
curl -X POST http://localhost:8000/v1/simulation/training/session/start \
  -H "Content-Type: application/json" \
  -d '{
    "drill_key": "DRILL-OVERDOSE-001",
    "trainee_id": "T-OPERATOR-101",
    "trainee_name": "Counselor Priya"
  }'
```

### 3.4 Submit Trainee Response Turn
```bash
curl -X POST http://localhost:8000/v1/simulation/training/session/{session_id}/turn \
  -H "Content-Type: application/json" \
  -d '{
    "trainee_input": "Stay calm, please turn him on his side in the recovery position immediately while I coordinate the emergency ambulance and doctor."
  }'
```

---

## 4. Troubleshooting & Operational FAQs

### Q1: Why does a critical scenario report false negative hazard?
Ensure the scenario dialogue contains canonical phrases registered in `apps/api/app/safety_rules/v1/` and that the caller's temporal indicators are `PRESENT` rather than `PAST` or `HYPOTHETICAL`.

### Q2: How does the engine prevent live telephony trunk pollution?
All simulated calls use `provider = "simulation"` and IDs starting with `SIM-*`. The session manager isolates these from carrier trunks and live counselor queues.

### Q3: How is WER computed on Indic scripts?
Unicode NFC normalization is applied first to unify combining matras and viramas. Western punctuation and Indic Dandas (`।`, `॥`) are stripped before Wagner-Fischer edit distance alignment.
