"""Concurrency tests for Phase 7 Adaptive Conversation Engine."""

import asyncio
import pytest
from app.adaptive.models import AdaptiveAction, AdaptivePlanRequest, AdaptivePriority
from app.adaptive.planner import AdaptivePlanner


@pytest.mark.asyncio
async def test_concurrent_adaptive_evaluations():
    """50 concurrent callers evaluate different scenarios simultaneously without crosstalk."""
    async def evaluate_single_session(index: int):
        # Even indices: Critical danger
        # Odd indices: High SVI distress
        is_even = index % 2 == 0
        req = AdaptivePlanRequest(
            call_id=f"concurrent-call-{index}",
            session_id=f"concurrent-sess-{index}",
            turn_index=index % 5 + 1,
            language="en-IN" if index % 3 == 0 else ("ta-IN" if index % 3 == 1 else "hi-IN"),
            safety_state="CRITICAL" if is_even else "NONE",
            safety_signals=[{"severity": "CRITICAL", "signal_type": "ACTIVE_VIOLENCE"}] if is_even else [],
            svi_score=80 if is_even else 65,
            svi_band="CRITICAL" if is_even else "HIGH",
            svi_trend="RISING",
            acoustic_quality="GOOD",
            acoustic_signals=[],
            known_facts={},
            last_caller_utterance="He is hitting me!" if is_even else "I feel so overwhelmed and scared.",
        )
        # Non-blocking executor to simulate async concurrent tasks
        strat = await asyncio.to_thread(AdaptivePlanner.evaluate_request, req)
        return index, strat

    tasks = [evaluate_single_session(i) for i in range(50)]
    results = await asyncio.gather(*tasks)

    assert len(results) == 50
    for idx, strat in results:
        assert strat.call_id == f"concurrent-call-{idx}"
        if idx % 2 == 0:
            assert strat.action in (AdaptiveAction.ASK_IMMEDIATE_DANGER, AdaptiveAction.SAFETY_CHECK)
            assert strat.priority == AdaptivePriority.P0
        else:
            assert strat.action == AdaptiveAction.ASK_SUPPORT
            assert strat.priority == AdaptivePriority.P2
