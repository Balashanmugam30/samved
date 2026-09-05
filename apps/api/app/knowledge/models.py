"""Data models and schemas for SAMVED Phase 10 Legal / Policy Knowledge RAG."""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
import uuid
from pydantic import BaseModel, Field

from app.schemas.events import (
    AuthorityTier,
    CitationMetadata,
    DocumentStatus,
    FreshnessStatus,
    KnowledgeJurisdiction,
)


class SourceType(str, Enum):
    PDF = "PDF"
    HTML = "HTML"
    TEXT = "TEXT"
    MARKDOWN = "MARKDOWN"


class TopicCategory(str, Enum):
    SERVICES = "SERVICES"
    PROCEDURE = "PROCEDURE"
    PROTECTION = "PROTECTION"
    HELPLINE = "HELPLINE"
    GOVERNMENT_SCHEME = "GOVERNMENT_SCHEME"
    LEGAL_INFORMATION = "LEGAL_INFORMATION"
    EMERGENCY_SUPPORT = "EMERGENCY_SUPPORT"


class DocumentChunk(BaseModel):
    chunk_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    document_id: str
    version: str
    heading_path: List[str] = Field(default_factory=list)
    section_page: str = "General"
    paragraph_range: Optional[str] = None
    text: str
    language: str = "en-IN"
    jurisdiction: str = KnowledgeJurisdiction.INDIA.value
    effective_from: str
    effective_to: Optional[str] = None
    qualifiers: List[str] = Field(default_factory=list)
    content_hash: str


class DocumentVersion(BaseModel):
    version_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    document_id: str
    version_number: str
    effective_from: str
    effective_to: Optional[str] = None
    retrieved_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    status: DocumentStatus = DocumentStatus.ACTIVE
    superseded_by: Optional[str] = None
    supersedes: Optional[str] = None
    checksum: str
    content_hash: str
    chunks: List[DocumentChunk] = Field(default_factory=list)


class SourceDocument(BaseModel):
    document_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    title: str
    publisher: str
    source_url: str
    source_type: SourceType = SourceType.MARKDOWN
    jurisdiction: str = KnowledgeJurisdiction.INDIA.value
    language: str = "en-IN"
    topic: TopicCategory = TopicCategory.GOVERNMENT_SCHEME
    issued_at: Optional[str] = None
    effective_from: str
    effective_to: Optional[str] = None
    retrieved_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    current_version: str = "1.0"
    status: DocumentStatus = DocumentStatus.ACTIVE
    authority_tier: AuthorityTier = AuthorityTier.TIER_1
    checksum: str = ""
    content_hash: str = ""
    license_notes: Optional[str] = "Official Public Information / Fair Use Guidance"
    verified_source: bool = True
    verification_method: str = "official_gazette_checksum"
    verified_at: Optional[str] = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    versions: List[DocumentVersion] = Field(default_factory=list)


class KnowledgeQuery(BaseModel):
    query: str
    language: Optional[str] = None
    jurisdiction: Optional[str] = None
    topic: Optional[TopicCategory] = None
    source_tiers: Optional[List[int]] = None
    as_of_date: Optional[str] = None
    effective_only: bool = True
    max_results: int = 5
    call_id: Optional[str] = None


class KnowledgeSearchResultItem(BaseModel):
    document_id: str
    version: str
    title: str
    publisher: str
    jurisdiction: str
    source_url: str
    chunk_id: str
    excerpt: str
    relevance: float
    authority_tier: int
    effective_status: str
    source_date: str
    retrieved_at: str
    citation: CitationMetadata


class ConflictingSourcePair(BaseModel):
    source_a: str
    source_b: str
    description: str
    jurisdiction_a: str
    jurisdiction_b: str
    tier_a: int
    tier_b: int
    resolution: Optional[str] = None


class KnowledgeSearchResult(BaseModel):
    query_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    call_id: Optional[str] = None
    query: str
    status: str = "COMPLETED"  # COMPLETED, NO_RELIABLE_SOURCE_FOUND, CONFLICT, DEGRADED, FAILED
    total_found: int = 0
    results: List[KnowledgeSearchResultItem] = Field(default_factory=list)
    citations: List[CitationMetadata] = Field(default_factory=list)
    ai_summary: Optional[str] = None
    requires_human_review: bool = False
    review_reasons: List[str] = Field(default_factory=list)
    conflict_detected: bool = False
    conflicting_sources: List[ConflictingSourcePair] = Field(default_factory=list)
    search_latency_ms: float = 0.0
    executed_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


class IngestionRequest(BaseModel):
    title: str
    publisher: str
    source_url: str
    content: str
    source_type: SourceType = SourceType.MARKDOWN
    jurisdiction: str = KnowledgeJurisdiction.INDIA.value
    language: str = "en-IN"
    topic: TopicCategory = TopicCategory.GOVERNMENT_SCHEME
    authority_tier: AuthorityTier = AuthorityTier.TIER_1
    version: str = "1.0"
    issued_at: Optional[str] = None
    effective_from: Optional[str] = None
    effective_to: Optional[str] = None
    license_notes: Optional[str] = None
    verified: bool = True
    verification_method: str = "manual_ingestion"


class IngestionAuditRecord(BaseModel):
    audit_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    document_id: str
    version: str
    source_url: str
    action: str  # INGEST, UPDATE_VERSION, SUPERSEDE, RETIRE, REJECT
    status: DocumentStatus
    content_hash: str
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    details: Dict[str, Any] = Field(default_factory=dict)
