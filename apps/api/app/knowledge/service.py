"""KnowledgeService: Central governed retrieval service for SAMVED Phase 10."""

import asyncio
import logging
import os
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from app.knowledge.audit import knowledge_audit_logger
from app.knowledge.chunking import chunk_document
from app.knowledge.citations import create_citation
from app.knowledge.conflicts import detect_source_conflicts
from app.knowledge.grounding import synthesize_deterministic_summary
from app.knowledge.indexing import InvertedIndex
from app.knowledge.models import (
    AuthorityTier,
    CitationMetadata,
    DocumentStatus,
    DocumentVersion,
    FreshnessStatus,
    IngestionAuditRecord,
    IngestionRequest,
    KnowledgeJurisdiction,
    KnowledgeQuery,
    KnowledgeSearchResult,
    KnowledgeSearchResultItem,
    SourceDocument,
    SourceType,
    TopicCategory,
)
from app.knowledge.normalization import (
    compute_sha256,
    normalize_and_hash,
    normalize_source_url,
)
from app.knowledge.sources import (
    determine_authority_tier,
    validate_document_size,
    validate_source_url_ssrf,
)
from app.knowledge.versioning import VersionManager, calculate_freshness
from app.schemas.events import EventEnvelope, EventType

logger = logging.getLogger(__name__)


