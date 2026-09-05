# SAMVED Phase 10 — Legal / Policy RAG Testing Guide

This document details the testing architecture, test suites, edge case validations, and security boundaries for SAMVED Phase 10: **Legal / Policy RAG — Governed, Citation-First, Versioned, Human-Supervised Knowledge Retrieval**.

---

## 1. Testing Philosophy & Scope

SAMVED operates under a strict, non-negotiable legal and safety retrieval doctrine:
1. **Human Operator Supremacy**: Retrieved policy excerpts and AI syntheses are purely advisory tools for human tele-counselors. No autonomous legal determinations, binding notices, or police dispatch are ever triggered.
2. **Phase 4 Safety Precedence**: Knowledge retrieval operates strictly downstream of the Deterministic Safety Engine. No retrieval event or policy guidance can ever modify, suppress, or override an active `SafetyState` or `SVI`.
3. **Zero Ungrounded Hallucinations**:
   - Every claim synthesized by an LLM must be backed by a verified verbatim excerpt citation (`[cit:<id>]`).
   - If no authoritative source satisfies a query under the specified jurisdiction and effective date, the system strictly yields `NO_RELIABLE_SOURCE_FOUND`. Model guesswork or parametric memory fallback is structurally blocked.
4. **Temporal Applicability & Version Governance**:
   - Queries evaluate documents strictly against an `as_of_date`.
   - Superseded or expired provisions trigger `SOURCE_STALE` warnings.
   - Contradictory provisions across jurisdictions or tiers trigger `SOURCE_CONFLICT` warnings.

---

## 2. Test Suites Overview

### 2.1 Backend Unit & Integration Suites (`apps/api/tests/`)

| Test Suite | File | Tests | Focus Area |
| :--- | :--- | :---: | :--- |
| **Knowledge Models** | `test_knowledge_models.py` | 3 | Source document metadata, document versioning, chunk models, query models, search results, citation schemas, and Pydantic validation. |
| **Ingestion Pipeline** | `test_knowledge_ingestion.py` | 3 | Text normalization, HTML/script sanitization, URL tracking parameter stripping, SHA-256 chunk hashing, idempotency, and audit trail generation. |
| **Versioning & Temporal Logic** | `test_knowledge_versioning.py` | 3 | Version trees, superseding chains, as-of temporal filtering (`effective_from <= as_of_date <= effective_to`), and freshness status computation (`CURRENT`, `STALE`, `EXPIRED`). |
| **Contextual Chunking** | `test_knowledge_chunking.py` | 3 | Context-preserving chunker, heading path preservation (`# Chapter > ## Section`), qualifier retention (`provided that`, `subject to`, `exceptions`), and length boundary constraints. |
| **Lexical Index & Retrieval** | `test_knowledge_retrieval.py` | 3 | In-memory BM25 lexical search, token overlap scoring, jurisdiction/language filters, authority tier reranking, and multi-version score decay. |
| **Citation Integrity** | `test_knowledge_citations.py` | 3 | Citation metadata assembly, cryptographic text hash verification, verbatim excerpt substring matching, and tamper detection. |
| **Conflict Resolution** | `test_knowledge_conflicts.py` | 3 | Cross-document conflict detection, multi-factor precedence (Recency > Authority Tier > Jurisdiction Specificity), and `SOURCE_CONFLICT` event flagging. |
| **Knowledge REST API** | `test_knowledge_api.py` | 3 | `/v1/knowledge/status`, `/sources`, `/documents/{id}`, `/documents/{id}/versions`, `/search`, `/ingest`, `/citations/{id}` endpoints. |
| **Security & Defenses** | `test_knowledge_security.py` | 3 | SSRF prevention (blocking loopback/private IP ingest), 10MB payload size limit, strict XML grounding delimiters (`<retrieved_source_data>`), and prompt injection neutralization. |
| **Realtime Event Broadcasting** | `test_knowledge_realtime.py` | 2 | Realtime WebSocket event broadcast (`KNOWLEDGE_SEARCH_STARTED`, `KNOWLEDGE_SEARCH_COMPLETED`, `KNOWLEDGE_SOURCE_CONFLICT`). |
| **Multi-Agent Integration** | `test_knowledge_agent.py` | 2 | Phase 9 `KnowledgeRetrievalAgent` worker execution, context injection, and `OperatorBriefingAgent` citation enrichment. |

