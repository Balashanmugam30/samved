"""SAMVED Phase 10 Legal / Policy Knowledge Retrieval Package."""

from app.knowledge.audit import KnowledgeAuditLogger, knowledge_audit_logger
from app.knowledge.chunking import chunk_document, extract_qualifiers
from app.knowledge.citations import create_citation, validate_citation_integrity
from app.knowledge.conflicts import detect_source_conflicts
from app.knowledge.grounding import (
    GroundedAnswer,
    GroundedClaim,
    build_safe_grounded_prompt,
    synthesize_deterministic_summary,
    validate_grounded_answer,
)
from app.knowledge.indexing import INDEX_VERSION, InvertedIndex
from app.knowledge.models import (
    AuthorityTier,
    CitationMetadata,
    ConflictingSourcePair,
    DocumentChunk,
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
    sanitize_text,
)
from app.knowledge.service import KnowledgeService, knowledge_service
from app.knowledge.sources import (
    SecurityValidationError,
    determine_authority_tier,
    validate_document_size,
    validate_source_url_ssrf,
)
from app.knowledge.versioning import (
    VersionManager,
    calculate_freshness,
    is_version_effective,
)

__all__ = [
    "AuthorityTier",
    "CitationMetadata",
    "ConflictingSourcePair",
    "DocumentChunk",
    "DocumentStatus",
    "DocumentVersion",
    "FreshnessStatus",
    "GroundedAnswer",
    "GroundedClaim",
    "INDEX_VERSION",
    "IngestionAuditRecord",
    "IngestionRequest",
    "InvertedIndex",
    "KnowledgeAuditLogger",
    "KnowledgeJurisdiction",
    "KnowledgeQuery",
    "KnowledgeSearchResult",
    "KnowledgeSearchResultItem",
    "KnowledgeService",
    "SecurityValidationError",
    "SourceDocument",
    "SourceType",
    "TopicCategory",
    "VersionManager",
    "build_safe_grounded_prompt",
    "calculate_freshness",
    "chunk_document",
    "compute_sha256",
    "create_citation",
    "detect_source_conflicts",
    "determine_authority_tier",
    "extract_qualifiers",
    "is_version_effective",
    "knowledge_audit_logger",
    "knowledge_service",
    "normalize_and_hash",
    "normalize_source_url",
    "sanitize_text",
    "synthesize_deterministic_summary",
    "validate_citation_integrity",
    "validate_document_size",
    "validate_grounded_answer",
    "validate_source_url_ssrf",
]
