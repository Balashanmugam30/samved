"""Tests for worker agent contracts and implementations in SAMVED Phase 9."""

import pytest
from app.orchestration.models import (
    AgentRequest,
    AgentStatus,
    AgentType,
    AgentSafetyClassification,
)
from app.orchestration.workers import (
    AcousticContextAgent,
    ConversationContextAgent,
    LanguageContextAgent,
    OperatorBriefingAgent,
    SafetyContextAgent,
    SupportOptionsAgent,
)


@pytest.mark.asyncio
async def test_safety_context_agent():
    agent = SafetyContextAgent()
    assert agent.spec.agent_type == AgentType.DETERMINISTIC_ADAPTER
    assert agent.spec.safety_classification == AgentSafetyClassification.READ_ONLY_SAFETY

    req = AgentRequest(
        call_id="call-123",
        turn_id="turn-1",
        task_type="safety",
        relevant_context={
            "safety_state": "CRITICAL",
            "highest_severity": "HIGH",
            "action": "TRANSFER",
            "requires_intervention": True,
            "triggered_rules": [{"rule_id": "CRIT_01", "name": "weapon"}],
        },
    )
    resp = await agent.execute(req)
    assert resp.status == AgentStatus.SUCCESS
    assert resp.result["safety_state"] == "CRITICAL"
    assert resp.result["is_authoritative"] is True
    assert "rule:CRIT_01" in resp.evidence_refs


@pytest.mark.asyncio
async def test_acoustic_context_agent():
    agent = AcousticContextAgent()
    assert agent.spec.agent_type == AgentType.DETERMINISTIC_ADAPTER

    req = AgentRequest(
        call_id="call-123",
        turn_id="turn-1",
        task_type="acoustic",
        relevant_context={
            "acoustic_features": {
                "snr_db": 15.0,
                "distress_score": 0.82,
                "tremor_detected": True,
                "distress_crying": True,
                "speech_rate_wpm": 200,
            }
        },
    )
    resp = await agent.execute(req)
    assert resp.status == AgentStatus.SUCCESS
    assert resp.result["distress_crying"] is True
    assert "crying_detected" in resp.result["operational_signals"]
    assert "vocal_tremor" in resp.result["operational_signals"]
    assert "rapid_speech" in resp.result["operational_signals"]


@pytest.mark.asyncio
async def test_language_context_agent():
    agent = LanguageContextAgent()
    assert agent.spec.agent_type == AgentType.RULE_WORKER

    # Test Tanglish / code-switching detection
    req = AgentRequest(
        call_id="call-123",
        turn_id="turn-1",
        task_type="language",
        language="ta-IN",
        relevant_context={"transcript": "romba help venum please sir"},
    )
    resp = await agent.execute(req)
    assert resp.status == AgentStatus.SUCCESS
    assert resp.result["code_switching_detected"] is True
    assert "lang:code_switching_detected" in resp.evidence_refs


@pytest.mark.asyncio
async def test_conversation_context_agent():
    agent = ConversationContextAgent()
    assert agent.spec.agent_type == AgentType.LLM_WORKER

    req = AgentRequest(
        call_id="call-123",
        turn_id="turn-1",
        task_type="context",
        relevant_context={
            "transcript": "My husband attacked me yesterday in Chennai home",
            "history": [],
        },
    )
    resp = await agent.execute(req)
    assert resp.status == AgentStatus.SUCCESS
    assert "chennai" in resp.result["entities"]["locations"]
    assert "husband" in resp.result["entities"]["relations"]
    assert "yesterday" in resp.result["entities"]["timing"]


@pytest.mark.asyncio
async def test_support_options_agent_stub():
    agent = SupportOptionsAgent()
    assert agent.spec.agent_type == AgentType.INTERFACE_STUB
    assert agent.spec.safety_classification == AgentSafetyClassification.PLACEHOLDER

    req = AgentRequest(
        call_id="call-123",
        turn_id="turn-1",
        task_type="support",
    )
    resp = await agent.execute(req)
    assert resp.status == AgentStatus.SUCCESS
    assert resp.result["status"] == "NOT_AVAILABLE"
    assert resp.result["reason"] == "NEEDS_KNOWLEDGE_BASE"
    assert "Phase 10" in resp.result["phase_target"]


@pytest.mark.asyncio
async def test_operator_briefing_agent():
    agent = OperatorBriefingAgent()
    assert agent.spec.agent_type == AgentType.SUMMARIZER

    req = AgentRequest(
        call_id="call-123",
        turn_id="turn-1",
        task_type="briefing",
        relevant_context={
            "safety_state": "CRITICAL",
            "safety_info": {"safety_state": "CRITICAL", "highest_severity": "HIGH"},
            "acoustic_info": {"distress_score": 0.75, "operational_signals": ["vocal_tremor"], "snr_db": 14.0},
            "svi": {"score": 0.85, "tier": "CRITICAL", "top_factors": ["crying", "threat"]},
            "facts": {"key_facts": ["Caller is in Chennai", "Physical danger reported"]},
        },
    )
    resp = await agent.execute(req)
    assert resp.status == AgentStatus.SUCCESS
    assert "CRITICAL" in resp.result["safety_summary"]
    assert "0.85" in resp.result["svi_summary"]
    assert "vocal_tremor" in resp.result["acoustic_summary"]
