"""Tests for CapabilityRouter in SAMVED Phase 9."""

import pytest
from app.orchestration.router import CapabilityRouter


def test_router_standard_triage_plan():
    router = CapabilityRouter()
    plan = router.plan_turn(task_type="turn_triage", safety_state="SAFE")

    assert len(plan.stage_1_workers) >= 4
    assert len(plan.stage_2_workers) == 1
    assert plan.stage_2_workers[0].name == "operator_briefing_agent"
    assert "support_options_agent" in [w.name for w in plan.stage_1_workers]
    assert plan.total_timeout_ms <= 250


def test_router_critical_safety_plan():
    router = CapabilityRouter()
    plan = router.plan_turn(task_type="turn_triage", safety_state="CRITICAL")

    # In critical mode, support options stub is omitted to prioritize safety and save latency
    worker_names = [w.name for w in plan.stage_1_workers]
    assert "safety_context_agent" in worker_names
    assert "operator_briefing_agent" in [w.name for w in plan.stage_2_workers]
    assert "support_options_agent" not in worker_names
    assert "High urgency" in plan.routing_reason


def test_router_explicit_agents():
    router = CapabilityRouter()
    plan = router.plan_turn(
        requested_agents=["safety_context_agent", "operator_briefing_agent"]
    )
    assert len(plan.stage_1_workers) == 1
    assert plan.stage_1_workers[0].name == "safety_context_agent"
    assert len(plan.stage_2_workers) == 1
    assert plan.stage_2_workers[0].name == "operator_briefing_agent"
