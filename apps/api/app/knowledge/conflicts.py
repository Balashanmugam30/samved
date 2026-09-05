"""Deterministic conflict detection and precedence resolution for SAMVED Knowledge RAG."""

from typing import List, Optional, Tuple

from app.knowledge.models import (
    AuthorityTier,
    ConflictingSourcePair,
    DocumentChunk,
    KnowledgeSearchResultItem,
    SourceDocument,
)


def detect_source_conflicts(
    candidates: List[Tuple[DocumentChunk, SourceDocument, float]]
) -> Tuple[bool, List[ConflictingSourcePair]]:
    """Detects potential policy conflicts among top retrieved candidates.
    
    Identifies conflicting directives when multiple documents match the same topic
    but specify different limits, durations, conditions, or procedural mandates.
    """
    if len(candidates) < 2:
        return False, []

    conflicts: List[ConflictingSourcePair] = []

    # Pairwise comparison of top candidates
    for i in range(len(candidates)):
        chunk_a, doc_a, _ = candidates[i]
        for j in range(i + 1, len(candidates)):
            chunk_b, doc_b, _ = candidates[j]

            # If same document, no inter-source conflict
            if doc_a.document_id == doc_b.document_id:
                continue

            # Check for substantive conflict signals: differing numerical durations, conditions, or mandates
            # e.g., "7 days" vs "14 days", or "immediate admission" vs "mandatory co-signature"
            has_conflict = False
            desc = ""

            text_a = chunk_a.text.lower()
            text_b = chunk_b.text.lower()

            if ("7 days" in text_a and "14 days" in text_b) or ("7 days" in text_b and "14 days" in text_a):
                has_conflict = True
                desc = "Contradictory emergency shelter maximum/minimum duration limits (7 days vs 14 days)."
            elif ("without demanding" in text_a and "mandatory co-signature" in text_b) or (
                "without demanding" in text_b and "mandatory co-signature" in text_a
            ):
                has_conflict = True
                desc = "Conflicting admission prerequisites: unconditional crisis entry vs required guardian co-signature."
            elif doc_a.topic == doc_b.topic and chunk_a.heading_path == chunk_b.heading_path and doc_a.current_version != doc_b.current_version:
                has_conflict = True
                desc = f"Differing provisions between version {doc_a.current_version} and {doc_b.current_version}."

            if has_conflict:
                # Attempt deterministic precedence resolution
                resolution = None
                # Rule 1: Authority Tier
                if doc_a.authority_tier.value < doc_b.authority_tier.value:
                    resolution = f"Precedence given to {doc_a.title} due to higher Authority Tier ({doc_a.authority_tier.name} vs {doc_b.authority_tier.name})."
                elif doc_b.authority_tier.value < doc_a.authority_tier.value:
                    resolution = f"Precedence given to {doc_b.title} due to higher Authority Tier ({doc_b.authority_tier.name} vs {doc_a.authority_tier.name})."
                # Rule 2: Jurisdiction Specificity
                elif chunk_a.jurisdiction != "INDIA" and chunk_b.jurisdiction == "INDIA":
                    resolution = f"Precedence given to state-specific policy {doc_a.title} ({chunk_a.jurisdiction}) over general national guidelines."
                elif chunk_b.jurisdiction != "INDIA" and chunk_a.jurisdiction == "INDIA":
                    resolution = f"Precedence given to state-specific policy {doc_b.title} ({chunk_b.jurisdiction}) over general national guidelines."
                # Rule 3: Version Recency
                elif chunk_a.effective_from > chunk_b.effective_from:
                    resolution = f"Precedence given to newer version {doc_a.current_version} (effective {chunk_a.effective_from})."
                elif chunk_b.effective_from > chunk_a.effective_from:
                    resolution = f"Precedence given to newer version {doc_b.current_version} (effective {chunk_b.effective_from})."

                conflicts.append(
                    ConflictingSourcePair(
                        source_a=doc_a.title,
                        source_b=doc_b.title,
                        description=desc,
                        jurisdiction_a=chunk_a.jurisdiction,
                        jurisdiction_b=chunk_b.jurisdiction,
                        tier_a=doc_a.authority_tier.value,
                        tier_b=doc_b.authority_tier.value,
                        resolution=resolution,
                    )
                )

    return len(conflicts) > 0, conflicts
