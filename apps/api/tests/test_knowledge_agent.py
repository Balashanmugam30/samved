"""Tests for KnowledgeRetrievalAgent in Multi-Agent Orchestration."""

import pytest
from app.orchestration.models import (
    AgentRequest,
    AgentSafetyClassification,
    AgentStatus,
    AgentType,
)
from app.orchestration.workers.knowledge_retrieval import KnowledgeRetrievalAgent


@pytest.mark.asyncio
async def test_knowledge_retrieval_agent_spec():
    agent = KnowledgeRetrievalAgent()
    assert agent.name == "knowledge_retrieval_agent"
    assert agent.spec.agent_type == AgentType.DETERMINISTIC_ADAPTER
    assert agent.spec.safety_classification == AgentSafetyClassification.OPERATIONAL
    assert agent.spec.requires_human_review is True
    assert "legal_policy_retrieval" in agent.spec.capabilities


@pytest.mark.asyncio
async def test_knowledge_retrieval_agent_execution():
    agent = KnowledgeRetrievalAgent()
    req = AgentRequest(
        call_id="call-agent-test",
        turn_id="turn-1",
        task_type="knowledge_retrieval",
        last_caller_utterance="One Stop Centre shelter stay guidelines",
        language="en-IN",
    )
    resp = await agent.execute(req)

    assert resp.status == AgentStatus.SUCCESS
    assert resp.agent_name == "knowledge_retrieval_agent"
    assert resp.result["status"] == "COMPLETED"
    assert resp.result["total_found"] > 0
    assert len(resp.result["citations"]) > 0
    assert len(resp.evidence_refs) > 0
    assert resp.latency_ms < 1000


@pytest.mark.asyncio
async def test_knowledge_retrieval_agent_fallback():
    agent = KnowledgeRetrievalAgent()
    req = AgentRequest(
        call_id="call-fallback",
        turn_id="turn-f",
        task_type="knowledge_retrieval",
    )
    fallback = agent.generate_fallback_result(req)
    assert fallback["status"] == "DEGRADED"
    assert fallback["requires_human_review"] is True
    assert len(fallback["results"]) == 0
