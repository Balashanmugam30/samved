# SAMVED — Grounded RAG Service (`services/rag-service`)

## Purpose
Provides grounded legal, regulatory, and institutional knowledge retrieval from authoritative sources to prevent hallucination in helpline responses and operator recommendations.

## Architectural Responsibilities
- Ingestion of verified statutory texts:
  - Narcotic Drugs and Psychotropic Substances (NDPS) Act, 1985 & amendments
  - Mental Healthcare Act, 2017 (decriminalization of suicide attempts, right to treatment)
  - National Policy on Narcotic Drugs and Psychotropic Substances
  - Ministry of Social Justice and Empowerment (MoSJE) NAPDDR Schemes & IRCA Guidelines
- Vector chunking, embedding generation, and `pgvector` indexing.
- Hybrid search (BM25 lexical + dense semantic retrieval) and cross-encoder reranking.
- Grounded citation generation ensuring every legal/scheme suggestion includes an authoritative citation.

## Core Rule
> **Never use arbitrary internet web pages as "legal truth". All guidance must ground directly in official gazette notifications and verified institutional databases.**

## Phase Boundary
- **Phase 0 (Current)**: Architectural boundary and domain models (`LegalSource`, `Document`).
- **Phase 10 (Upcoming)**: Knowledge base embedding pipeline, pgvector integration, and citation-grounded RAG query handler.
