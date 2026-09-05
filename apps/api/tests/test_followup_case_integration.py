"""Integration tests for Case Graph and Multi-Agent Orchestration with Follow-ups."""

import pytest

from app.cases.service import get_case_service
from app.followup.schemas import CreateFollowupRequest
from app.followup.service import FollowupService
from app.orchestration.models import AgentRequest, AgentStatus
from app.orchestration.workers.followup_recommendation import FollowupRecommendationAgent
from app.schemas.events import ConsentState, EntityType, RelationshipType


@pytest.mark.asyncio
async def test_followup_creates_case_graph_node_and_edge():
    case_svc = get_case_service()
    fol_svc = FollowupService(auto_seed=False)

    # Create follow-up on case-1001
    req = CreateFollowupRequest(
        purpose="Verify graph edge creation for follow-up",
        scheduled_for="2026-09-05T18:30:00Z",
        safe_contact_window="18:00-20:00",
        consent_state=ConsentState.GRANTED,
        citation_ref="cit:policy:section4",
    )
    fol, warnings = await fol_svc.create_followup("case-1001", req)

    # Inspect case graph
    graph = await case_svc.get_graph("case-1001", max_depth=2)
    fol_node = next((n for n in graph.nodes if n.metadata.get("followup_id") == fol.followup_id), None)
    assert fol_node is not None
    assert fol_node.type == EntityType.FOLLOW_UP

    # Check for HAS_FOLLOW_UP edge
    has_edge = next(
        (e for e in graph.edges if e.relationship_type == RelationshipType.HAS_FOLLOW_UP and e.target_entity == fol_node.entity_id),
        None,
    )
    assert has_edge is not None


@pytest.mark.asyncio
async def test_followup_recommendation_agent_worker():
    agent = FollowupRecommendationAgent()
    req = AgentRequest(
        session_id="sess-test",
        call_id="call-test",
        turn_id="turn-1",
        task_type="continuity_planning",
        last_caller_utterance="Can someone please call me back tomorrow about the shelter?",
    )
    resp = await agent.execute(req)
    assert resp.status == AgentStatus.SUCCESS
    res = resp.result
    assert res["has_recommendation"] is True
    assert res["suggested_type"] == "HUMAN_CALLBACK"
    assert res["suggested_priority"] == "HIGH"
    assert res["requires_operator_confirmation"] is True
    assert res["no_autonomous_contact"] is True
