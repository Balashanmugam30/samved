"""Tests for conflict detection and deterministic precedence resolution."""

from pathlib import Path
import pytest
from app.knowledge.models import (
    AuthorityTier,
    IngestionRequest,
    KnowledgeQuery,
    SourceType,
)
from app.knowledge.service import KnowledgeService


@pytest.mark.asyncio
async def test_policy_conflict_detection_and_flagging():
    service = KnowledgeService(auto_seed=False)
    fixtures_dir = Path(__file__).parent.parent / "app" / "knowledge" / "fixtures"

    content_a = (fixtures_dir / "conflicting_policy_a.md").read_text(encoding="utf-8")
    content_b = (fixtures_dir / "conflicting_policy_b.md").read_text(encoding="utf-8")

    req_a = IngestionRequest(
        title="Regional Advisory Circular A",
        publisher="State Social Welfare Board",
        source_url="https://welfare.gov.in/circular-a",
        content=content_a,
        source_type=SourceType.MARKDOWN,
        authority_tier=AuthorityTier.TIER_2,
        version="1.0",
        effective_from="2024-01-10",
    )
    req_b = IngestionRequest(
        title="Regional Advisory Circular B",
        publisher="Metropolitan Welfare Board",
        source_url="https://welfare.gov.in/circular-b",
        content=content_b,
        source_type=SourceType.MARKDOWN,
        authority_tier=AuthorityTier.TIER_2,
        version="1.0",
        effective_from="2024-02-15",
    )

    await service.ingest_document(req_a, allow_test_fixtures=True)
    await service.ingest_document(req_b, allow_test_fixtures=True)

    query = KnowledgeQuery(
        query="Emergency shelter duration limit days",
        effective_only=True,
    )
    res = await service.search(query)

    assert res.status == "CONFLICT"
    assert res.conflict_detected is True
    assert res.requires_human_review is True
    assert len(res.conflicting_sources) > 0
    conflict_desc = res.conflicting_sources[0].description
    assert "7 days vs 14 days" in conflict_desc
    assert "WARNING" in res.ai_summary or "conflict" in res.ai_summary.lower()
