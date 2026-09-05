"""Tests for MultiAgentOrchestrator coordinator in SAMVED Phase 9."""

import asyncio
import pytest
from app.orchestration.models import (
    AgentStatus,
    OrchestrationState,
)
from app.orchestration.service import MultiAgentOrchestrator


@pytest.mark.asyncio
async def test_multi_agent_orchestrator_turn_flow():
    orchestrator = MultiAgentOrchestrator()
    events_emitted = []

    async def callback(event_type, payload):
        events_emitted.append((event_type, payload))

    context = {
        "transcript": "Help me, my husband is hurting me in our Chennai house",
        "text": "Help me, my husband is hurting me in our Chennai house",
        "language": "ta-IN",
        "safety_state": "CRITICAL",
        "safety_evaluation": {
            "safety_state": "CRITICAL",
            "highest_severity": "HIGH",
            "requires_intervention": True,
            "triggered_rules": [{"rule_id": "PHYS_01", "name": "physical_violence"}],
        },
        "acoustic_features": {
            "snr_db": 12.0,
            "distress_score": 0.88,
            "tremor_detected": True,
            "distress_crying": True,
        },
        "svi": {"score": 0.89, "band": "CRITICAL"},
        "adaptive": {"action": "SAFETY_GROUNDING", "pacing": "slow"},
    }

    result = await orchestrator.orchestrate_turn(
        call_id="call-orchestrate-1",
        turn_id="turn-1",
        context=context,
        safety_state="CRITICAL",
        event_callback=callback,
    )

    assert result.state == OrchestrationState.COMPLETED
    assert len(result.completed_agents) >= 5
    assert result.briefing is not None
    assert "CRITICAL" in result.briefing.safety_summary
    assert result.total_latency_ms < 300  # Latency budget requirement

    # Check events
    event_names = [e[0] for e in events_emitted]
    assert "ORCHESTRATION_STARTED" in event_names
    assert "ORCHESTRATION_COMPLETED" in event_names


@pytest.mark.asyncio
async def test_multi_agent_orchestrator_barge_in_cancellation():
    orchestrator = MultiAgentOrchestrator()
    cancel_event = asyncio.Event()
    cancel_event.set()  # Simulate immediate barge-in

    result = await orchestrator.orchestrate_turn(
        call_id="call-barge-in",
        turn_id="turn-1",
        context={"transcript": "hello"},
        cancel_event=cancel_event,
    )

    assert result.state == OrchestrationState.DEGRADED
    assert any("caller barge-in" in w.lower() for w in result.warnings)
