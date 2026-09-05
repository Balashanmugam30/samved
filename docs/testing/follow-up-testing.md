# Phase 12 Testing Documentation: Follow-up Workflow & Continuity Engine

## 1. Overview
SAMVED Phase 12 introduces human-supervised, consent-aware, auditable, and safe follow-up workflows for victims of domestic violence and harassment contacting the NHAA 14566 helpline.

### Absolute Operational Constraints Verified:
1. **Zero Autonomous Outbound Dialing**: No robot-callers, automated interactive voice response dialers, or AI-driven unprompted contact. All outbound callbacks must be initiated by an authorized human tele-counselor.
2. **Consent Supremacy**: Consent is explicitly recorded (`GRANTED`, `LIMITED`, `REQUESTED`, `NOT_APPLICABLE`, `REFUSED`, `REVOKED`). Silence or non-response never implies consent. Revocation or refusal cascades immediately to block all active contact workflows (`BLOCKED`).
3. **Safe Contact Windows**: Contact can strictly only be attempted within explicit caller-defined windows (e.g., `09:00-12:00`, `18:00-20:00`). Scheduling or executing contact outside safe windows is deterministically rejected by policy.
4. **Safety Supremacy**: Phase 4 Deterministic Safety Engine and Phase 5 SVI maintain absolute priority. A caller in `CRITICAL` safety state cannot have immediate danger deferred into a future follow-up task.
5. **Bounded Recurrence & Max Attempt Caps**: Recurrence rules (`ONCE`, `DAILY`, `WEEKLY`, `CUSTOM_BOUNDED`) are strictly bounded. Maximum contact attempts are enforced (default: 3, hard cap: 5), transitioning unresolved tasks to `MISSED` or requiring human supervisor review.

---

## 2. Test Pyramid & Execution Summary

| Test Layer | Test Files | Total Tests | Passed | Execution Time |
| :--- | :--- | :--- | :--- | :--- |
| **Backend Unit & Domain** | 4 files (`test_followup_models.py`, `test_followup_policy.py`, `test_followup_consent.py`, `test_followup_scheduler.py`) | 14 tests | 14 | 0.15s |
| **Backend Service & State Machine** | 3 files (`test_followup_state_machine.py`, `test_followup_concurrency.py`, `test_followup_idempotency.py`) | 9 tests | 9 | 0.11s |
| **Backend Integration & Audit** | 4 files (`test_followup_api.py`, `test_followup_audit.py`, `test_followup_case_integration.py`, `test_followup_realtime.py`) | 11 tests | 11 | 0.13s |
| **Full Backend Regression** | All phases (0 through 12) | **287 tests** | **287** | **9.11s** |
| **Frontend Playwright E2E** | `e2e/follow-up.spec.ts` (Desktop Chrome + Mobile Chrome) | 24 tests | 24 | 21.4s |
| **Full Frontend Regression** | 11 Playwright spec files across all phases | **128 tests** | **128** | **~1.5m** |

---

## 3. Backend Test Coverage Breakdown

### `apps/api/tests/test_followup_models.py`
- `test_followup_model_defaults_and_validation`: Validates default state (`DRAFT`), valid UUID generation, and ISO UTC timestamp generation.
- `test_contact_preferences_validation`: Validates safe contact preferences, channel validation, and boolean flags (`human_only`, `no_voicemail`, `no_text`).
- `test_followup_attempt_payload`: Validates attempt number sequence, channel, contact result, notes, and operator attribution.

### `apps/api/tests/test_followup_policy.py`
- `test_purpose_validation`: Ensures empty or whitespace-only purposes are rejected; requires actionable context.
- `test_channel_consent_compatibility`: Ensures SMS/phone outreach without explicit consent is rejected; internal tasks remain allowed.
- `test_safe_window_policy_validation`: Rejects scheduling outside safe contact windows.
- `test_duplicate_followup_prevention`: Detects and flags duplicate pending follow-ups for the same case with identical purpose.
- `test_max_attempts_cap`: Verifies that attempting contact beyond configured `max_attempts` is rejected and flagged.
- `test_safety_engine_supremacy`: Confirms `CRITICAL` safety state cannot have life-threatening emergencies deferred to follow-ups.

### `apps/api/tests/test_followup_consent.py`
- `test_consent_state_transitions`: Validates explicit state transitions (`REQUESTED` -> `GRANTED`, `GRANTED` -> `REVOKED`).
- `test_consent_revocation_blocks_active_tasks`: Verifies that revoking case consent immediately halts all scheduled/in-progress follow-ups and marks them `BLOCKED`.
- `test_consent_refusal_blocks_creation`: Prevents creating outbound contact tasks when consent is in `REFUSED` state.

### `apps/api/tests/test_followup_scheduler.py`
- `test_scheduler_frozen_clock`: Verifies deterministic evaluation of due/ready states using `FrozenTimeProvider`.
- `test_scheduler_safe_window_matching`: Verifies UTC time window calculations against caller safe hours.
- `test_bounded_recurrence_calculation`: Validates next recurrence calculation for `DAILY`, `WEEKLY`, and `CUSTOM_BOUNDED` with maximum occurrence caps.

