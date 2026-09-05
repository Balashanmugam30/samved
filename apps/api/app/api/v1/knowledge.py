"""REST API Router for SAMVED Phase 10 Legal / Policy Knowledge RAG."""

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field

from app.knowledge.models import (
    AuthorityTier,
    CitationMetadata,
    DocumentStatus,
    DocumentVersion,
    IngestionRequest,
    KnowledgeJurisdiction,
    KnowledgeQuery,
    KnowledgeSearchResult,
    SourceDocument,
    TopicCategory,
)
from app.knowledge.service import knowledge_service
from app.knowledge.sources import SecurityValidationError

router = APIRouter(prefix="/knowledge", tags=["Legal & Policy Knowledge RAG"])


class KnowledgeSearchRequest(BaseModel):
    query: str = Field(..., min_length=2, description="Search query string")
    language: Optional[str] = Field(default=None, description="e.g., en-IN, ta-IN, hi-IN")
    jurisdiction: Optional[str] = Field(
        default=None, description="INDIA, TAMIL_NADU, CENTRAL_GOVERNMENT"
    )
    topic: Optional[TopicCategory] = Field(default=None)
    source_tiers: Optional[List[int]] = Field(
        default=None, description="Filter by authority tiers [1, 2, 3, 4]"
    )
    as_of_date: Optional[str] = Field(
        default=None, description="Effective date evaluation point (YYYY-MM-DD)"
    )
    effective_only: bool = Field(default=True, description="Filter to ACTIVE effective versions")
    max_results: int = Field(default=5, ge=1, le=20)
    call_id: Optional[str] = Field(default=None)


class KnowledgeStatusResponse(BaseModel):
    status: str
    index_version: str
    total_documents: int
    total_chunks: int
    active_documents: int
    supported_jurisdictions: List[str]
    authority_hierarchy: List[Dict[str, Any]]


class KnowledgeSourcesListResponse(BaseModel):
    total_sources: int
    sources: List[SourceDocument]


@router.get("/status", response_model=KnowledgeStatusResponse)
async def get_knowledge_status():
    """Retrieves operational status, index metrics, and authority hierarchy."""
    return knowledge_service.get_status()


@router.get("/sources", response_model=KnowledgeSourcesListResponse)
async def list_sources():
    """Lists all registered legal and policy documents in the corpus."""
    sources = knowledge_service.list_sources()
    return KnowledgeSourcesListResponse(
        total_sources=len(sources),
        sources=sources,
    )


@router.get("/documents/{document_id}", response_model=SourceDocument)
async def get_document(document_id: str):
    """Retrieves a specific document and its metadata by UUID."""
    doc = knowledge_service.get_document(document_id)
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document '{document_id}' not found.",
        )
    return doc


@router.get("/documents/{document_id}/versions", response_model=List[DocumentVersion])
async def get_document_versions(document_id: str):
    """Retrieves all version history for a specific document."""
    doc = knowledge_service.get_document(document_id)
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document '{document_id}' not found.",
        )
    return doc.versions


@router.post("/search", response_model=KnowledgeSearchResult)
async def search_knowledge(req: KnowledgeSearchRequest):
    """Performs citation-first search with metadata filtering, conflict detection, and grounded summary."""
    query = KnowledgeQuery(
        query=req.query,
        language=req.language,
        jurisdiction=req.jurisdiction,
        topic=req.topic,
        source_tiers=req.source_tiers,
        as_of_date=req.as_of_date,
        effective_only=req.effective_only,
        max_results=req.max_results,
        call_id=req.call_id,
    )
    result = await knowledge_service.search(query)
    return result


@router.post("/ingest", response_model=SourceDocument, status_code=status.HTTP_201_CREATED)
async def ingest_document(req: IngestionRequest):
    """Ingests, validates, hashes, chunks, and indexes a new document or version.
    
    Restricted/Privileged operation protected against SSRF and oversized payloads.
    """
    try:
        doc = await knowledge_service.ingest_document(req, allow_test_fixtures=True)
        return doc
    except SecurityValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Security validation failed: {str(e)}",
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ingestion failed: {str(e)}",
        )


@router.get("/citations/{citation_id}", response_model=CitationMetadata)
async def get_citation(citation_id: str):
    """Retrieves specific citation metadata and provenance by UUID."""
    citation = knowledge_service.get_citation(citation_id)
    if not citation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Citation '{citation_id}' not found.",
        )
    return citation
