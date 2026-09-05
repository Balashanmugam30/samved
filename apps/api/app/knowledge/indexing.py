"""Deterministic in-memory indexing and multi-factor retrieval for SAMVED Knowledge RAG."""

import math
import re
from datetime import datetime, timezone
from typing import Dict, List, Optional, Set, Tuple

from app.knowledge.models import (
    AuthorityTier,
    DocumentChunk,
    DocumentStatus,
    KnowledgeJurisdiction,
    KnowledgeQuery,
    SourceDocument,
)
from app.knowledge.versioning import is_version_effective

INDEX_VERSION = "knowledge-index-v1"


def tokenize(text: str) -> List[str]:
    """Tokenizes string into lowercase alphanumeric tokens supporting Indic scripts."""
    # Split on whitespace and standard punctuation while preserving Unicode words
    tokens = re.findall(r"[\w\u0900-\u097F\u0B80-\u0BFF]+", text.lower())
    return [t for t in tokens if len(t) > 1]


class InvertedIndex:
    """In-memory BM25-style lexical index with metadata filtering and versioning."""

    def __init__(self, index_version: str = INDEX_VERSION):
        self.index_version = index_version
        self.created_at = datetime.now(timezone.utc).isoformat()
        self.documents: Dict[str, SourceDocument] = {}
        self.chunks: Dict[str, DocumentChunk] = {}
        self.chunk_doc_map: Dict[str, str] = {}  # chunk_id -> document_id
        self.term_postings: Dict[str, Set[str]] = {}  # token -> set of chunk_ids
        self.chunk_tokens: Dict[str, List[str]] = {}  # chunk_id -> tokens
        self.avg_chunk_len: float = 0.0

    def clear(self) -> None:
        """Clears all indexed documents and postings."""
        self.documents.clear()
        self.chunks.clear()
        self.chunk_doc_map.clear()
        self.term_postings.clear()
        self.chunk_tokens.clear()
        self.avg_chunk_len = 0.0

    def add_document(self, document: SourceDocument) -> None:
        """Indexes all chunks across all versions of the document."""
        self.documents[document.document_id] = document
        total_len = 0

        for version in document.versions:
            for chunk in version.chunks:
                self.chunks[chunk.chunk_id] = chunk
                self.chunk_doc_map[chunk.chunk_id] = document.document_id

                # Index chunk text and headings
                full_text = " ".join(chunk.heading_path) + " " + chunk.text
                tokens = tokenize(full_text)
                self.chunk_tokens[chunk.chunk_id] = tokens
                total_len += len(tokens)

                for token in set(tokens):
                    if token not in self.term_postings:
                        self.term_postings[token] = set()
                    self.term_postings[token].add(chunk.chunk_id)

        if self.chunks:
            self.avg_chunk_len = total_len / len(self.chunks)

    def remove_document(self, document_id: str) -> None:
        """Removes a document and its chunks from the index."""
        if document_id not in self.documents:
            return
        doc = self.documents.pop(document_id)
        for version in doc.versions:
            for chunk in version.chunks:
                self.chunks.pop(chunk.chunk_id, None)
                self.chunk_doc_map.pop(chunk.chunk_id, None)
                self.chunk_tokens.pop(chunk.chunk_id, None)
                for postings in self.term_postings.values():
                    postings.discard(chunk.chunk_id)

    def search(
        self, query: KnowledgeQuery
    ) -> List[Tuple[DocumentChunk, SourceDocument, float]]:
        """Executes filtered, reranked lexical search.
        
        Returns list of tuples: (chunk, source_document, relevance_score)
        """
        query_tokens = tokenize(query.query)
        if not query_tokens:
            return []

        # 1. Gather candidate chunk IDs containing at least one query term
        candidate_chunk_ids: Set[str] = set()
        for token in query_tokens:
            if token in self.term_postings:
                candidate_chunk_ids.update(self.term_postings[token])

        if not candidate_chunk_ids:
            return []

        scored_candidates: List[Tuple[DocumentChunk, SourceDocument, float]] = []
        k1 = 1.2
        b = 0.75
        num_docs = max(1, len(self.chunks))

        for chunk_id in candidate_chunk_ids:
            chunk = self.chunks[chunk_id]
            doc_id = self.chunk_doc_map.get(chunk_id)
            if not doc_id or doc_id not in self.documents:
                continue
            doc = self.documents[doc_id]

            # 2. Metadata Filter Gate
            # Document status filter
            if query.effective_only and doc.status not in {DocumentStatus.ACTIVE}:
                continue

            # Temporal validity check
            if query.effective_only:
                if not is_version_effective(chunk.effective_from, chunk.effective_to, query.as_of_date):
                    continue

            # Jurisdiction filter
            if query.jurisdiction:
                q_jur = query.jurisdiction.upper()
                c_jur = chunk.jurisdiction.upper()
                # Central laws apply everywhere, but mismatch between distinct states is blocked
                if q_jur != KnowledgeJurisdiction.INDIA.value and c_jur != KnowledgeJurisdiction.INDIA.value:
                    if q_jur != c_jur:
                        continue

            # Authority tier filter
            if query.source_tiers and doc.authority_tier.value not in query.source_tiers:
                continue

            # 3. BM25 Lexical Scoring
            doc_tokens = self.chunk_tokens.get(chunk_id, [])
            doc_len = len(doc_tokens)
            bm25_score = 0.0

            for q_tok in query_tokens:
                if q_tok in self.term_postings:
                    df = len(self.term_postings[q_tok])
                    idf = math.log((num_docs - df + 0.5) / (df + 0.5) + 1.0)
                    tf = doc_tokens.count(q_tok)
                    numerator = tf * (k1 + 1.0)
                    denominator = tf + k1 * (1.0 - b + b * (doc_len / (self.avg_chunk_len or 1.0)))
                    bm25_score += idf * (numerator / max(0.001, denominator))

            if bm25_score <= 0.01:
                continue

            # 4. Multi-Factor Reranking Weights
            # Authority tier weight
            tier_weights = {
                AuthorityTier.TIER_1: 1.0,
                AuthorityTier.TIER_2: 0.85,
                AuthorityTier.TIER_3: 0.70,
                AuthorityTier.TIER_4: 0.50,
            }
            authority_factor = tier_weights.get(doc.authority_tier, 0.5)

            # Jurisdiction specificity bonus
            jur_bonus = 1.0
            if query.jurisdiction and query.jurisdiction.upper() == chunk.jurisdiction.upper():
                jur_bonus = 1.25  # State-specific bonus over national general

            # Qualifier preservation bonus (if query searches for conditions/exceptions)
            qualifier_bonus = 1.0
            if chunk.qualifiers:
                qualifier_bonus = 1.05

            final_score = bm25_score * authority_factor * jur_bonus * qualifier_bonus
            scored_candidates.append((chunk, doc, final_score))

        # Sort descending by final score
        scored_candidates.sort(key=lambda x: x[2], reverse=True)
        return scored_candidates[: query.max_results]