### `apps/api/tests/test_followup_state_machine.py`
- `test_valid_lifecycle_transitions`: Validates `DRAFT` -> `PENDING_APPROVAL` -> `SCHEDULED` -> `READY` -> `IN_PROGRESS` -> `COMPLETED`.
- `test_invalid_lifecycle_transition_rejection`: Rejects illegal transitions (e.g. `COMPLETED` -> `IN_PROGRESS`, `CANCELLED` -> `READY`).
- `test_reschedule_transition`: Validates rescheduling from `READY` or `IN_PROGRESS` back to `SCHEDULED`.

### `apps/api/tests/test_followup_concurrency.py`
- `test_concurrent_attempt_recording`: Simulates concurrent attempt recordings on the same follow-up task using Python `asyncio.gather`, verifying atomic attempt number incrementing and thread safety.

### `apps/api/tests/test_followup_idempotency.py`
- `test_idempotent_task_creation`: Verifies that identical requests with the same `Idempotency-Key` header return cached responses without duplicating records or audit events.

### `apps/api/tests/test_followup_audit.py`
- `test_followup_audit_trail_immutability`: Ensures all mutations (`CREATED`, `SCHEDULED`, `ATTEMPTED`, `COMPLETED`, `REVOKED`) write append-only records with actor attribution, timestamp, and metadata.

### `apps/api/tests/test_followup_case_integration.py`
- `test_case_graph_followup_linkage`: Verifies that creating a follow-up links an entity of type `FOLLOW_UP` and relationship `HAS_FOLLOW_UP` into the Case Knowledge Graph.
- `test_multi_agent_recommendation_worker`: Verifies that the `FollowupRecommendationAgent` correctly synthesizes safety, SVI, and conversation gaps to produce compliant follow-up plans.

### `apps/api/tests/test_followup_realtime.py`
- `test_realtime_websocket_event_broadcast`: Verifies that follow-up mutations emit canonical `EventEnvelope` payloads (`FOLLOWUP_CREATED`, `FOLLOWUP_STARTED`, etc.) to connected operator consoles.

---

## 4. Playwright E2E Suite Breakdown (`apps/web/e2e/follow-up.spec.ts`)

| Test ID | Test Scenario | Viewports |
| :--- | :--- | :--- |
| **TC-FOL-01** | Workqueue Panel renders with KPI metrics strip (`total_active`, `due_today`, `overdue`, `blocked`, `completed_today`) and governance badges (`HUMAN_SUPERVISED`, `CONSENT_GUARDED`). | Desktop Chrome, Mobile Chrome |
| **TC-FOL-02** | Follow-up task cards render with correct attributes (ID, type, status, priority, consent state, channel, safe contact window). | Desktop Chrome, Mobile Chrome |
| **TC-FOL-03** | Workqueue filter pills filter tasks by lifecycle status (`ALL`, `SCHEDULED`, `READY`, `IN_PROGRESS`, `BLOCKED`, `COMPLETED`). | Desktop Chrome, Mobile Chrome |
| **TC-FOL-04** | Tele-counselor can schedule new follow-up via Create Follow-up Modal with clinical context, channel, and safe window. | Desktop Chrome, Mobile Chrome |
| **TC-FOL-05** | Counselor can transition task to `IN_PROGRESS` via Start Task. | Desktop Chrome, Mobile Chrome |
| **TC-FOL-06** | Counselor can record contact attempt with notes, channel, and contact result in the Details Drawer. | Desktop Chrome, Mobile Chrome |
| **TC-FOL-07** | Counselor can reschedule follow-up with structured reason and target ISO timestamp. | Desktop Chrome, Mobile Chrome |
| **TC-FOL-08** | Counselor can mark follow-up completed with clinical outcome (`CONTACTED_SUCCESSFULLY`, `REFERRED`, etc.). | Desktop Chrome, Mobile Chrome |
| **TC-FOL-09** | Caller consent revocation halts and blocks contact workflow immediately (`BLOCKED`). | Desktop Chrome, Mobile Chrome |
| **TC-FOL-10** | Audit trail modal displays append-only immutable event logs with actor, action, and JSON payload. | Desktop Chrome, Mobile Chrome |
| **TC-FOL-11** | Case Intelligence panel displays linked follow-ups badge (`data-testid="case-followup-count"`). | Desktop Chrome, Mobile Chrome |
| **TC-FOL-12** | Event stream timeline supports `FOLLOWUP` filter category and highlights follow-up events with emerald styling. | Desktop Chrome, Mobile Chrome |

---

## 5. Verification Commands

```bash
# 1. Run all Phase 12 backend unit and integration tests
pnpm --filter @samved/api test

# 2. Run dedicated follow-up test suite
cd apps/api && poetry run pytest tests/test_followup_*.py -v

# 3. Verify TypeScript types in web console
pnpm --filter @samved/web type-check

# 4. Run Phase 12 Playwright E2E tests
pnpm --filter @samved/web exec playwright test e2e/follow-up.spec.ts

# 5. Run full Playwright regression suite
pnpm --filter @samved/web exec playwright test --workers=4
```
