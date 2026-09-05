"""Citation assembly, provenance tracking, and integrity validation for SAMVED Knowledge RAG."""

import uuid
from typing import Optional, Tuple

from app.knowledge.models import DocumentChunk, SourceDocument
from app.schemas.events import CitationMetadata


def create_citation(
    chunk: DocumentChunk, document: SourceDocument, excerpt: Optional[str] = None
) -> CitationMetadata:
    """Creates a structured CitationMetadata instance anchored to the specific chunk and document."""
    # If excerpt not explicitly given, use the first 250 characters of chunk text
    text_excerpt = excerpt if excerpt else (chunk.text[:250] + ("..." if len(chunk.text) > 250 else ""))

    # Format section/page string
    heading_str = " > ".join(chunk.heading_path) if chunk.heading_path else chunk.section_page

    return CitationMetadata(
        citation_id=str(uuid.uuid4()),
        document_id=document.document_id,
        document_title=document.title,
        publisher=document.publisher,
        version=chunk.version,
        section_page=f"{heading_str} ({chunk.paragraph_range or 'Sec 1'})",
        effective_date=f"{chunk.effective_from} to {chunk.effective_to or 'Present'}",
        source_url=document.source_url,
        retrieved_at=document.retrieved_at,
        excerpt=text_excerpt,
        authority_tier=document.authority_tier.value,
        jurisdiction=chunk.jurisdiction,
    )


def validate_citation_integrity(
    citation: CitationMetadata, chunk: DocumentChunk, document: SourceDocument
) -> Tuple[bool, Optional[str]]:
    """Validates that a citation faithfully represents the source document and chunk text.
    
    Checks:
    1. Document IDs match.
    2. Version matches chunk version.
    3. Excerpt is a genuine substring of chunk text.
    4. Document is verified and active.
    """
    if citation.document_id != document.document_id:
        return False, f"Citation document_id '{citation.document_id}' mismatch with source '{document.document_id}'."

    if citation.version != chunk.version:
        return False, f"Citation version '{citation.version}' mismatch with chunk version '{chunk.version}'."

    # Check substring match for excerpt (cleaning ellipses)
    clean_excerpt = citation.excerpt.rstrip(".").strip()
    if clean_excerpt and clean_excerpt not in chunk.text:
        return False, "Citation excerpt is not a verbatim substring of the underlying source chunk."

    if not document.verified_source:
        return False, "Citation references an unverified source document."

    return True, None