**Total Phase 10 Backend Tests**: **30 tests** (bringing total API test suite to **217 tests**).

---

### 2.2 Frontend Playwright E2E Suite (`apps/web/e2e/knowledge-rag.spec.ts`)

The E2E suite exercises the Operator Workstation Knowledge Support Panel across Desktop Chrome and Mobile Chrome viewports:

| Test Case | Description | Verification Points |
| :--- | :--- | :--- |
| **Panel Rendering & Controls** | Verifies panel presence in Call View | Header branding, status badge (`READY`), query input, search button, jurisdiction filter, language filter, current-only toggle, and statutory legal disclaimer. |
| **Manual Search & Grounded Cards** | Performs query and verifies grounded results | Status badge (`GROUNDED`), results count badge, AI synthesized summary with inline citation chips, and authoritative source cards with Tier badges, publisher, jurisdiction, effective dates, and verbatim excerpts. |
| **Save Citation into Notes** | Adds retrieved citation to caller case file | POSTs to `/v1/operator/calls/{id}/notes` with `citation_ref`, updates notes count, and displays `note-citation-ref` badge inside operator notes timeline. |
| **Conflict Warning Banner** | Handles contradictory policy provisions | Displays `SOURCE CONFLICT DETECTED` banner with conflict explanations and precedence recommendation. |
| **Stale Warning Banner** | Handles superseded / expired documents | Displays `SOURCE MAY BE OUTDATED` banner prompting operator verification before guidance is delivered. |
| **Zero-Source Notice** | Prevents ungrounded model hallucination | When no reliable source matches, displays `NO RELIABLE SOURCE FOUND` notice and strictly suppresses AI summary generation. |
| **Timeline Category Filtering** | Integrates with operator timeline | Timeline filter includes `KNOWLEDGE` pill, displaying `KNOWLEDGE_SEARCH_STARTED` and completion events. |
| **Multi-Call State Isolation** | Tests operator switching between active calls | Ensures knowledge search queries, results, and conflict flags do not leak across distinct caller sessions. |

---

## 3. Running Backend Tests

```bash
# Run all Phase 10 Knowledge Retrieval unit and integration tests
uv --directory apps/api run pytest tests/test_knowledge_*.py -v

# Run entire backend test suite across all phases (217 tests)
uv --directory apps/api run pytest -v
```

---

## 4. Running Frontend E2E Tests

```bash
# Type-check frontend code
pnpm --filter @samved/web type-check

# Build frontend production bundle
pnpm --filter @samved/web build

# Run Phase 10 Playwright E2E suite
pnpm --filter @samved/web exec playwright test e2e/knowledge-rag.spec.ts

# Run all Playwright E2E suites across entire repository
pnpm --filter @samved/web test:e2e
```

---

## 5. Security & Boundary Checklist

- [x] **No Autonomous Action**: System never generates legal notices or emergency dispatches.
- [x] **Grounding Delimiters**: Raw source text is enclosed inside `<retrieved_source_data>` tags to prevent prompt injection hijacking.
- [x] **SSRF Defense**: Ingestion rejects requests targeting `127.0.0.1`, `localhost`, `169.254.169.254`, `10.0.0.0/8`, `192.168.0.0/16`, and private subnets.
- [x] **Payload Bounds**: Document size limit strictly enforced at 10MB per document; chunk sizes capped at 1,500 characters.
- [x] **Citation Integrity**: Citations verify SHA-256 substring matches against original raw documents.
