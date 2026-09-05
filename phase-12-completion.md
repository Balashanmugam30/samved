# SAMVED — Phase 12 Milestone Completion Document
**Follow-up Workflow & Continuity Engine — Human-Supervised, Consent-Aware, Auditable, Safe**

- **Date**: September 2026
- **Status**: COMPLETE ✅
- **Repository**: [Balashanmugam30/samved](https://github.com/Balashanmugam30/samved)
- **Branch**: `main`

---

## 1. Executive Summary

Phase 12 delivers the **Follow-up Workflow & Continuity Engine** for SAMVED, establishing a human-supervised, consent-aware, safety-constrained, and cryptographically auditable operational layer for victim support continuity under the National Helpline Against Abuse (NHAA 14566).

### Core Architectural Doctrine:
$$\text{Operator / Approved Workflow} \to \text{Follow-up Plan} \to \text{Consent + Safety + Policy Validation} \to \text{Scheduled Task} \to \text{Reminder / Human Action} \to \text{Outcome} \to \text{Audit Trail}$$

### Absolute Operational & Safety Boundaries Verified:
1. **Zero Autonomous Outbound Dialing / Robot-Calling**:
   - Outbound telephony contact is strictly prohibited from automated initiation. Every outbound call must be placed manually by a licensed human tele-counselor.
2. **Consent Supremacy & Silence Invariance**:
   - Silence or non-response never implies consent. Consent states are explicitly tracked (`GRANTED`, `LIMITED`, `REQUESTED`, `NOT_APPLICABLE`, `REFUSED`, `REVOKED`).
   - Any refusal or revocation immediately transitions active contact tasks to `BLOCKED` and halts all outreach workflows.
3. **Strict Safe Contact Windows**:
   - Outreach is deterministically restricted to caller-specified safe contact windows (e.g., `09:00-12:00`, `18:00-20:00`). Scheduling or executing outside safe hours is blocked by policy.
4. **Deterministic Safety Precedence**:
   - Phase 4 Safety Engine and Phase 5 SVI maintain unconditional priority. An acute life-threatening emergency (`CRITICAL` safety state) cannot be deferred to future follow-up.
5. **Bounded Recurrence & Attempt Caps**:
   - Supported recurrence rules (`ONCE`, `DAILY`, `WEEKLY`, `CUSTOM_BOUNDED`) are capped. Contact attempts are strictly capped (default 3, hard max 5), preventing repeated unwanted caller harassment.
6. **Immutable Cryptographic Audit Trail**:
   - Every mutation, scheduling event, attempt, outcome, and consent revocation is written to an append-only audit trail with actor attribution and timestamps.

---

## 2. Completed Architecture & Deliverables

### 2.1 Backend Follow-up Subsystem (`apps/api/app/followup/`)
1. **Domain Models & Enums (`models.py`)**:
   - Enums: `FollowupType`, `FollowupStatus`, `ConsentState`, `FollowupPriority`, `ContactChannel`, `ContactResult`, `FollowupOutcome`, `RecurrenceRule`.
   - Domain Pydantic models: `ContactPreferences`, `FollowupAttempt`, `FollowupConsent`, `FollowupRecord`, `FollowupEvent`, `FollowupWorkqueueSummary`.
2. **Deterministic Policy Validation (`policy.py`)**:
   - Purpose string validation, channel-consent compatibility, safe window regex and interval checks, duplicate follow-up prevention, max attempt enforcement, and safety engine supremacy.
3. **Explicit Consent Transition Model (`consent.py`)**:
   - Finite state machine for consent transitions, and `apply_consent_revocation` cascade halting all active follow-ups under a case.
4. **Time & Recurrence Scheduler (`scheduler.py`)**:
   - Abstract `TimeProvider` interface (`SystemTimeProvider`, `FrozenTimeProvider`), ISO-8601 UTC parsing, safe contact window matching, and bounded recurrence rule calculations.
5. **Thread-Safe Audit Logger (`audit.py`)**:
   - In-memory ring-buffer audit logger (`FollowupAuditLogger`) recording actor, action, timestamp, and details.
6. **Canonical Event Emitter (`events.py`)**:
   - Constructs canonical `EventEnvelope` payloads (`FOLLOWUP_CREATED`, `FOLLOWUP_STARTED`, etc.) with `session_id` and `call_id`.
7. **Input Validation & Sanitization (`validators.py`)**:
   - Defense against IDOR, safe contact window regex validation, and script injection filtering.
8. **Follow-up Lifecycle Service (`service.py`)**:
   - `FollowupService` singleton orchestrating `create_followup`, `approve_followup`, `schedule_followup`, `assign_followup`, `start_followup`, `record_attempt`, `complete_followup`, `reschedule_followup`, `cancel_followup`, `revoke_consent`, `evaluate_all_tasks`, and `get_workqueue_summary`. Seeds default fixtures for `fol-1001` and `fol-1002`.

### 2.2 Shared Schemas & Contracts
- **`packages/schemas/src/events.ts`**:
  - Added 15 `FOLLOWUP_*` event types to `EventType`.
  - Added `FOLLOW_UP` to `EntityType`, `HAS_FOLLOW_UP` and `BASED_ON` to `RelationshipType`.
  - Exported TypeScript enums and payload interfaces for all follow-up contracts.
- **`apps/api/app/schemas/events.py`**:
  - Mirrored Python Pydantic models aligning 1:1.

### 2.3 Database Migration (`infra/db/init.sql`)
Created 5 relational tables with foreign keys and performance indexes:
- `followup_consents`: Tracks consent state and restrictions per case.
- `followup_preferences`: Caller safe channels, windows, and flags.
- `followups`: Primary task records with lifecycle states, timings, attempts, and outcomes.
- `followup_attempts`: Log of individual contact attempts with results and notes.
- `followup_events`: Append-only audit log of all follow-up workflow mutations.

### 2.4 Multi-Agent Orchestration & Case Integration
- **`FollowupRecommendationAgent` (`apps/api/app/orchestration/workers/followup_recommendation.py`)**:
  - Specialized agent analyzing call safety signals, SVI, acoustic distress, and knowledge citations to produce recommended follow-up actions.
  - Registered in worker registry and taxonomy.
- **`OperatorBriefingAgent` Enrichment**:
  - Briefing cards enriched with structured follow-up recommendations.
- **Case Knowledge Graph Linkage**:
  - Follow-up creation adds an entity (`EntityType.FOLLOW_UP`) and relationship (`RelationshipType.HAS_FOLLOW_UP`) into the case graph.

### 2.5 REST API Endpoints (`/v1/followups`)
- `GET /v1/followups/status` — Subsystem status and health.
- `GET /v1/followups/summary` — Workqueue summary metrics (`total_active`, `due_today`, `overdue`, `blocked`, `completed_today`).
- `GET /v1/followups` — Filterable list of follow-ups with pagination.
- `GET /v1/cases/{case_id}/followups` — All follow-ups for a specific case.
- `POST /v1/cases/{case_id}/followups` — Schedule a new follow-up task.
- `GET /v1/followups/{id}` — Detailed task view with attempt history.
- `POST /v1/followups/{id}/approve` — Supervisor approval.
- `POST /v1/followups/{id}/schedule` — Schedule task for execution.
- `POST /v1/followups/{id}/assign` — Assign task to tele-counselor.
- `POST /v1/followups/{id}/start` — Transition task to `IN_PROGRESS`.
- `POST /v1/followups/{id}/attempt` — Record human contact attempt.
- `POST /v1/followups/{id}/complete` — Complete task with clinical outcome.
- `POST /v1/followups/{id}/reschedule` — Reschedule task with reason.
- `POST /v1/followups/{id}/cancel` — Cancel task with structured reason.
- `POST /v1/cases/{case_id}/followups/revoke-consent` — Revoke consent and block active tasks.
- `GET /v1/followups/{id}/audit` — Retrieve immutable audit trail.

### 2.6 Frontend Operator Workstation (`apps/web/src/app/calls/page.tsx`)
- **Follow-up Workqueue Panel (`data-testid="followup-workqueue-panel"`)**:
  - Governance badges: `HUMAN_SUPERVISED`, `CONSENT_GUARDED`.
  - Metrics strip: `workqueue-stat-active`, `workqueue-stat-due`, `workqueue-stat-overdue`, `workqueue-stat-blocked`, `workqueue-stat-completed`.
  - Filter pills: `followup-filter-all`, `followup-filter-scheduled`, `followup-filter-ready`, `followup-filter-inprogress`, `followup-filter-blocked`, `followup-filter-completed`.
  - Card list: `followup-list`, with individual cards displaying type, status, priority, consent state, channel, safe contact window, attempt counter, and purpose.
  - Interactive actions: Start task, Record attempt, Complete, Reschedule, Cancel, Revoke consent.
- **Create Follow-up Modal (`data-testid="create-followup-modal"`)**:
  - Form with type, priority, purpose, channel, scheduled time, due deadline, safe contact window, consent state, max attempts, and human-only checkbox.
- **Follow-up Details Drawer (`data-testid="followup-details-drawer"`)**:
  - Full metadata, attempt history list (`followup-attempts-list`), attempt recording form, reschedule form, complete form, and consent revocation control.
- **Follow-up Audit Modal (`data-testid="followup-audit-modal"`)**:
  - Append-only event log list with action, actor, timestamp, and JSON details.
- **Case Intelligence Integration**:
  - Added `data-testid="case-followup-count"` badge displaying active follow-ups linked to the current case.
- **Realtime Timeline Stream**:
  - Added `FOLLOWUP` filter button (`timeline-filter-FOLLOWUP`) and emerald styling for follow-up events.

---

## 3. Verification & Test Metrics

### Backend Test Suite (Pytest)
- Dedicated Follow-up test files: **11 files, 34 tests** — **34 passed in 0.39s (100% pass rate)**.
- Full backend regression across all 12 phases: **287 passed in 9.11s (100% pass rate)**.

### Frontend Playwright E2E Suite
- Dedicated Follow-up test suite (`apps/web/e2e/follow-up.spec.ts`):
  - Desktop Chrome: 12 tests passed.
  - Mobile Chrome: 12 tests passed.
  - Total: **24 passed in 21.4s (100% pass rate)**.
- Full Playwright regression across 11 test suites: **128 passed (100% pass rate)**.

### Build & Docker Verification
- `pnpm --filter @samved/schemas build`: Clean compilation, 0 errors.
- `pnpm --filter @samved/web type-check`: 0 TypeScript errors.
- `pnpm --filter @samved/web build`: Successful production Next.js build.
- `docker compose config`: 100% valid YAML configuration.

---

## 4. Documentation & Operational Runbooks
- `docs/architecture/phase-12-follow-up-workflow.md`: Architecture specification.
- `docs/testing/follow-up-testing.md`: Comprehensive test strategy and edge cases.
- `docs/runbooks/follow-up.md`: Counselor operational runbook.
- `docs/runbooks/localhost.md`: Added Section 9 (Follow-up Workflows).
- `docs/roadmap.md`: Updated Phase 12 status to COMPLETE ✅.
- `README.md`: Updated capabilities, test commands, and non-clinical boundaries.

---

## 5. Conclusion & Next Phase
Phase 12 is fully completed, verified, and integrated into SAMVED. The platform now possesses safe, consent-aware case continuity capabilities.

**Next Milestone**: Phase 13 — District Analytics, Geospatial Aggregation, and Hotspot Intelligence (Human-Supervised, Privacy-Preserving).
