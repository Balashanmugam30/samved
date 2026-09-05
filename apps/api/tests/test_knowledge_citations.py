"""Tests for citation creation and integrity validation."""

import pytest
from app.knowledge.citations import create_citation, validate_citation_integrity
from app.knowledge.models import AuthorityTier, DocumentChunk, SourceDocument, SourceType


def test_citation_creation_and_validation():
    doc = SourceDocument(
        document_id="doc-123",
        title="Helpline Standard Operating Procedure",
        publisher="National Authority",
        source_url="https://wcd.nic.in/sop",
        source_type=SourceType.MARKDOWN,
        jurisdiction="INDIA",
        effective_from="2023-01-01",
        authority_tier=AuthorityTier.TIER_1,
        checksum="chk",
        content_hash="cnt",
        verified_source=True,
    )
    chunk = DocumentChunk(
        chunk_id="chk-456",
        document_id="doc-123",
        version="1.0",
        heading_path=["SOP", "Section 1"],
        section_page="Section 1",
        text="All calls received on 181 shall be triaged within 15 minutes.",
        language="en-IN",
        jurisdiction="INDIA",
        effective_from="2023-01-01",
        content_hash="h1",
    )

    cit = create_citation(chunk, doc, excerpt="All calls received on 181 shall be triaged within 15 minutes.")
    assert cit.document_id == "doc-123"
    assert cit.version == "1.0"
    assert cit.authority_tier == 1

    # Validate integrity
    is_valid, error = validate_citation_integrity(cit, chunk, doc)
    assert is_valid is True
    assert error is None


def test_citation_integrity_detects_fabricated_excerpt():
    doc = SourceDocument(
        document_id="doc-123",
        title="Helpline Standard Operating Procedure",
        publisher="National Authority",
        source_url="https://wcd.nic.in/sop",
        effective_from="2023-01-01",
        authority_tier=AuthorityTier.TIER_1,
        checksum="chk",
        content_hash="cnt",
        verified_source=True,
    )
    chunk = DocumentChunk(
        chunk_id="chk-456",
        document_id="doc-123",
        version="1.0",
        heading_path=["SOP"],
        text="Official verified text.",
        language="en-IN",
        jurisdiction="INDIA",
        effective_from="2023-01-01",
        content_hash="h1",
    )

    # Fabricated excerpt not found in chunk
    cit = create_citation(chunk, doc, excerpt="Fabricated clause granting 100% legal indemnity.")
    is_valid, error = validate_citation_integrity(cit, chunk, doc)
    assert is_valid is False
    assert "not a verbatim substring" in error
