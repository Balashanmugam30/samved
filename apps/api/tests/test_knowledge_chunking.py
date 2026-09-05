"""Tests for context-preserving chunking and qualifier preservation."""

import pytest
from app.knowledge.chunking import chunk_document, extract_qualifiers


def test_qualifier_extraction():
    sample_text = (
        "Subject to availability of beds, temporary shelter is provided. "
        "Provided that police assistance shall not apply without consent. "
        "Exception: nocturnal arrivals."
    )
    qualifiers = extract_qualifiers(sample_text)
    assert "subject to" in qualifiers
    assert "provided that" in qualifiers
    assert "exception" in qualifiers
    assert "shall not apply" in qualifiers


def test_chunking_heading_preservation():
    markdown_text = """# PWDVA Section 12
## Magistrate Application
Aggrieved women may apply directly for protection orders.

### Subsection 1
Provided that before passing any order, the Magistrate shall take into consideration the DIR.
"""
    chunks = chunk_document(
        document_id="doc-test",
        version="1.0",
        text=markdown_text,
        language="en-IN",
        jurisdiction="INDIA",
        effective_from="2022-01-01",
    )

    assert len(chunks) >= 2
    # Verify heading hierarchy was preserved
    last_chunk = chunks[-1]
    assert "PWDVA Section 12" in last_chunk.heading_path
    assert "Subsection 1" in last_chunk.section_page or "Subsection 1" in last_chunk.heading_path
    assert "provided that" in last_chunk.qualifiers
    assert last_chunk.content_hash != ""
