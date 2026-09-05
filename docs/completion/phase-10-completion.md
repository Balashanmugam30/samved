# SAMVED — Phase 10 Milestone Completion Document
**Legal / Policy RAG — Governed, Citation-First, Versioned, Human-Supervised Knowledge Retrieval**

- **Date**: September 2026
- **Status**: COMPLETE ✅
- **Repository**: [Balashanmugam30/samved](https://github.com/Balashanmugam30/samved)
- **Branch**: `main`

---

## 1. Executive Summary

Phase 10 establishes the **Legal / Policy RAG Subsystem** for SAMVED, fulfilling the architectural doctrine:
$$\text{Authoritative Source} \to \text{Ingestion} \to \text{Normalization \& Hashing} \to \text{Context Chunking} \to \text{Versioned Index} \to \text{Filtered Retrieval} \to \text{Citation Assembly} \to \text{Policy Validation \& Conflict Resolution} \to \text{Human Supervision} \to \text{Advisory Orchestration / UI}$$

The subsystem empowers human tele-counselors with verifiable, citation-grounded statutory schemes, circulars, and institutional protocols under strict legal and clinical boundaries:
1. **Advisory Non-Autonomous Retrieval**: Zero autonomous legal determinations, court filings, binding notices, or police dispatches.
2. **Phase 4 Safety Subordination**: Programmatic safety states from the Deterministic Safety Engine retain absolute, unalterable authority.
3. **Zero Ungrounded Hallucinations**: Missing or unauthoritative sources strictly produce `NO_RELIABLE_SOURCE_FOUND`. Parametric LLM memory guesswork is structurally blocked.
4. **Temporal & Version Applicability**: Document lifecycle transitions (`DRAFT` $\to$ `ACTIVE` $\to$ `SUPERSEDED` $\to$ `ARCHIVED` / `WITHDRAWN`) ensure outdated guidance triggers explicit operator warnings.

---

## 2. Completed Architecture & Deliverables

### 2.1 Core Knowledge Subsystem (`apps/api/app/knowledge/`)
1. **Pydantic Data Models (`models.py`)**:
   - `SourceDocument`, `DocumentVersion`, `DocumentChunk`, `KnowledgeQuery`, `KnowledgeSearchResult`, `CitationMetadata`, `ConflictingSourcePair`, `IngestionRequest`, `IngestionAuditRecord`.
2. **Deterministic Corpus Fixtures (`fixtures/`)**:
   - `central_policy_en.md`, `gov_scheme_current_en.md`, `gov_scheme_old_en.md`, `tn_policy_current_en.md`, `tn_policy_current_ta.md`, `conflicting_policy_a.md`, `conflicting_policy_b.md`, `malicious_injection.md`.
3. **Normalization & Hashing (`normalization.py`)**:
   - Canonical URL normalization (stripping tracking parameters), text sanitization, HTML/script stripping, SHA-256 chunk hashing.
4. **Context-Preserving Chunking (`chunking.py`)**:
   - Maintains hierarchical heading paths (`# Scheme > ## Section > ### Eligibility`) and preserves legal qualifiers (`provided that`, `subject to`, `exceptions`, `definitions`).
5. **Source Registry & Security (`sources.py`)**:
   - Authority Tier Resolver (Tiers 1–4: Statutory/Gazetted, Executive Departmental, Institutional Best Practice, General Information).
   - SSRF defenses blocking loopback (`127.0.0.1`), private IP ranges (`10.0.0.0/8`, `192.168.0.0/16`), and AWS metadata (`169.254.169.254`).
   - Strict 10MB payload size limit boundary.
6. **Multi-Version Tree & Freshness (`versioning.py`)**:
   - Parent/child superseding relationships and as-of temporal applicability (`effective_from <= as_of_date <= effective_to`). Freshness status calculation (`CURRENT`, `STALE`, `EXPIRED`, `UNKNOWN`).
7. **Lexical Index & Reranking (`indexing.py`)**:
   - In-memory BM25 lexical search with token overlap scoring, jurisdiction/language filters, authority tier reranking, and multi-version score decay.
8. **Citation Integrity & Assembly (`citations.py`)**:
   - Cryptographic SHA-256 substring integrity verification ensuring retrieved excerpts are verbatim passages of the underlying document.
9. **Conflict Detection Engine (`conflicts.py`)**:
   - Cross-document discrepancy detector enforcing statutory precedence: Version Recency > Authority Tier > Jurisdiction Specificity. Emits `KNOWLEDGE_SOURCE_CONFLICT` events.
10. **Grounding & Injection Defenses (`grounding.py`)**:
    - Encloses retrieved excerpts within `<retrieved_source_data>` XML delimiters, isolates untrusted caller input, validates structured citation claims, and provides deterministic excerpt fallback.
11. **Audit Logging (`audit.py`)**:
    - Bounded in-memory logger recording ingestion audits, document lifecycle transitions, and query retrieval trails.
12. **Knowledge Service (`service.py`)**:
    - Singleton service with synchronous fixture ingestion at startup (`_ingest_sync`) and async event broadcasting.

### 2.2 Shared Schemas & Contracts
- **`packages/schemas/src/events.ts`**:
  - Registered Phase 10 event types: `KNOWLEDGE_SEARCH_STARTED`, `KNOWLEDGE_SEARCH_COMPLETED`, `KNOWLEDGE_SEARCH_FAILED`, `KNOWLEDGE_SOURCE_SELECTED`, `KNOWLEDGE_SOURCE_CONFLICT`, `KNOWLEDGE_REVIEW_RECOMMENDED`, `KNOWLEDGE_ANSWER_BLOCKED`.
  - Added enums `AuthorityTier`, `DocumentStatus`, `FreshnessStatus`, `KnowledgeJurisdiction`.
  - Added interfaces `CitationMetadata`, `KnowledgeItemPayload`, `KnowledgeQueryPayload`, `KnowledgeResultPayload`.
- **`apps/api/app/schemas/events.py`**:
  - Mirrored Python Pydantic models with identical discriminators.

### 2.3 Phase 9 Multi-Agent & Realtime Integration
- **`KnowledgeRetrievalAgent` (`apps/api/app/orchestration/workers/knowledge_retrieval.py`)**:
  - Registered worker executing governed retrieval against `KnowledgeService`.
- **Context Injection (`apps/api/app/orchestration/models.py`)**:
  - Added `knowledge_info` to `ValidatedContext`.
- **Operator Briefing Enrichment (`apps/api/app/orchestration/workers/operator_briefing.py`)**:
  - Synthesizes knowledge citations and evidence tags directly into the Operator Briefing Card.
- **Operator Notes with Citation Reference**:
  - Added optional `citation_ref` field to `OperatorNote` schema, model, and REST endpoint (`POST /v1/operator/calls/{id}/notes`).

### 2.4 REST API & Database Schema
- **REST Endpoints (`/v1/knowledge`)**:
  - `GET /v1/knowledge/status` — Subsystem health, corpus size, chunk count, and index status.
  - `GET /v1/knowledge/sources` — List registered authoritative sources.
  - `GET /v1/knowledge/documents/{id}` — Retrieve document metadata and active version.
  - `GET /v1/knowledge/documents/{id}/versions` — Full version history tree.
  - `POST /v1/knowledge/search` — Governed retrieval query with filters and citations.
  - `POST /v1/knowledge/ingest` — Ingest new document or version with SSRF/size validation.
  - `GET /v1/knowledge/citations/{id}` — Cryptographic citation integrity verification.
- **Database Schema (`infra/db/init.sql`)**:
  - Added `citation_ref` to `operator_notes`.
  - Created 7 relational tables: `knowledge_sources`, `knowledge_documents`, `knowledge_document_versions`, `knowledge_chunks`, `knowledge_citations`, `knowledge_retrieval_events`, and `knowledge_ingestion_audit`.

### 2.5 Operator Workstation UI (`apps/web/src/app/calls/page.tsx`)
- **Knowledge Support Panel (`data-testid="knowledge-panel"`)**:
  - Query input, search button, jurisdiction filter, language filter, and current-only toggle.
  - Status badge (`data-testid="knowledge-status-badge"`) displaying `READY`, `SEARCHING`, `GROUNDED`, `CONFLICT`, or `NO_RELIABLE_SOURCE_FOUND`.
  - Authoritative Source Cards with Tier badge (Tier 1–4), publisher, jurisdiction, status, section, effective date, and verbatim excerpt.
  - AI Synthesized Summary Card with inline citation tags and "Save to Notes" button.
  - Conflict Alert Banner (`data-testid="knowledge-conflict-banner"`) warning of contradictory provisions.
  - Stale Alert Banner (`data-testid="knowledge-stale-banner"`) warning of superseded documents.
  - Zero-Source Notice (`data-testid="knowledge-no-source-notice"`) preventing LLM hallucination.
  - Statutory Legal Disclaimer (`data-testid="knowledge-disclaimer"`).
  - Event Timeline integration with dedicated `KNOWLEDGE` filter pill.
  - Clean call-switching isolation preventing cross-session search bleed.

---

## 3. Verification & Test Metrics

1. **Backend Unit & Integration Suite (`pytest`)**:
   - **217 / 217 tests PASSED (100%)** across 11 dedicated Phase 10 test files and all prior phases.
2. **TypeScript Compilation (`tsc --noEmit`)**:
   - **0 errors**.
3. **Next.js Production Build (`next build`)**:
   - **0 errors**; all 9 static and dynamic routes compiled cleanly.
4. **Playwright E2E Test Suite (`playwright test`)**:
   - **16 / 16 Phase 10 E2E tests PASSED (100%)** across Desktop Chrome and Mobile Chrome viewports.
   - Zero regressions across prior suites.
5. **Docker Compose Validation**:
   - Compose file configuration validated cleanly.

---

## 4. Scope Compliance Verification

- [x] Only Phase 10 implemented.
- [x] Phase 11 Knowledge Graph & Case Intelligence NOT started.
- [x] Phase 12 Follow-up & Care Continuity NOT started.
- [x] Deterministic Safety Engine retains absolute authority over safety states.
- [x] Zero ungrounded answers; missing sources strictly yield `NO_RELIABLE_SOURCE_FOUND`.
