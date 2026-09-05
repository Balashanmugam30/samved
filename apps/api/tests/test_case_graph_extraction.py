"""Test suite for CaseGraphExtractionAgent worker and negation clause handling."""

import pytest
from app.cases.extraction import extract_case_candidates, is_sentence_negated
from app.orchestration.models import AgentRequest
from app.orchestration.workers.case_graph_extraction import CaseGraphExtractionAgent
from app.schemas.events import RelationshipType


def test_negation_clause_detection():
    assert is_sentence_negated("My sister is not at home") is True
    assert is_sentence_negated("Avar illai") is True
    assert is_sentence_negated("Vahan nahi hai") is True
    assert is_sentence_negated("I am with my sister in Chennai") is False


def test_negation_prevents_affirmative_location_edges():
    # Affirmitative sentence: should extract location
    aff_text = "I am currently staying in Chennai."
    _, aff_cands = extract_case_candidates("turn-1", aff_text)
    loc_cands = [c for c in aff_cands if c.relationship_type == RelationshipType.LOCATED_AT]
    assert len(loc_cands) >= 1

    # Negated sentence: should NOT extract location edge
    neg_text = "I am not staying in Chennai anymore."
    _, neg_cands = extract_case_candidates("turn-2", neg_text)
    neg_loc_cands = [c for c in neg_cands if c.relationship_type == RelationshipType.LOCATED_AT]
    assert len(neg_loc_cands) == 0


@pytest.mark.asyncio
async def test_case_graph_extraction_worker_execution():
    worker = CaseGraphExtractionAgent()
    request = AgentRequest(
        call_id="call-extract-worker-01",
        turn_id="turn-01",
        task_type="case_extraction",
        language="en-IN",
        last_caller_utterance="My sister Ananya is helping me from Chennai.",
    )

    response = await worker.execute(request)
    assert response.status.value in ("SUCCESS", "COMPLETED")
    assert response.result["total_candidates_proposed"] >= 1
    assert "case_id" in response.result