class KnowledgeService:
    """Singleton service governing legal and policy retrieval operations in SAMVED."""

    def __init__(self, auto_seed: bool = True):
        self._documents: Dict[str, SourceDocument] = {}
        self._citations: Dict[str, CitationMetadata] = {}
        self._index = InvertedIndex()
        self._lock = asyncio.Lock()
        self._event_broadcaster = None
        self._status = "READY"

        if auto_seed:
            self._seed_default_corpus()

    def set_event_broadcaster(self, broadcaster) -> None:
        """Sets external async callable to broadcast EventEnvelope over WebSocket."""
        self._event_broadcaster = broadcaster

    async def _broadcast_event(
        self, event_type: EventType, call_id: Optional[str], payload: dict
    ) -> None:
        """Emits an event through the broadcaster if registered."""
        if not self._event_broadcaster:
            return
        try:
            envelope = EventEnvelope(
                event_type=event_type,
                session_id=call_id or "system",
                call_id=call_id or "system",
                payload=payload,
            )
            await self._event_broadcaster(envelope)
        except Exception as e:
            logger.warning(f"Failed to broadcast knowledge event {event_type.value}: {e}")

    def get_status(self) -> dict:
        """Returns service status, index size, and authority metrics."""
        return {
            "status": self._status,
            "index_version": self._index.index_version,
            "total_documents": len(self._documents),
            "total_chunks": len(self._index.chunks),
            "active_documents": sum(
                1 for d in self._documents.values() if d.status == DocumentStatus.ACTIVE
            ),
            "supported_jurisdictions": [
                j.value for j in KnowledgeJurisdiction
            ],
            "authority_hierarchy": [
                {"tier": 1, "label": "Official GoI / State Official Sources"},
                {"tier": 2, "label": "Official Courts & Statutory Commissions"},
                {"tier": 3, "label": "Approved Institutional Partners & Shelters"},
                {"tier": 4, "label": "Secondary References & Operational SOPs"},
            ],
        }

    def _ingest_sync(
        self, req: IngestionRequest, allow_test_fixtures: bool = False
    ) -> Tuple[SourceDocument, IngestionAuditRecord]:
        """Synchronously parses, versions, chunks, and indexes a document."""
        # 1. SSRF and Size Validation
        validate_document_size(len(req.content.encode("utf-8")))
        validate_source_url_ssrf(req.source_url, allow_test_fixtures=allow_test_fixtures)

        # 2. URL Normalization and Content Hashing
        canonical_url = normalize_source_url(req.source_url)
        raw_checksum, clean_text, content_hash = normalize_and_hash(req.content)

        # 3. Determine Authority Tier
        tier, verification_note = determine_authority_tier(
            req.publisher, canonical_url, req.authority_tier
        )

        effective_from = req.effective_from or datetime.now(timezone.utc).strftime("%Y-%m-%d")

        # Check if document already exists by canonical URL or title
        existing_doc = None
        for doc in self._documents.values():
            if doc.source_url == canonical_url or doc.title == req.title:
                existing_doc = doc
                break

        if existing_doc:
            # Check for exact duplicate
            if existing_doc.content_hash == content_hash and existing_doc.current_version == req.version:
                logger.info(f"Duplicate document content detected for {req.title}. Skipping re-chunking.")
                audit_record = IngestionAuditRecord(
                    document_id=existing_doc.document_id,
                    version=req.version,
                    source_url=canonical_url,
                    action="DUPLICATE_IGNORED",
                    status=DocumentStatus.ACTIVE,
                    content_hash=content_hash,
                )
                return existing_doc, audit_record

            # Create new version under existing document
            doc_id = existing_doc.document_id
            chunks = chunk_document(
                document_id=doc_id,
                version=req.version,
                text=clean_text,
                language=req.language,
                jurisdiction=req.jurisdiction,
                effective_from=effective_from,
                effective_to=req.effective_to,
            )

            new_version = DocumentVersion(
                document_id=doc_id,
                version_number=req.version,
                effective_from=effective_from,
                effective_to=req.effective_to,
                status=DocumentStatus.ACTIVE,
                checksum=raw_checksum,
                content_hash=content_hash,
                chunks=chunks,
            )

            VersionManager.add_version(existing_doc, new_version, auto_supersede_previous=True)
            self._index.remove_document(doc_id)
            self._index.add_document(existing_doc)

            audit_record = IngestionAuditRecord(
                document_id=doc_id,
                version=req.version,
                source_url=canonical_url,
                action="UPDATE_VERSION",
                status=DocumentStatus.ACTIVE,
                content_hash=content_hash,
                details={"title": req.title, "supersedes": new_version.supersedes},
            )
            return existing_doc, audit_record

        # New document
        doc_id = str(uuid.uuid4())
        chunks = chunk_document(
            document_id=doc_id,
            version=req.version,
            text=clean_text,
            language=req.language,
            jurisdiction=req.jurisdiction,
            effective_from=effective_from,
            effective_to=req.effective_to,
        )

        version_obj = DocumentVersion(
            document_id=doc_id,
            version_number=req.version,
            effective_from=effective_from,
            effective_to=req.effective_to,
            status=DocumentStatus.ACTIVE,
            checksum=raw_checksum,
            content_hash=content_hash,
            chunks=chunks,
        )

        document = SourceDocument(
            document_id=doc_id,
            title=req.title,
            publisher=req.publisher,
            source_url=canonical_url,
            source_type=req.source_type,
            jurisdiction=req.jurisdiction,
            language=req.language,
            topic=req.topic,
            issued_at=req.issued_at,
            effective_from=effective_from,
            effective_to=req.effective_to,
            current_version=req.version,
            status=DocumentStatus.ACTIVE,
            authority_tier=tier,
            checksum=raw_checksum,
            content_hash=content_hash,
            license_notes=req.license_notes,
            verified_source=req.verified,
            verification_method=req.verification_method or verification_note,
            versions=[version_obj],
        )

        self._documents[doc_id] = document
        self._index.add_document(document)

        audit_record = IngestionAuditRecord(
            document_id=doc_id,
            version=req.version,
            source_url=canonical_url,
            action="INGEST",
            status=DocumentStatus.ACTIVE,
            content_hash=content_hash,
            details={"title": req.title, "tier": tier.value},
        )
        return document, audit_record

    async def ingest_document(
        self, req: IngestionRequest, allow_test_fixtures: bool = False
    ) -> SourceDocument:
        """Ingests, sanitizes, versions, chunks, and indexes a legal/policy document."""
        async with self._lock:
            doc, audit_record = self._ingest_sync(req, allow_test_fixtures=allow_test_fixtures)
        await knowledge_audit_logger.log_ingestion(audit_record)
        return doc


    async def search(self, query: KnowledgeQuery) -> KnowledgeSearchResult:
        """Performs citation-first retrieval, conflict detection, and grounded summary synthesis."""
        start_time = time.perf_counter()
        query_id = str(uuid.uuid4())

        await self._broadcast_event(
            EventType.KNOWLEDGE_SEARCH_STARTED,
            query.call_id,
            {"query_id": query_id, "query": query.query, "jurisdiction": query.jurisdiction},
        )

        async with self._lock:
            candidates = self._index.search(query)

        # Conflict Detection
        has_conflict, conflicts = detect_source_conflicts(candidates)

        citations: List[CitationMetadata] = []
        results: List[KnowledgeSearchResultItem] = []
        review_reasons: List[str] = []

        if has_conflict:
            review_reasons.append("Source contradiction detected between applicable policy directives.")

        for chunk, doc, score in candidates:
            citation = create_citation(chunk, doc)
            citations.append(citation)
            self._citations[citation.citation_id] = citation

            freshness = calculate_freshness(
                chunk.effective_from, chunk.effective_to, doc.status, query.as_of_date
            )
            if freshness in {FreshnessStatus.STALE, FreshnessStatus.EXPIRED}:
                review_reasons.append(f"Source '{doc.title}' is marked {freshness.value}.")

            results.append(
                KnowledgeSearchResultItem(
                    document_id=doc.document_id,
                    version=chunk.version,
                    title=doc.title,
                    publisher=doc.publisher,
                    jurisdiction=chunk.jurisdiction,
                    source_url=doc.source_url,
                    chunk_id=chunk.chunk_id,
                    excerpt=citation.excerpt,
                    relevance=round(score, 4),
                    authority_tier=doc.authority_tier.value,
                    effective_status=freshness.value,
                    source_date=chunk.effective_from,
                    retrieved_at=doc.retrieved_at,
                    citation=citation,
                )
            )

        requires_human_review = len(review_reasons) > 0 or has_conflict

        # Determine overall result status
        if not results:
            status = "NO_RELIABLE_SOURCE_FOUND"
            requires_human_review = True
            review_reasons.append("No authoritative source matched query under specified jurisdiction.")
        elif has_conflict:
            status = "CONFLICT"
        else:
            status = "COMPLETED"

        # Generate grounded summary
        grounded_answer = synthesize_deterministic_summary(
            query.query, citations, conflict_detected=has_conflict
        )

        latency_ms = (time.perf_counter() - start_time) * 1000

        final_result = KnowledgeSearchResult(
            query_id=query_id,
            call_id=query.call_id,
            query=query.query,
            status=status,
            total_found=len(results),
            results=results,
            citations=citations,
            ai_summary=grounded_answer.summary_text,
            requires_human_review=requires_human_review,
            review_reasons=review_reasons,
            conflict_detected=has_conflict,
            conflicting_sources=conflicts,
            search_latency_ms=round(latency_ms, 2),
            executed_at=datetime.now(timezone.utc).isoformat(),
        )

        await knowledge_audit_logger.log_search(final_result)

        # Broadcast completion & warning events
        if has_conflict:
            await self._broadcast_event(
                EventType.KNOWLEDGE_SOURCE_CONFLICT,
                query.call_id,
                {"query_id": query_id, "conflicts": [c.model_dump() for c in conflicts]},
            )

        if requires_human_review:
            await self._broadcast_event(
                EventType.KNOWLEDGE_REVIEW_RECOMMENDED,
                query.call_id,
                {"query_id": query_id, "reasons": review_reasons},
            )

        await self._broadcast_event(
            EventType.KNOWLEDGE_SEARCH_COMPLETED,
            query.call_id,
            final_result.model_dump(),
        )

        return final_result

    def list_sources(self) -> List[SourceDocument]:
        """Lists all registered documents."""
        return list(self._documents.values())

    def get_document(self, document_id: str) -> Optional[SourceDocument]:
        """Retrieves a specific document by its UUID."""
        return self._documents.get(document_id)

    def get_document_versions(self, document_id: str) -> List[DocumentVersion]:
        """Retrieves all versions for a document."""
        doc = self._documents.get(document_id)
        return doc.versions if doc else []

    def get_citation(self, citation_id: str) -> Optional[CitationMetadata]:
        """Retrieves a specific citation by ID."""
        return self._citations.get(citation_id)

    def _seed_default_corpus(self) -> None:
        """Seeds the in-memory retrieval engine with the deterministic test fixtures."""
        fixtures_dir = Path(__file__).parent / "fixtures"
        if not fixtures_dir.exists():
            return

        seed_configs = [
            {
                "file": "gov_scheme_current_en.md",
                "title": "One Stop Centre (OSC) Scheme Guidelines",
                "publisher": "Ministry of Women and Child Development, Government of India",
                "source_url": "https://wcd.nic.in/schemes/one-stop-centre-scheme-2.0",
                "jurisdiction": KnowledgeJurisdiction.INDIA.value,
                "language": "en-IN",
                "topic": TopicCategory.GOVERNMENT_SCHEME,
                "tier": AuthorityTier.TIER_1,
                "version": "2.0",
                "effective_from": "2022-04-01",
            },
            {
                "file": "tn_policy_current_ta.md",
                "title": "தமிழ்நாடு மகளிர் தங்குமிடம் மற்றும் பாதுகாப்பு வழிகாட்டுதல்கள்",
                "publisher": "சமூக நலன் மற்றும் மகளிர் உரிமைத் துறை, தமிழ்நாடு அரசு",
                "source_url": "https://tn.gov.in/schemes/women-shelter-guidelines-ta",
                "jurisdiction": KnowledgeJurisdiction.TAMIL_NADU.value,
                "language": "ta-IN",
                "topic": TopicCategory.PROTECTION,
                "tier": AuthorityTier.TIER_1,
                "version": "2.1",
                "effective_from": "2023-01-15",
            },
            {
                "file": "tn_policy_current_en.md",
                "title": "Government of Tamil Nadu Women Shelter and Protection Guidelines",
                "publisher": "Department of Social Welfare and Women Empowerment, Government of Tamil Nadu",
                "source_url": "https://tn.gov.in/schemes/women-shelter-guidelines-en",
                "jurisdiction": KnowledgeJurisdiction.TAMIL_NADU.value,
                "language": "en-IN",
                "topic": TopicCategory.PROTECTION,
                "tier": AuthorityTier.TIER_1,
                "version": "2.1",
                "effective_from": "2023-01-15",
            },
            {
                "file": "central_policy_en.md",
                "title": "Standard Operating Procedures for Women Helpline 181 and NHAA 14566",
                "publisher": "Ministry of Women and Child Development & NHA, Government of India",
                "source_url": "https://wcd.nic.in/guidelines/helpline-181-nh-14566-sop",
                "jurisdiction": KnowledgeJurisdiction.INDIA.value,
                "language": "en-IN",
                "topic": TopicCategory.HELPLINE,
                "tier": AuthorityTier.TIER_1,
                "version": "3.0",
                "effective_from": "2023-06-01",
            },
        ]

        for cfg in seed_configs:
            f_path = fixtures_dir / cfg["file"]
            if f_path.exists():
                try:
                    content = f_path.read_text(encoding="utf-8")
                    req = IngestionRequest(
                        title=cfg["title"],
                        publisher=cfg["publisher"],
                        source_url=cfg["source_url"],
                        content=content,
                        source_type=SourceType.MARKDOWN,
                        jurisdiction=cfg["jurisdiction"],
                        language=cfg["language"],
                        topic=cfg["topic"],
                        authority_tier=cfg["tier"],
                        version=cfg["version"],
                        effective_from=cfg["effective_from"],
                        verified=True,
                    )
                    self._ingest_sync(req, allow_test_fixtures=True)
                except Exception as e:
                    logger.warning(f"Failed to seed fixture {cfg['file']}: {e}")


# Global knowledge service singleton
knowledge_service = KnowledgeService(auto_seed=True)
