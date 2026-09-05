# SAMVED Phase 9 — Multi-Agent Orchestration Testing Guide

This document details the testing architecture, test suites, and validation procedures for SAMVED Phase 9: **Multi-Agent Orchestration & Specialized AI Coordination Layer**.

---

## 1. Testing Philosophy & Scope

SAMVED is a safety-first, explainable helpline triage system. LLM and advisory sub-agents are strictly subordinate to:
1. Human Tele-Counselors (absolute operational authority).
2. Phase 4 Deterministic Safety Engine (absolute programmatic authority over safety states).
3. Phase 5 SVI Engine (calibrated quantitative risk index).

### Core Testing Mandates:
- **Zero Unsupervised External Action**: No sub-agent can autonomously dispatch emergency services or provide ungrounded clinical/legal diagnoses.
- **Deterministic Precedence**: Any discrepancy between conversation cues and the Safety Engine strictly resolves in favor of the Safety Engine.
- **Bounded Latency**: Full multi-agent orchestration must complete within $\le 250\text{ms}$ per turn.
- **Barge-in / Stale Result Protection**: Interruptions cancel in-flight worker tasks and prevent stale responses from affecting conversation flow.
- **Graceful Degradation**: If non-critical workers fail or time out, fallback summaries are generated without halting the call.

---

## 2. Test Suites Overview

| Test Suite | File | Tests | Focus Area |
| :--- | :--- | :---: | :--- |
| **Agent Registry** | `apps/api/tests/test_agent_registry.py` | 2 | Registration, capability indexing, lookup, duplicate handling. |
| **Worker Contracts** | `apps/api/tests/test_worker_contracts.py` | 6 | All 6 workers: SafetyContext, AcousticContext, LanguageContext, ConversationContext, OperatorBriefing, SupportOptions stub. |
| **Capability Router** | `apps/api/tests/test_capability_router.py` | 3 | Deterministic DAG stage planning, fast-track high-urgency routing, custom agent filters. |
| **DAG Executor** | `apps/api/tests/test_dag_executor.py` | 3 | Bounded timeouts, cancellation tokens, worker exception resilience. |
| **Output Validation** | `apps/api/tests/test_output_validation.py` | 3 | Schema checks, identifier validation, prohibited claim sanitization, safety immutability. |
| **Context Aggregation** | `apps/api/tests/test_context_aggregation.py` | 1 | Conflict resolution hierarchy, safety precedence override, evidence aggregation. |
| **Audit Logger** | `apps/api/tests/test_orchestration_audit.py` | 2 | In-memory audit logging, bounded queues, call-specific lookup. |
| **Multi-Agent Coordinator** | `apps/api/tests/test_multi_agent_orchestrator.py` | 2 | End-to-end turn flow, events, latency budgeting, barge-in cancellation. |
| **Orchestration REST API** | `apps/api/tests/test_orchestration_api.py` | 4 | `/v1/orchestration/status`, `/agents`, `/calls/{id}`, `/history`, `/refresh`, `/plan`. |
| **Orchestration Safety** | `apps/api/tests/test_orchestration_safety.py` | 2 | Non-overridable safety states, Phase 10 support options boundary guard. |
| **Realtime Integration** | `apps/api/tests/test_orchestration_realtime.py` | 1 | Realtime turn flow integration with `ConversationOrchestrator` and WebSocket broadcaster. |
| **Playwright E2E Suite** | `apps/web/e2e/orchestration.spec.ts` | 8 | Multi-agent status panel, operator briefing card, refresh action, degraded mode, timeline filter. |

---

## 3. Running Backend Tests

```bash
# Run all orchestration test suites
uv --directory apps/api run pytest tests/test_agent_registry.py tests/test_worker_contracts.py tests/test_capability_router.py tests/test_dag_executor.py tests/test_output_validation.py tests/test_context_aggregation.py tests/test_orchestration_audit.py tests/test_multi_agent_orchestrator.py tests/test_orchestration_api.py tests/test_orchestration_safety.py tests/test_orchestration_realtime.py -v

# Run entire backend test suite (187 tests)
uv --directory apps/api run pytest -v
```

---

## 4. Running Frontend E2E Tests

```bash
# Run Phase 9 orchestration Playwright tests (Desktop & Mobile)
pnpm --filter @samved/web test:e2e e2e/orchestration.spec.ts

# Run all Playwright E2E suites (68 tests)
pnpm --filter @samved/web test:e2e
```

---

## 5. Verification Results Summary

- **Backend Pytest**: **187 / 187 tests PASSED (100%)**
- **TypeScript Type Check**: **0 errors** (`tsc --noEmit`)
- **Next.js Production Build**: **Clean build succeeded**
- **Playwright E2E Suite**: **68 / 68 tests PASSED (100%)** across Desktop Chrome and Mobile Chrome viewports.
