# SAMVED Testing Strategy: Phase 14 Scenario Simulation Engine & Operator Training Sandbox

## 1. Quality & Safety Verification Objectives

Phase 14 ensures that SAMVED's AI-assisted triage, safety rules, speech models, and counselor workstations undergo continuous, automated, non-disruptive testing:

1. **Safety Recall Verification ($\text{Recall} = 1.00$)**:
   - Immediate physical harm (`SELF_HARM`), lethal violence (`ONGOING_THREAT`, `WEAPON`), and acute poisoning (`MEDICAL_EMERGENCY`) triggers must fire with 100% recall.
   - Zero tolerance for false negatives on life-threatening scenarios.
2. **Deterministic Negation Trap Defense**:
   - Utterances like "I do not want to die" or "nobody is threatening me with a knife" must NEVER trigger emergency alarms or counselor takeovers.
3. **Indic Speech Recognition Quality (WER & CER)**:
   - Evaluates Word Error Rate and Character Error Rate with Unicode NFC canonical decomposition, Indic Danda (`।`, `॥`) stripping, and case/whitespace normalization.
4. **SVI Band Calibration**:
   - Compares computed SVI scores against calibrated risk bands (`LOW`: 0–25, `MODERATE`: 26–50, `HIGH`: 51–75, `CRITICAL`: 76–100).
5. **P95 Latency Profiling**:
   - Turn processing latency must be strictly $< 1200\text{ ms}$ (SLA).
6. **Operator Sandbox Protocol Compliance**:
   - Real-time scoring of trainee responses against 4 SOP dimensions: Safety Protocol (35 pts), Empathy (25 pts), De-escalation (20 pts), and Referral Accuracy (20 pts).

---

## 2. Test Execution Matrix

| Test Module | Scope | Test Count | Key Invariants Tested |
| :--- | :--- | :---: | :--- |
| `test_simulation_metrics.py` | Unit | 6 | Levenshtein alignment, Unicode NFC Indic normalization, exact matches, deletion/insertion handling, noise profiles (8kHz, street, packet loss). |
| `test_simulation_catalog.py` | Unit | 3 | Scenario catalog coverage (24 scenarios, 11 languages, 4 risk bands), tag filtering, retrieval by ID. |
| `test_simulation_harness.py` | Integration | 3 | Single scenario execution, 100% critical safety recall, negation trap defense, automated smoke suite aggregation. |
| `test_simulation_sandbox.py` | Integration | 2 | Drill catalog listing, interactive session lifecycle, multi-turn SOP scoring, scorecard generation. |
| `test_simulation_api.py` | API Integration | 6 | `/v1/simulation/status`, `/scenarios`, `/scenarios/{id}`, `/benchmark/run`, `/wer/evaluate`, `/training/drills`, `/training/session/start`, `/training/session/{id}/turn`. |
| `test_simulation_scenarios.py`| Realtime Voice | 2 | End-to-end conversation simulation with mock telephony session. |
| `simulation-dashboard.spec.ts`| Browser E2E | 8 × 2 = 16 | Desktop Chrome and Mobile Chrome browser flows: tab switching, filter buttons, benchmark runner, WER token diff, operator training practice. |

**Total Phase 14 Backend Tests: 23 passed**
**Total Phase 14 Browser E2E Tests: 16 passed**
**Total Repository Regression: 356/356 passed (100%)**

---

## 3. How to Run Tests

### 3.1 Backend Tests
```bash
# Run Phase 14 simulation unit & integration tests
uv --directory apps/api run pytest -k simulation -v

# Run full backend regression (356 tests)
uv --directory apps/api run pytest -q
```

### 3.2 Frontend Type Check & Production Build
```bash
pnpm type-check
pnpm build
```

### 3.3 Browser E2E Tests (Playwright)
```bash
pnpm --filter @samved/web exec playwright test e2e/simulation-dashboard.spec.ts
```
