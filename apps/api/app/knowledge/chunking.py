"""Deterministic, context-preserving chunking for SAMVED Knowledge RAG."""

import re
import uuid
from typing import List

from app.knowledge.models import DocumentChunk
from app.knowledge.normalization import compute_sha256

# Critical statutory qualifiers that must be detected and attached to chunk metadata
QUALIFIER_PATTERNS = [
    r"\bsubject to\b",
    r"\bprovided that\b",
    r"\bnotwithstanding\b",
    r"\bexcept\b",
    r"\bexception\b",
    r"\bdefined as\b",
    r"\bdefinition\b",
    r"\bapplicability\b",
    r"\bapplicable to\b",
    r"\beligibility\b",
    r"\bcondition\b",
    r"\bshall not apply\b",
    r"\bவிதிவிலக்கு\b",  # Tamil: exception
    r"\bநிபந்தனை\b",     # Tamil: condition
    r"\bअपवाद\b",          # Hindi: exception
    r"\bशर्त\b",           # Hindi: condition
]


def extract_qualifiers(text: str) -> List[str]:
    """Identifies critical legal qualifiers present in chunk text."""
    found = []
    text_lower = text.lower()
    for pattern in QUALIFIER_PATTERNS:
        match = re.search(pattern, text_lower)
        if match:
            found.append(match.group(0))
    return sorted(list(set(found)))


def chunk_document(
    document_id: str,
    version: str,
    text: str,
    language: str,
    jurisdiction: str,
    effective_from: str,
    effective_to: str = None,
    max_chunk_chars: int = 1200,
    overlap_chars: int = 150,
) -> List[DocumentChunk]:
    """Splits normalized document into deterministic chunks preserving heading paths and qualifiers.
    
    Uses Markdown headers (#, ##, ###) as semantic section boundaries,
    ensuring legal clauses and their exceptions remain tightly coupled.
    """
    lines = text.split("\n")
    chunks: List[DocumentChunk] = []

    current_heading_path: List[str] = []
    current_section = "Preamble"
    current_lines: List[str] = []
    current_para_index = 0

    def finalize_chunk(lines_to_flush: List[str], sec_page: str, h_path: List[str]) -> None:
        nonlocal current_para_index
        content = "\n".join(lines_to_flush).strip()
        if not content:
            return

        qualifiers = extract_qualifiers(content)
        chunk_hash = compute_sha256(content)
        current_para_index += 1

        chunks.append(
            DocumentChunk(
                chunk_id=str(uuid.uuid4()),
                document_id=document_id,
                version=version,
                heading_path=list(h_path),
                section_page=sec_page,
                paragraph_range=f"Paragraph {current_para_index}",
                text=content,
                language=language,
                jurisdiction=jurisdiction,
                effective_from=effective_from,
                effective_to=effective_to,
                qualifiers=qualifiers,
                content_hash=chunk_hash,
            )
        )

    for line in lines:
        stripped = line.strip()
        header_match = re.match(r"^(#{1,4})\s+(.+)$", stripped)

        if header_match:
            # Flush accumulated lines under previous header
            if current_lines:
                finalize_chunk(current_lines, current_section, current_heading_path)
                current_lines = []

            depth = len(header_match.group(1))
            title = header_match.group(2).strip()

            # Adjust heading hierarchy according to depth
            if depth <= len(current_heading_path):
                current_heading_path = current_heading_path[: depth - 1]
            current_heading_path.append(title)
            current_section = title
            continue

        if not stripped:
            # Paragraph separator: if accumulated chunk is large enough, finalize it
            if sum(len(l) for l in current_lines) >= max_chunk_chars:
                finalize_chunk(current_lines, current_section, current_heading_path)
                # Apply overlap if lines available
                if current_lines and overlap_chars > 0:
                    current_lines = [current_lines[-1]]
                else:
                    current_lines = []
            continue

        current_lines.append(stripped)

    # Flush final accumulated chunk
    if current_lines:
        finalize_chunk(current_lines, current_section, current_heading_path)

    # Fallback if no sections or empty text
    if not chunks and text.strip():
        content = text.strip()
        chunks.append(
            DocumentChunk(
                chunk_id=str(uuid.uuid4()),
                document_id=document_id,
                version=version,
                heading_path=["General Document"],
                section_page="General",
                paragraph_range="Paragraph 1",
                text=content,
                language=language,
                jurisdiction=jurisdiction,
                effective_from=effective_from,
                effective_to=effective_to,
                qualifiers=extract_qualifiers(content),
                content_hash=compute_sha256(content),
            )
        )

    return chunks
