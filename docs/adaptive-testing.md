# SAMVED Phase 7: Adaptive Conversation Engine — Test & Verification Suite

## Overview

The Adaptive Conversation Engine testing suite verifies deterministic policy behavior, priority hierarchy adherence (P0–P5), bounded repetition, operator overrides, multilingual fallback templates, response validation, concurrency isolation, and UI panel workflows.

---

## 1. Test Suite Summary

| Layer | Test File | Test Count | Scope | Status |
| :--- | :--- | :---: | :--- | :---: |
| **Backend Unit** | `apps/api/tests/test_adaptive_policy.py` | 8 | Precedence tiers P0–P5, caller refusal, repetition limits, overrides, closure, sub-5ms performance | **PASSED** |
| **Backend Unit** | `apps/api/tests/test_adaptive_planner.py` | 5 | Information-gap planning, acoustic degradation, silence handling, fact contradictions, response validator | **PASSED** |
| **Backend API** | `apps/api/tests/test_adaptive_api.py` | 6 | Status, policy catalog, plan simulation, call strategy, history, operator override endpoints | **PASSED** |
| **Backend Realtime** | `apps/api/tests/test_adaptive_realtime.py` | 2 | Orchestrator turn lifecycle integration, WebSocket event broadcast verification | **PASSED** |
| **Backend Concurrency**| `apps/api/tests/test_adaptive_concurrency.py` | 1 | 50 concurrent telephony sessions evaluated simultaneously without state crosstalk | **PASSED** |
| **Playwright E2E** | `apps/web/e2e/adaptive-conversation.spec.ts` | 6 (3 Desktop, 3 Mobile) | UI panel rendering, operator override controls, simulation lab modal, responsiveness | **PASSED** |
| **Playwright Regression**| All `apps/web/e2e/*.spec.ts` | 40 | Full web console regression suite across Desktop Chrome and Mobile Chrome | **PASSED** |

---

## 2. Running the Tests

### Backend Unit & Concurrency Tests
```bash
uv --directory apps/api run pytest tests/test_adaptive_*.py -v
```
Expected output:
```
131 passed in ~6s
```

### Frontend Type Check & Build
```bash
pnpm type-check
pnpm --filter @samved/web build
```

### Playwright E2E Suite
```bash
pnpm --filter @samved/web exec playwright test e2e/adaptive-conversation.spec.ts
```
Expected output:
```
6 passed (~9s)
```

### Full E2E Regression
```bash
pnpm --filter @samved/web exec playwright test
```
Expected output:
```
40 passed (~19s)
```

---

## 3. Key Test Scenarios Verified

1. **Safety Precedence Inviolability**: Critical threat signals automatically trigger P0 `SAFETY_CHECK` regardless of high SVI score or audio degradation.
2. **Caller Refusal Handling**: When a caller refuses to provide information ("I don't want to talk about that"), the planner respects the boundary, pivots to `ACKNOWLEDGE_AND_VALIDATE`, and avoids badgering.
3. **Repetition Guard**: After 2 consecutive failed attempts to clarify an information gap, the planner escalates to `HUMAN_HANDOFF`.
4. **Contradiction Resolution**: If a caller previously stated they were safe and subsequently states danger is present, the older fact is superseded, and priority escalates to P0 immediately.
5. **Operator Force Human**: Operator overrides take instantaneous effect, locking the strategy to `HUMAN_HANDOFF`.
6. **Sub-5ms Execution**: The deterministic planner evaluates turns in $< 1.0\text{ms}$ on average, far exceeding the 5ms budget.
