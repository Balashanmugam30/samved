# SAMVED Phase 11 — Case Intelligence & Knowledge Graph Testing Guide

This document details the testing architecture, test suites, edge case validations, and security boundaries for SAMVED Phase 11: **Case Intelligence & Knowledge Graph — Explainable Entity/Relationship Layer**.

---

## 1. Testing Philosophy & Scope

SAMVED Case Intelligence operates under a strict, non-negotiable legal, privacy, and epistemic doctrine:
1. **Epistemic Boundaries**:
   - The graph models caller-reported evidence and claims, **NOT** objective truth, guilt, or legal liability.
   - Every entity and relationship explicitly maintains `claim_status` (`REPORTED`, `CORROBORATED`, `CONTESTED`, `SUPERSEDED`).
2. **Zero Guilt Accusations & Role Normalization**:
   - Prohibited punitive or legal roles (e.g., `OFFENDER`, `PERPETRATOR`, `GUILTY`, `ACCUSED`) are structurally rejected or normalized to `REPORTED_ACTOR` with `claim_status = REPORTED`.
3. **Deterministic Safety Supremacy**:
   - Phase 4 Safety Engine and Phase 5 SVI retain unconditional precedence. Safety events are ingested as immutable, read-only evidence nodes (`SAFETY_SIGNAL`, `SVI_SIGNAL`) and cannot be suppressed or edited.
4. **Human Tele-Counselor Supervision**:
   - Extraction yields **Candidate Relationships** (`is_candidate = true`). Candidates remain isolated until confirmed or rejected by a licensed human tele-counselor.
5. **Cryptographic Provenance & Temporal Grounding**:
   - Every node and edge is cryptographically anchored by a SHA-256 hash of verbatim call dialogue excerpts with byte/character offsets.
   - Relationships have explicit temporal validity intervals (`valid_from`, `valid_to`). Conflicting facts do not delete history; they supersede prior edges with full audit preservation.
6. **Zero Autonomous Dispatch**:
   - No autonomous police calls, emergency dispatch, or external notifications can be initiated by the knowledge graph.

---

## 2. Test Suites Overview

### 2.1 Backend Unit & Integration Suites (`apps/api/tests/`)

| Test Suite | File | Tests | Focus Area |
| :--- | :--- | :---: | :--- |
| **Case Models** | `test_case_models.py` | 3 | Pydantic validation for `CaseEntity`, `CaseRelationship`, `CaseEntityCandidate`, `CaseEvent`, and graph response schemas. |
| **Case Entities** | `test_case_entities.py` | 3 | Entity registration, deduplication by canonical name and type, role normalization, and evidence link assembly. |
| **Case Relationships** | `test_case_relationships.py` | 3 | Directed relationship insertion, candidate generation, counselor confirmation/rejection workflow, and confidence scoring. |
| **Provenance Integrity** | `test_case_provenance.py` | 3 | SHA-256 cryptographic hashing, verbatim excerpt substring verification, tamper detection, and offset bounds validation. |
| **Temporal Logic** | `test_case_timeline.py` | 3 | ISO-8601 interval checking, `is_edge_active_at` temporal filtering, superseding chains (`supersede_edge`), and timeline event sorting. |
| **Case REST API** | `test_case_api.py` | 4 | Complete API endpoint test for `/cases`, `/cases/{id}`, `/graph`, `/candidates/{id}/confirm`, `/candidates/{id}/reject`, and `/integrity`. |
| **Safety & SVI Linking** | `test_case_linking.py` | 3 | Verification that Phase 4 safety events and Phase 5 SVI assessments link as unalterable evidence nodes in the case graph. |
| **Concurrency & Thread Safety** | `test_case_concurrency.py` | 3 | Thread-safe concurrent entity ingestion, candidate confirmations, and race condition prevention using atomic locks. |
| **Epistemic & Prompt Security** | `test_case_security.py` | 4 | Rejection of guilt/punitive claims, prompt injection defenses via `<untrusted_dialogue>` delimiters, role sanitization, and PII protection. |
| **Graph Queries & Subgraphs** | `test_case_graph_queries.py` | 4 | Depth-bounded subgraph extraction (1-4 hops), entity neighbor traversals, cycle handling, and dangling edge detection. |
| **Graph Extraction Agent** | `test_case_graph_extraction.py` | 3 | Phase 9 multi-agent worker integration, conservative extraction heuristics, and negation handling across English, Hindi, and Tamil. |

