"""Tests for document ingestion workflow and validation."""

import pytest
from app.knowledge.models import (
    AuthorityTier,
    DocumentStatus,
    IngestionRequest,
    SourceType,
    TopicCategory,
)
from app.knowledge.service import KnowledgeService


@pytest.mark.asyncio
async def test_successful_document_ingestion():
    service = KnowledgeService(auto_seed=False)
    req = IngestionRequest(
        title="Test Protection Guidelines",
        publisher="Department of Social Welfare",
        source_url="https://tn.gov.in/test-policy",
        content="# Section 1\nEmergency assistance is guaranteed within 24 hours.",
        source_type=SourceType.MARKDOWN,
        jurisdiction="TAMIL_NADU",
        language="en-IN",
        topic=TopicCategory.PROTECTION,
        authority_tier=AuthorityTier.TIER_1,
        version="1.0",
        effective_from="2023-01-01",
    )
    doc = await service.ingest_document(req, allow_test_fixtures=True)

    assert doc.title == "Test Protection Guidelines"
    assert doc.status == DocumentStatus.ACTIVE
    assert doc.authority_tier == AuthorityTier.TIER_1
    assert len(doc.versions) == 1
    assert len(doc.versions[0].chunks) >= 1
    assert doc.checksum != ""
    assert doc.content_hash != ""


@pytest.mark.asyncio
async def test_duplicate_content_ingestion():
    service = KnowledgeService(auto_seed=False)
    req = IngestionRequest(
        title="Identical Policy",
        publisher="Ministry",
        source_url="https://wcd.nic.in/identical",
        content="Identical content line.",
        version="1.0",
    )
    doc1 = await service.ingest_document(req, allow_test_fixtures=True)
    doc2 = await service.ingest_document(req, allow_test_fixtures=True)

    # Document ID should be preserved, no extra duplicate versions added
    assert doc1.document_id == doc2.document_id
    assert len(doc2.versions) == 1


@pytest.mark.asyncio
async def test_new_version_superseding_ingestion():
    service = KnowledgeService(auto_seed=False)
    req_v1 = IngestionRequest(
        title="Evolving SOP",
        publisher="Helpline Bureau",
        source_url="https://wcd.nic.in/sop",
        content="Version 1 procedures: 3 days stay.",
        version="1.0",
        effective_from="2020-01-01",
        effective_to="2022-12-31",
    )
    doc_v1 = await service.ingest_document(req_v1, allow_test_fixtures=True)
    assert doc_v1.current_version == "1.0"
    assert doc_v1.versions[0].status == DocumentStatus.ACTIVE

    req_v2 = IngestionRequest(
        title="Evolving SOP",
        publisher="Helpline Bureau",
        source_url="https://wcd.nic.in/sop",
        content="Version 2 procedures: 7 days stay.",
        version="2.0",
        effective_from="2023-01-01",
    )
    doc_v2 = await service.ingest_document(req_v2, allow_test_fixtures=True)

    assert doc_v2.current_version == "2.0"
    assert len(doc_v2.versions) == 2
    # Prior version superseded
    assert doc_v2.versions[0].status == DocumentStatus.SUPERSEDED
    assert doc_v2.versions[0].superseded_by == "2.0"
    # New version active
    assert doc_v2.versions[1].status == DocumentStatus.ACTIVE
    assert doc_v2.versions[1].supersedes == "1.0"
