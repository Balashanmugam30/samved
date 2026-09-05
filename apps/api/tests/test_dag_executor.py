"""Tests for DAGExecutor in SAMVED Phase 9."""

import asyncio
import pytest
from app.orchestration.contracts import BaseAgentWorker
from app.orchestration.executor import DAGExecutor
from app.orchestration.models import (
    AgentRequest,
    AgentResponse,
    AgentSafetyClassification,
    AgentSpec,
    AgentStatus,
    AgentTimeoutTier,
    AgentType,
)


class SlowWorker(BaseAgentWorker):
    def __init__(self, delay: float = 0.5):
        spec = AgentSpec(
            name="slow_worker",
            version="1.0.0",
            agent_type=AgentType.RULE_WORKER,
            timeout_tier=AgentTimeoutTier.REALTIME_CRITICAL,
            max_latency_ms=50,  # 50ms deadline
            safety_classification=AgentSafetyClassification.OPERATIONAL,
        )
        super().__init__(spec)
        self.delay = delay

    async def execute(self, request: AgentRequest) -> AgentResponse:
        await asyncio.sleep(self.delay)
        return self.create_success_response(request, {"done": True})


class FailingWorker(BaseAgentWorker):
    def __init__(self):
        spec = AgentSpec(
            name="failing_worker",
            version="1.0.0",
            agent_type=AgentType.RULE_WORKER,
            timeout_tier=AgentTimeoutTier.REALTIME_NORMAL,
            max_latency_ms=100,
            safety_classification=AgentSafetyClassification.NON_CRITICAL,
        )
        super().__init__(spec)

    async def execute(self, request: AgentRequest) -> AgentResponse:
        raise ValueError("Simulated worker failure")


@pytest.mark.asyncio
async def test_executor_timeout_handling():
    executor = DAGExecutor()
    worker = SlowWorker(delay=0.2)  # Exceeds 50ms deadline
    req = AgentRequest(call_id="c1", turn_id="t1", task_type="test")

    resp = await executor.execute_worker(worker, req)
    assert resp.status == AgentStatus.TIMED_OUT
    assert "timed out" in resp.warnings[0].lower() or "exceeded deadline" in resp.warnings[0].lower()


@pytest.mark.asyncio
async def test_executor_cancellation():
    executor = DAGExecutor()
    worker = SlowWorker(delay=0.2)
    req = AgentRequest(call_id="c1", turn_id="t1", task_type="test")

    cancel_event = asyncio.Event()
    cancel_event.set()  # Pre-cancelled

    resp = await executor.execute_worker(worker, req, cancel_event=cancel_event)
    assert resp.status == AgentStatus.CANCELLED


@pytest.mark.asyncio
async def test_executor_failure_resilience():
    executor = DAGExecutor()
    worker = FailingWorker()
    req = AgentRequest(call_id="c1", turn_id="t1", task_type="test")

    resp = await executor.execute_worker(worker, req)
    assert resp.status == AgentStatus.FAILED
    assert "Simulated worker failure" in resp.warnings[0]
