# SAMVED — Phase 11 Milestone Completion Document
**Case Intelligence & Knowledge Graph — Explainable Entity/Relationship Layer**

- **Date**: September 2026
- **Status**: COMPLETE ✅
- **Repository**: [Balashanmugam30/samved](https://github.com/Balashanmugam30/samved)
- **Branch**: `main`

---

## 1. Executive Summary

Phase 11 introduces the **Case Intelligence & Knowledge Graph Subsystem** for SAMVED, establishing an evidence-linked, temporally aware, human-supervised case entity/relationship layer.

### Core Architectural Doctrine:
$$\text{Evidence} \to \text{Structured Entities} \to \text{Structured Relationships} \to \text{Temporal Context} \to \text{Provenance} \to \text{Case Graph} \to \text{Operator Intelligence View}$$

### Absolute Epistemic & Operational Boundaries:
1. **Epistemic Model**:
   - The graph models caller-reported dialogue and claims, **NOT** objective truth, guilt, or legal culpability.
   - All entities and relationships maintain explicit `claim_status` (`REPORTED`, `CORROBORATED`, `CONTESTED`, `SUPERSEDED`).
2. **Zero Guilt Accusations & Role Normalization**:
   - Punitive or legal guilt accusations (`OFFENDER`, `GUILTY`, `PERPETRATOR`) are rejected or normalized to `REPORTED_ACTOR` with `claim_status = REPORTED`.
3. **Deterministic Safety Supremacy**:
   - Phase 4 Safety Engine and Phase 5 SVI retain unconditional supremacy. Safety events link into the graph as unalterable, read-only evidence nodes (`SAFETY_SIGNAL`, `SVI_SIGNAL`).
4. **Human Tele-Counselor Supervision**:
   - Automated entity/relationship extraction produces **Candidate Relationships** (`is_candidate = true`). Candidates do not graduate into active edges until confirmed by a licensed human tele-counselor.
5. **Cryptographic Provenance**:
   - Every node and edge is cryptographically anchored by a SHA-256 hash of verbatim call dialogue excerpts with character/byte offsets.
6. **Temporal Non-Destructiveness**:
   - Conflicting facts trigger historical supersession (`superseded_by`), preserving historical audit records and temporal validity intervals.
7. **Zero Autonomous Dispatch**:
   - The knowledge graph never initiates autonomous police calls, emergency dispatch, or external agency transmissions.

---

## 2. Completed Architecture & Deliverables

### 2.1 Case Intelligence Subsystem (`apps/api/app/cases/`)
1. **Pydantic Data Models (`models.py`)**:
   - `CaseEntity`, `CaseRelationship`, `CaseEntityCandidate`, `CaseEvent`, `CaseEvidenceLink`, `CaseGraphResponse`, `CaseIntegrityReport`, `CandidateConfirmationRequest`, `CandidateRejectionRequest`.
2. **Cryptographic Provenance (`provenance.py`)**:
   - SHA-256 evidence hashing, anchor assembly, and verbatim substring offset validation.
3. **Bitemporal Logic (`temporal.py`)**:
   - ISO-8601 interval checking, `is_edge_active_at` temporal filtering, and non-destructive historical preservation via `supersede_edge`.
4. **Conservative Extraction & Guardrails (`extraction.py`)**:
   - Multilingual negation detection (`not`, `nahi`, `illai`), prompt injection defenses via `<untrusted_dialogue>` delimiters, and punitive/guilt claim rejection.
5. **Graph Query Engine & Integrity (`graph.py`)**:
   - Depth-bounded subgraph extraction (1 to 4 hops), entity neighbor queries, cycle handling, and integrity verification (dangling edge, temporal anomaly, and evidence hash verification).
6. **Immutable Audit Logger (`audit.py`)**:
   - Thread-safe in-memory ring buffer audit logging (`CaseAuditLogger`).
7. **Case Service (`service.py`)**:
   - Singleton service managing cases, entities, relationships, candidates, events, and WebSocket broadcasting via `EventEnvelope(session_id=..., call_id=...)`. Preloaded with deterministic fixtures for `case-1001`.

### 2.2 Shared Schemas & Contracts
- **`packages/schemas/src/events.ts`**:
   - Added Phase 11 event types: `CASE_ENTITY_EXTRACTED`, `CASE_RELATIONSHIP_CREATED`, `CASE_CANDIDATE_PROPOSED`, `CASE_CANDIDATE_CONFIRMED`, `CASE_CANDIDATE_REJECTED`, `CASE_GRAPH_MUTATED`, `CASE_EDGE_SUPERSEDED`.
   - Added enums: `EntityType`, `PersonRole`, `ClaimStatus`, `RelationshipType`.
   - Added payload interfaces for all case events.
- **`packages/schemas/src/domain.ts`**:
   - Added unified `CaseStatus` (`OPEN`, `ACTIVE`, `PENDING_REVIEW`, `CLOSED`, `ARCHIVED`).
- **`apps/api/app/schemas/events.py`**:
   - Mirrored Python Pydantic models with identical discriminators.

### 2.3 Database Migration (`infra/db/init.sql`)
Created 7 relational tables with foreign keys and performance indexes:
- `case_calls`: Links helpline calls to cases.
- `case_entities`: Unique entities with canonical names, roles, and types.
- `case_relationships`: Directed active relationship edges with temporal intervals.
- `case_events`: Immutable case timeline events.
- `case_evidence_links`: Verbatim dialogue excerpts and SHA-256 hashes.
- `case_entity_candidates`: Pending relationships requiring human counselor review.
- `case_merge_operations`: Immutable audit records of merges, confirmations, and rejections.

### 2.4 Multi-Agent Orchestration Integration
- **`CaseGraphExtractionAgent` (`apps/api/app/orchestration/workers/case_graph_extraction.py`)**:
   - Specialized worker analyzing call turns for entities and candidate relationships.
   - Registered in worker taxonomy and DAG execution plan.
- **Operator Briefing Card Enrichment (`apps/api/app/orchestration/workers/operator_briefing.py`)**:
   - Enriched with entity counts and pending candidate counts.

### 2.5 REST API Endpoints (`/v1/cases`)
- `GET /v1/cases/status` — Subsystem health and global metrics.
- `POST /v1/cases` — Create new case.
- `GET /v1/cases` — List cases.
- `GET /v1/cases/{id}` — Retrieve case details and metadata.
- `GET /v1/cases/{id}/graph` — Depth-bounded subgraph query with candidate inclusion.
- `GET /v1/cases/{id}/timeline` — Chronological case event stream.
- `GET /v1/cases/{id}/entities` — List entities in case.
- `GET /v1/cases/{id}/relationships` — List active relationship edges.
- `POST /v1/cases/candidates/{id}/confirm` — Human counselor confirmation.
- `POST /v1/cases/candidates/{id}/reject` — Human counselor rejection.
- `GET /v1/cases/{id}/integrity` — Cryptographic integrity check.
- `GET /v1/cases/{id}/audit` — Immutable mutation audit trail.

### 2.6 Frontend Operator Console (`apps/web/src/app/calls/page.tsx`)
- **Case Intelligence Panel (`data-testid="case-intelligence-panel"`)**:
   - Case ID header (`case-1001`), call ID, status badge (`OPEN`), and epistemic disclaimer badges.
   - **Metrics Strip**: Entity count, active edge count, pending candidate count.
   - **Interactive Graph Visualizer (`data-testid="case-graph-visualizer"`)**: Entity nodes with role chips and directed edges.
   - **Node Inspector drawer (`data-testid="node-inspector"`)**: Entity metadata, claim status, and SHA-256 evidence anchors.
   - **Edge Inspector drawer (`data-testid="edge-inspector"`)**: Directed relationship type, confidence, and temporal validity intervals.
   - **Candidate Confirmation Cards (`data-testid="candidate-card-..."`)**: Grounded verbatim excerpt display with **Confirm** and **Reject** buttons.
   - **Depth Traversal Selector (`data-testid="graph-depth-select"`)**: 1 to 4 hop subgraph expansion.
   - **Case Audit Trail Modal (`data-testid="case-audit-modal"`)**: Chronological audit trail of all graph operations.
   - **Epistemic Safety Notice (`data-testid="case-epistemic-disclaimer"`)**: Persistent non-clinical and non-guilt declaration.
   - **Timeline Integration**: Added `CASE` filter pill and event cards.

---

## 3. Verification & Test Metrics

### 3.1 Backend Test Results
- **Phase 11 Dedicated Test Suites**: **36 tests** (100% pass rate in 0.32s).
- **Full Backend Pytest Regression**: **253 tests** across all 11 phases (100% pass rate in 7.92s).

```
============================== 253 passed in 7.92s ==============================
```

### 3.2 Frontend Playwright E2E Results
- **Phase 11 E2E Suite (`e2e/case-intelligence.spec.ts`)**: **20 tests** (10 Desktop Chrome + 10 Mobile Chrome) passed in 9.3s.
- **Full Playwright Regression Suite**: **104 tests** across all 10 spec files passed in 24.2s (100% pass rate, 0 failures).

```
  104 passed (24.2s)
```

### 3.3 Docker & Infrastructure Validation
- `docker compose config`: Validated with zero syntax errors.
- Monorepo TypeScript builds: `pnpm --filter @samved/schemas build`, `pnpm --filter @samved/web type-check`, `pnpm --filter @samved/web build` passed with zero errors.

---

## 4. Documentation & Runbooks
- Architectural Specification: `docs/architecture/phase-11-case-intelligence-knowledge-graph.md`
- Testing Guide: `docs/testing/case-intelligence-testing.md`
- Operational Runbook: `docs/runbooks/case-intelligence.md`
- Localhost Runbook: `docs/runbooks/localhost.md`
- Multi-Phase Roadmap: `docs/roadmap.md`
- Main Readme: `README.md`
