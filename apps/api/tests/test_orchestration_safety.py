"""Strict safety constraint verification tests for Multi-Agent Orchestration in SAMVED Phase 9."""

import pytest
from app.orchestration.models import AgentStatus, OrchestrationState
from app.orchestration.service import MultiAgentOrchestrator
from app.orchestration.workers import SupportOptionsAgent


@pytest.mark.asyncio
async def test_llm_worker_cannot_override_critical_safety():
    """Verify that even if caller transcript or advisory agent suggests safety,
    the deterministic safety engine evaluation remains authoritative."""
    orchestrator = MultiAgentOrchestrator()

    # Ambivalent transcript where caller says "I am fine now" but weapon threat was detected
    context = {
        "transcript": "I am fine now, don't worry",
        "text": "I am fine now, don't worry",
        "language": "ta-IN",
        "safety_state": "CRITICAL",
        "safety_evaluation": {
            "safety_state": "CRITICAL",
            "highest_severity": "HIGH",
            "action": "TRANSFER",
            "requires_intervention": True,
            "triggered_rules": [{"rule_id": "WEAPON_01", "name": "weapon_cue"}],
        },
        "svi": {"score": 0.92, "band": "CRITICAL"},
    }

    result = await orchestrator.orchestrate_turn(
        call_id="call-safety-precedence",
        turn_id="turn-1",
        context=context,
        safety_state="CRITICAL",
    )

    # 1. State must remain safe/completed without overriding the critical safety status
    assert result.validated_context is not None
    assert result.validated_context.safety_info["safety_state"] == "CRITICAL"
    assert result.validated_context.safety_info["is_authoritative"] is True

    # 2. Conflict resolution must explicitly record safety precedence
    assert len(result.validated_context.conflict_resolutions) > 0
    assert "absolute precedence" in result.validated_context.conflict_resolutions[0]

    # 3. Operator briefing must preserve CRITICAL alert
    assert "CRITICAL" in result.briefing.safety_summary


@pytest.mark.asyncio
async def test_support_options_strictly_stubbed_for_phase_10():
    """Verify that support options agent strictly guards Phase 10 boundary."""
    agent = SupportOptionsAgent()
    assert agent.spec.requires_human_review is True

    from app.orchestration.models import AgentRequest
    req = AgentRequest(call_id="c1", turn_id="t1", task_type="support")
    resp = await agent.execute(req)

    assert resp.result["status"] == "NOT_AVAILABLE"
    assert resp.result["reason"] == "NEEDS_KNOWLEDGE_BASE"
    assert "Phase 10" in resp.result["phase_target"]
    assert len(resp.result["options"]) == 0
