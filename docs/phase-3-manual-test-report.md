# SAMVED Phase 3 Manual Verification & Test Report

**Phase:** Phase 3 — Realtime Transcript Platform + Operator Console + Localhost Runbook + Testing + Playwright + CI  
**Repository:** https://github.com/Balashanmugam30/samved  
**Date:** September 4, 2026  
**Environment:** Windows 11, Python 3.13.6 (uv), Node.js v22 (pnpm), Next.js 14, Playwright  

---

## 1. Automated Verification Summary

| Test Category | Suite / Command | Total Tests | Passed | Failed | Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Backend Unit & Contract** | `uv run pytest tests/` | 52 | 52 | 0 | **PASSED (100%)** |
| **Frontend Type Checking** | `pnpm type-check` | 3 packages | 3 | 0 | **PASSED (100%)** |
| **Frontend Production Build** | `pnpm build` | 9 routes | 9 | 0 | **PASSED (100%)** |
| **E2E Playwright Suite** | `pnpm test:e2e` | 12 | 12 | 0 | **PASSED (100%)** |

---

## 2. Test Cases & Execution Details

### TC-P3-01: Dedicated Operator WebSocket Handshake & Initial Snapshot
- **Endpoint:** `ws://localhost:8000/ws/operator`
- **Verification:** Client connects without authentication errors. Backend immediately dispatches an `OPERATOR_SNAPSHOT` envelope containing active calls array, recent calls array, and system mode (`DEV`).
- **Result:** **PASSED**. Initial snapshot delivered in < 5ms.

### TC-P3-02: Operator Dynamic Subscription & Cross-Call Isolation
- **Scenario:** Two concurrent operator WebSocket connections (`ws_a` on `call_a`, `ws_b` on `call_b`).
- **Verification:** When an event is broadcast on `call_a`, `ws_a` receives the turn, while `ws_b` does not observe any crosstalk.
- **Result:** **PASSED** (`tests/test_operator_ws.py::test_operator_subscription_and_cross_call_isolation`).

### TC-P3-03: Malformed WebSocket JSON Resilience
- **Scenario:** Client sends non-JSON text payload over `/ws/operator`.
- **Verification:** Backend catches exception gracefully, sends structured error envelope (`MALFORMED_JSON`), and keeps the WebSocket connection open for subsequent interactions.
- **Result:** **PASSED** (`tests/test_operator_ws.py::test_operator_ws_malformed_json_resilience`).

### TC-P3-04: REST Snapshot Endpoints
- **Endpoints Tested:**
  - `GET /v1/calls` → 200 OK, lists active and recent calls with masked phone numbers (`+91******3210`).
  - `GET /v1/calls/{call_id}` → 200 OK for active or completed call, 404 for unknown call.
  - `GET /v1/calls/{call_id}/transcript` → 200 OK with ordered caller and agent turns.
  - `GET /v1/calls/{call_id}/events` → 200 OK with bounded domain events history.
- **Result:** **PASSED** (`tests/test_calls_api.py`).

### TC-P3-05: Live Partial Draft to Final Transcript Transition
- **Scenario:** Voice simulation streaming `TRANSCRIPT_PARTIAL` drafts followed by `TRANSCRIPT_FINAL`.
- **Verification:** In the UI, the partial draft bubble displays an animated tentative draft state. Upon receipt of `TRANSCRIPT_FINAL`, the partial draft is cleared and atomically appended to the immutable transcript list with duplicate prevention.
- **Result:** **PASSED**. Verified in operator console and Playwright E2E.

### TC-P3-06: Event Timeline Category Filtering & Payload Inspector
- **Scenario:** Operator filters events by `TRANSCRIPT`, `CONVERSATION`, `ERRORS`, `LATENCY`.
- **Verification:** Filter pills update the event list reactively. Clicking "Inspect" opens a modal displaying the formatted JSON payload with syntax styling and a copy-to-clipboard button.
- **Result:** **PASSED**. Verified in Playwright E2E.

### TC-P3-07: Responsive Mobile Layout
- **Scenario:** Viewport resized to 375x667 (Mobile Chrome / Pixel 5).
- **Verification:** Operator Console header, call master list, and simulation controls render cleanly without horizontal overflow.
- **Result:** **PASSED** (`apps/web/e2e/operator-console.spec.ts` & `apps/web/e2e/smoke.spec.ts`).

---

## 3. Latency Metrics Verification

Under deterministic simulation in `DEV` mode:
- **Sarvam STT Mock Latency:** ~10ms
- **Gemini Mock Reasoning Latency:** ~12ms
- **Sarvam Bulbul TTS Mock Latency:** ~8ms
- **Total Turn Latency:** ~30ms (well under the 2500ms SLA)
