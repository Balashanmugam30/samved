"""Tests for ContextAggregator in SAMVED Phase 9."""

import pytest
from app.orchestration.aggregation import ContextAggregator
from app.orchestration.models import AgentResponse, AgentStatus


def test_aggregation_safety_precedence():
    aggregator = ContextAggregator()

    safety_resp = AgentResponse(
        request_id="r1",
        call_id="c1",
        turn_id="t1",
        agent_name="safety_context_agent",
        status=AgentStatus.SUCCESS,
        result={"safety_state": "CRITICAL", "action": "TRANSFER", "is_authoritative": True},
        evidence_refs=["rule:CRIT_01"],
    )

    conv_resp = AgentResponse(
        request_id="r1",
        call_id="c1",
        turn_id="t1",
        agent_name="conversation_context_agent",
        status=AgentStatus.SUCCESS,
        result={
            "entities": {"locations": ["chennai"]},
            "contradictions": [{"type": "safety_ambivalence", "detail": "Caller claimed safe"}],
        },
        evidence_refs=["turn:t1"],
    )

    responses = {
        "safety_context_agent": safety_resp,
        "conversation_context_agent": conv_resp,
    }

    validated_ctx = aggregator.aggregate(responses, base_context={"safety_state": "CRITICAL"})

    # Check safety info is authoritative
    assert validated_ctx.safety_info["safety_state"] == "CRITICAL"
    assert "rule:CRIT_01" in validated_ctx.evidence_refs
    assert "turn:t1" in validated_ctx.evidence_refs

    # Check conflict resolution logged
    assert len(validated_ctx.conflict_resolutions) > 0
    assert "absolute precedence" in validated_ctx.conflict_resolutions[0]
