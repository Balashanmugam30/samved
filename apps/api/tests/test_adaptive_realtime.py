"""Integration tests for Adaptive Conversation in Realtime ConversationOrchestrator."""

import asyncio
import pytest
from app.providers.mocks import (
    MockLLMProvider,
    MockSpeechToTextProvider,
    MockTextToSpeechProvider,
)
from app.realtime.conversation_orchestrator import ConversationOrchestrator
from app.schemas.conversation import TranscriptEvent


@pytest.mark.asyncio
async def test_adaptive_realtime_turn_orchestration():
    """Verifies that final STT transcript triggers Adaptive Planning and emits ADAPTIVE_STRATEGY_SELECTED."""
    session_id = "realtime-sess-ad-1"
    call_id = "realtime-call-ad-1"
    events_broadcast = []

    def broadcast_collector(event_type: str, payload: dict):
        events_broadcast.append((event_type, payload))

    stt = MockSpeechToTextProvider()
    tts = MockTextToSpeechProvider()
    llm = MockLLMProvider()

    orchestrator = ConversationOrchestrator(
        session_id=session_id,
        call_id=call_id,
        stt_provider=stt,
        llm_provider=llm,
        tts_provider=tts,
        outbound_queue=asyncio.Queue(),
        event_broadcaster=broadcast_collector,
    )
    orchestrator._is_running = True

    # Send a final transcript event
    event = TranscriptEvent(
        session_id=session_id,
        call_id=call_id,
        speaker="caller",
        text="He is hitting me right now with a knife!",
        confidence=0.98,
        is_final=True,
        language="en-IN",
    )

    await orchestrator.handle_transcript_event(event)

    # Wait briefly for background execution
    await asyncio.sleep(0.05)

    # Verify that ADAPTIVE_STRATEGY_SELECTED was broadcast
    adaptive_events = [e for e in events_broadcast if e[0] == "ADAPTIVE_STRATEGY_SELECTED"]
    assert len(adaptive_events) >= 1

    strat_payload = adaptive_events[0][1]
    assert strat_payload["call_id"] == call_id
    assert strat_payload["action"] in ("SAFETY_CHECK", "ASK_IMMEDIATE_DANGER")
    assert strat_payload["priority"] in ("P0", "P1")
    assert "CRITICAL_SAFETY_PRIORITY" in strat_payload["reason_codes"] or "SAFETY_UNKNOWN" in strat_payload["reason_codes"]

    # Verify latest strategy on orchestrator
    assert orchestrator.latest_adaptive_strategy is not None
