"""Tests for AgentRegistry in SAMVED Phase 9."""

import pytest
from app.orchestration.models import (
    AgentSafetyClassification,
    AgentSpec,
    AgentTimeoutTier,
    AgentType,
)
from app.orchestration.registry import AgentRegistry
from app.orchestration.contracts import BaseAgentWorker
from app.orchestration.models import AgentRequest, AgentResponse


class DummyWorker(BaseAgentWorker):
    def __init__(self, name: str = "dummy_worker", caps: list = None):
        spec = AgentSpec(
            name=name,
            version="1.0.0",
            agent_type=AgentType.RULE_WORKER,
            capabilities=caps or ["dummy_task"],
            timeout_tier=AgentTimeoutTier.REALTIME_NORMAL,
            max_latency_ms=100,
            safety_classification=AgentSafetyClassification.OPERATIONAL,
        )
        super().__init__(spec)

    async def execute(self, request: AgentRequest) -> AgentResponse:
        return self.create_success_response(request, {"dummy": True})


def test_agent_registry_initialization():
    registry = AgentRegistry(register_defaults=True)
    agents = registry.list_agents()
    assert len(agents) >= 6

    names = [a.name for a in agents]
    assert "safety_context_agent" in names
    assert "acoustic_context_agent" in names
    assert "language_context_agent" in names
    assert "conversation_context_agent" in names
    assert "support_options_agent" in names
    assert "operator_briefing_agent" in names


def test_agent_registry_custom_worker():
    registry = AgentRegistry(register_defaults=False)
    assert len(registry.list_agents()) == 0

    worker = DummyWorker("custom_worker", ["special_feature"])
    registry.register(worker)

    assert registry.is_registered("custom_worker")
    assert registry.get("custom_worker") is worker
    assert "special_feature" in registry.all_capabilities()

    by_cap = registry.get_agents_by_capability("special_feature")
    assert len(by_cap) == 1
    assert by_cap[0].name == "custom_worker"

    unreg = registry.unregister("custom_worker")
    assert unreg is worker
    assert not registry.is_registered("custom_worker")
