"""Tests for metadata-aware retrieval and reranking."""

import pytest
from app.knowledge.models import KnowledgeJurisdiction, KnowledgeQuery
from app.knowledge.service import KnowledgeService


@pytest.mark.asyncio
async def test_search_national_osc_scheme():
    service = KnowledgeService(auto_seed=True)
    query = KnowledgeQuery(
        query="One Stop Centre temporary shelter days",
        jurisdiction=KnowledgeJurisdiction.INDIA.value,
        effective_only=True,
    )
    res = await service.search(query)

    assert res.status == "COMPLETED"
    assert res.total_found > 0
    top = res.results[0]
    assert "One Stop Centre" in top.title
    assert top.authority_tier == 1
    assert "5 days" in top.excerpt
    assert len(res.citations) > 0


@pytest.mark.asyncio
async def test_search_tamil_nadu_specific_policy():
    service = KnowledgeService(auto_seed=True)
    query = KnowledgeQuery(
        query="Tamil Nadu women shelter admission emergency 48 hours",
        jurisdiction=KnowledgeJurisdiction.TAMIL_NADU.value,
        effective_only=True,
    )
    res = await service.search(query)

    assert res.status == "COMPLETED"
    assert res.total_found > 0
    top = res.results[0]
    assert "Tamil Nadu" in top.title or "தமிழ்நாடு" in top.title
    assert top.jurisdiction == "TAMIL_NADU"


@pytest.mark.asyncio
async def test_unsupported_query_returns_no_reliable_source():
    service = KnowledgeService(auto_seed=True)
    query = KnowledgeQuery(
        query="imaginary statutory clause XYZ999 regarding spaceship ownership",
        effective_only=True,
    )
    res = await service.search(query)

    assert res.status == "NO_RELIABLE_SOURCE_FOUND"
    assert res.total_found == 0
    assert res.requires_human_review is True
    assert "No sufficiently authoritative source was found" in res.ai_summary