**Total Phase 11 Backend Tests**: **36 tests** (bringing total API test suite to **253 tests** with 100% pass rate).

---

### 2.2 Frontend Playwright E2E Suite (`apps/web/e2e/case-intelligence.spec.ts`)

The E2E suite exercises the Operator Workstation Case Intelligence Panel across both Desktop Chrome and Mobile Chrome viewports:

| Test Case | Description | Verification Points |
| :--- | :--- | :--- |
| **TC-CASE-01** | Case Intelligence Panel Rendering | Verifies panel rendering, case ID header (`case-1001`), call ID, status badge (`OPEN`), and epistemic disclaimer badges. |
| **TC-CASE-02** | Metrics Summary Strip | Validates display of entity counts, active relationship edges, and pending candidate relationship counts. |
| **TC-CASE-03** | Graph Visualizer Rendering | Verifies rendering of entity nodes (`entity-node-*`) with role badges and directed relationship edges (`graph-edge-*`). |
| **TC-CASE-04** | Node Inspector & Provenance | Clicking an entity opens the Node Inspector drawer, displaying entity metadata, claim status, and SHA-256 evidence hash anchors. |
| **TC-CASE-05** | Edge Inspector & Validity | Clicking a relationship edge opens the Edge Inspector drawer, showing directed relationship type, confidence, and temporal validity. |
| **TC-CASE-06** | Counselor Candidate Confirmation | Displays candidate relationship card with verbatim excerpt, allows clicking "Confirm", and graduates candidate to active edge. |
| **TC-CASE-07** | Depth Selector Traversal | Tests adjusting the graph traversal depth selector (1 to 4 hops) and verifies UI query updates. |
| **TC-CASE-08** | Audit Trail Modal | Opens the Case Audit modal (`case-audit-modal`) and verifies immutable chronological mutation records. |
| **TC-CASE-09** | Timeline Event Stream Filtering | Verifies that the event timeline filter includes the `CASE` category pill and displays `CASE_*` event cards. |
| **TC-CASE-10** | Epistemic Safety Notice | Verifies persistent visibility of the epistemic disclaimer: *"Case Intelligence reflects reported dialogue and evidence, not legal conclusions or guilt."* |

**Total Phase 11 E2E Runs**: **20 tests** (10 Desktop Chrome + 10 Mobile Chrome) with 100% pass rate.
**Total Full Web Regression**: **104 tests** across all 10 spec files passing cleanly.

---

## 3. Running Backend Tests

```bash
# Run all Phase 11 Case Intelligence unit and integration tests
uv --directory apps/api run pytest tests/test_case_*.py -v

# Run entire backend test suite across all 11 phases (253 tests)
uv --directory apps/api run pytest -v
```

---

## 4. Running Frontend E2E Tests

```bash
# Type-check frontend code
pnpm --filter @samved/web type-check

# Build frontend production bundle
pnpm --filter @samved/web build

# Run Phase 11 Playwright E2E suite
pnpm --filter @samved/web exec playwright test e2e/case-intelligence.spec.ts

# Run all Playwright E2E suites across entire repository (104 tests)
pnpm --filter @samved/web exec playwright test
```

---

## 5. Security & Boundary Checklist

- [x] **Zero Guilt Claims**: Input dialogue claiming guilt or demanding criminal labels is rejected or normalized to `REPORTED_ACTOR` with `claim_status = REPORTED`.
- [x] **Prompt Injection Defense**: Dialogue ingested for extraction is enclosed in `<untrusted_dialogue>` XML blocks with instruction-escaping.
- [x] **Deterministic Safety Supremacy**: Phase 4 safety engine overrides cannot be muted, altered, or deleted by case graph operations.
- [x] **Cryptographic Anchoring**: All evidence links contain verbatim excerpt strings and valid SHA-256 content hashes.
- [x] **Temporal Non-Destructiveness**: Conflicting edges trigger historical supersession (`superseded_by`), preserving historical audit records.
- [x] **Human Tele-Counselor Gate**: Automated extraction creates candidates; graduation to active relationship edges requires explicit human confirmation.
- [x] **Zero Autonomous Dispatch**: Autonomous external notifications and emergency dispatch are structurally excluded.
