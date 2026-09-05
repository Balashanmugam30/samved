"""Test suite for Case Intelligence provenance and evidence hashing (Phase 11)."""

from app.cases.provenance import (
    compute_evidence_hash,
    create_evidence_link,
    validate_evidence_anchors,
    verify_excerpt_substring,
)


def test_compute_evidence_hash_deterministic():
    text1 = "I am calling from Chennai shelter."
    text2 = "  I am   calling from Chennai shelter.  "
    h1 = compute_evidence_hash(text1)
    h2 = compute_evidence_hash(text2)
    assert len(h1) == 64
    assert h1 == h2


def test_create_evidence_link_with_hash():
    excerpt = "My brother called earlier."
    link = create_evidence_link(
        source_type="CALL_TRANSCRIPT",
        source_id="call-123",
        turn_index=2,
        verbatim_excerpt=excerpt,
    )
    assert link.content_hash == compute_evidence_hash(excerpt)
    assert link.turn_index == 2


def test_validate_evidence_anchors():
    assert validate_evidence_anchors(source_refs=["turn:1"]) is True
    assert validate_evidence_anchors(source_refs=[]) is False
    assert validate_evidence_anchors(source_refs=[], evidence=[create_evidence_link("SRC", "1")]) is True


def test_verify_excerpt_substring():
    full_turn = "Hello counselor, my name is Priya and I need guidance about safe shelter."
    valid_excerpt = "my name is Priya"
    invalid_excerpt = "I want to file criminal charges"

    assert verify_excerpt_substring(full_turn, valid_excerpt) is True
    assert verify_excerpt_substring(full_turn, invalid_excerpt) is False
