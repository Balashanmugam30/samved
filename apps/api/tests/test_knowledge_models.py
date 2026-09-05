"""Tests for knowledge data models and enum contracts."""

import pytest
from app.knowledge.models import (
    AuthorityTier,
    DocumentChunk,
    DocumentStatus,
    DocumentVersion,
    FreshnessStatus,
    KnowledgeJurisdiction,
    KnowledgeQuery,
    KnowledgeSearchResult,
    SourceDocument,
    SourceType,
    TopicCategory,
)
from app.schemas.events import CitationMetadata


def test_knowledge_enums():
    assert AuthorityTier.TIER_1.value == 1
    assert AuthorityTier.TIER_4.value == 4
    assert DocumentStatus.ACTIVE.value == "ACTIVE"
    assert DocumentStatus.SUPERSEDED.value == "SUPERSEDED"
    assert FreshnessStatus.CURRENT.value == "CURRENT"
    assert FreshnessStatus.STALE.value == "STALE"
    assert KnowledgeJurisdiction.INDIA.value == "INDIA"
    assert KnowledgeJurisdiction.TAMIL_NADU.value == "TAMIL_NADU"
    assert TopicCategory.PROTECTION.value == "PROTECTION"


def test_document_chunk_model():
    chunk = DocumentChunk(
        document_id="doc-1",
        version="1.0",
        heading_path=["Act", "Section 1"],
        section_page="Section 1",
        text="The aggrieved woman shall be entitled to emergency shelter.",
        language="en-IN",
        jurisdiction="INDIA",
        effective_from="2023-01-01",
        qualifiers=["entitled to"],
        content_hash="abc123hash",
    )
    assert chunk.document_id == "doc-1"
    assert "Section 1" in chunk.section_page
    assert len(chunk.qualifiers) == 1


def test_source_document_model():
    doc = SourceDocument(
        title="Domestic Violence Act Guidelines",
        publisher="Ministry of Women and Child Development",
        source_url="https://wcd.nic.in/dv-act",
        source_type=SourceType.MARKDOWN,
        jurisdiction="INDIA",
        language="en-IN",
        effective_from="2022-01-01",
        authority_tier=AuthorityTier.TIER_1,
        checksum="hash1",
        content_hash="hash2",
    )
    assert doc.title == "Domestic Violence Act Guidelines"
    assert doc.authority_tier == AuthorityTier.TIER_1
    assert doc.status == DocumentStatus.ACTIVE
    assert doc.verified_source is True


def test_knowledge_search_result_model():
    cit = CitationMetadata(
        citation_id="cit-1",
        document_id="doc-1",
        document_title="Title",
        publisher="Govt",
        version="1.0",
        section_page="Sec 1",
        effective_date="2023 to Present",
        source_url="https://gov.in",
        retrieved_at="2023-01-01T00:00:00Z",
        excerpt="Ex",
        authority_tier=1,
        jurisdiction="INDIA",
    )
    res = KnowledgeSearchResult(
        query="shelter options",
        status="COMPLETED",
        total_found=1,
        citations=[cit],
    )
    assert res.total_found == 1
    assert len(res.citations) == 1
    assert res.requires_human_review is False
