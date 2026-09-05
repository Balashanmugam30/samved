"""Provenance & Evidence Anchor Layer for Case Intelligence (Phase 11)."""

import hashlib
from typing import List, Optional
from app.cases.models import CaseEvidenceLink


def compute_evidence_hash(text: str) -> str:
    """Computes deterministic SHA-256 digest of normalized evidence text."""
    if not text:
        return ""
    normalized = " ".join(text.strip().split())
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def create_evidence_link(
    source_type: str,
    source_id: str,
    turn_index: Optional[int] = None,
    verbatim_excerpt: Optional[str] = None,
    citation_ref: Optional[str] = None,
    confidence: float = 1.0,
) -> CaseEvidenceLink:
    """Creates a strongly anchored CaseEvidenceLink with cryptographic hash."""
    content_hash = (
        compute_evidence_hash(verbatim_excerpt) if verbatim_excerpt else None
    )
    return CaseEvidenceLink(
        source_type=source_type,
        source_id=source_id,
        turn_index=turn_index,
        verbatim_excerpt=verbatim_excerpt,
        citation_ref=citation_ref,
        content_hash=content_hash,
        confidence=confidence,
    )


def validate_evidence_anchors(
    source_refs: List[str], evidence: Optional[List[CaseEvidenceLink]] = None
) -> bool:
    """Validates that a node or edge possesses at least one valid source reference or evidence link."""
    if source_refs and any(ref.strip() for ref in source_refs):
        return True
    if evidence and len(evidence) > 0:
        return True
    return False


def verify_excerpt_substring(full_turn_text: str, excerpt: str) -> bool:
    """Verifies that an extracted verbatim excerpt actually occurs within the claimed turn."""
    if not full_turn_text or not excerpt:
        return False
    norm_full = " ".join(full_turn_text.lower().split())
    norm_excerpt = " ".join(excerpt.lower().split())
    return norm_excerpt in norm_full
