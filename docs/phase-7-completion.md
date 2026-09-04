# SAMVED Phase 7 Completion Report

## Phase Overview

- **Phase**: 7 of 17
- **Name**: Adaptive Conversation Engine — Safety-First, Explainable, Multilingual, Human-Supervised
- **Objective**: Implement a deterministic conversational policy layer answering "Given known state and structured evidence, what should SAMVED do next?", upholding strict policy precedence (P0–P5), information-gap planning, bounded repetition, contradiction handling, operator overrides, multilingual localized templates, and full UI operator controls.
- **Repository**: `https://github.com/Balashanmugam30/samved`
- **Branch**: `main`

---

## Completed Deliverables

### 1. Core Adaptive Engine Package (`apps/api/app/adaptive/`)
- `models.py`:
  - Enums: `AdaptiveAction`, `AdaptivePriority` (P0–P5), `AdaptiveReasonCode`, `FactPriority`, `OperatorOverrideAction`, `ConversationPhase`.
  - Pydantic models: `ConversationFact`, `OperatorOverride`, `ConversationStrategy`, `AdaptivePlanRequest`, `AdaptiveStatusResponse`, `AdaptivePolicyResponse`, `AdaptiveHistoryResponse`.
- `templates.py`:
  - Versioned deterministic localized templates for `ta-IN` (Tamil), `hi-IN` (Hindi), and `en-IN` (Indian English) covering safety checks, danger checks, location requests, support options, human handoffs, audio clarifications, and graceful closure.
- `evidence.py`:
  - Deterministic caller intent extraction (`requests_human`, `refuses_question`, `requests_pause`, `affirms_danger`, `affirms_safe`).
  - Fact extraction and contradiction handling (superseding stale facts with explainable reason codes).
- `response_policy.py`:
  - Action-specific policies enforcing tone, question limits ($\le 1$), and prohibited claims.
- `validator.py`:
  - `ResponseValidator` verifying LLM realization length ($\le 45$ words), question marks ($\le 1$), and screening against unauthorized emergency dispatch or clinical diagnostic statements, with instantaneous deterministic fallback substitution.
- `planner.py`:
  - `AdaptivePlanner` implementing P0–P5 priority cascades with sub-millisecond evaluation latency.
- `service.py`:
  - `AdaptiveEngine` singleton managing call session states, facts, attempt counts, overrides, and strategy trajectory histories.

### 2. Pipeline & Orchestrator Integration
- `apps/api/app/realtime/session_manager.py`:
  - Per-session adaptive strategy and trajectory tracking.
  - Operator override application and retrieval methods (`apply_call_operator_override`, `get_call_adaptive`, `get_call_adaptive_history`).
- `apps/api/app/realtime/conversation_orchestrator.py`:
  - Turn-level evaluation of `adaptive_engine.evaluate_turn()` following acoustic and SVI updates.
  - Immediate broadcast of `ADAPTIVE_STRATEGY_SELECTED` over `/ws/operator`.
  - Application of `ResponseValidator` on LLM realizations.

### 3. REST API Suite (`apps/api/app/api/v1/adaptive.py`)
- `GET /v1/adaptive/status`: Engine operational health, version, policy count, and non-clinical guarantee.
- `GET /v1/adaptive/policy`: Catalog of all 17 actions, priority tiers, and reason codes.
- `POST /v1/adaptive/plan`: Standalone deterministic planning endpoint for simulation and testing.
- `GET /v1/adaptive/calls/{call_id}`: Active strategy for a given call.
- `GET /v1/adaptive/calls/{call_id}/history`: Turn-by-turn strategy history for a given call.
- `POST /v1/adaptive/calls/{call_id}/override`: Operator manual controls (`operator_force_human`, `operator_pause_adaptive`, `operator_resume_adaptive`, `operator_request_safety_check`).

### 4. Operator Console UI (`apps/web/src/app/calls/page.tsx`)
- **Adaptive Conversation Panel (`data-testid="adaptive-panel"`)**:
  - Live Action badge (`data-testid="adaptive-strategy"`) and Priority badge (`data-testid="adaptive-priority"`).
  - Target information gap indicator (`data-testid="adaptive-target"`).
  - Confidence percentage gauge (`data-testid="adaptive-confidence"`).
  - Operator override status badge (`data-testid="adaptive-override-badge"`).
  - Quick override buttons: `btn-override-human`, `btn-override-pause`, `btn-override-safety`.
  - Deterministic reason code chips (`data-testid="adaptive-reasons"` / `data-testid="adaptive-reason-chip"`).
  - Structured evidence chips (`data-testid="adaptive-evidence"` / `data-testid="adaptive-evidence-chip"`).
  - Recent turn trajectory breadcrumb (`data-testid="adaptive-history"` / `data-testid="adaptive-history-item"`).
  - Non-clinical disclaimer (`data-testid="adaptive-disclaimer"`).
- **Adaptive Simulation Lab Modal (`data-testid="adaptive-lab-modal"`)**:
  - Six preset scenario buttons: `preset-danger-unknown`, `preset-high-svi`, `preset-poor-audio`, `preset-caller-human`, `preset-caller-refusal`, `preset-closure-ready`.
  - Parameter inputs: caller utterance, safety state, acoustic quality, language, and SVI slider (0–100).
  - Live evaluation runner (`data-testid="run-adaptive-eval"`).
  - Results container (`data-testid="adaptive-lab-result"`) displaying action, priority, target, reasons, and deterministic fallback realization.

### 5. Verification & Test Metrics
- **Backend Tests**: 131 passed in 6.22s (100% pass rate).
- **Playwright Tests**: 40 passed in 19.2s across Desktop Chrome and Mobile Chrome (100% pass rate).
- **Docker Compose**: Configuration validated via `docker compose config`.
- **Docker MCP**: Profile `samved_dev` verified.
