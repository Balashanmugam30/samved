"""Realtime integration tests for Multi-Agent Orchestration with ConversationOrchestrator."""

import asyncio
import pytest
from app.schemas.languages import LanguageCode
from app.realtime.conversation_orchestrator import ConversationOrchestrator, TranscriptEvent


class MockSTT:
    async def send_audio_chunk(self, session_id: str, pcm: bytes):
        pass


class MockLLM:
    async def generate_response(self, *args, **kwargs):
        from app.schemas.telephony import ConversationalResponse
        return ConversationalResponse(
            text="Naan ungalukku udhavi seikiren.",
            language=LanguageCode.TA,
            latency_ms=10.0,
        )


class MockTTS:
    async def synthesize(self, *args, **kwargs):
        async def dummy_gen():
            yield b"\x00" * 320
        return dummy_gen()


@pytest.mark.asyncio
async def test_realtime_turn_orchestrates_agents():
    outbound_queue = asyncio.Queue()
    events = []

    def broadcaster(event_type: str, payload: dict):
        events.append((event_type, payload))

    orch = ConversationOrchestrator(
        session_id="sess-realtime-test",
        call_id="call-realtime-test",
        stt_provider=MockSTT(),
        llm_provider=MockLLM(),
        tts_provider=MockTTS(),
        outbound_queue=outbound_queue,
        event_broadcaster=broadcaster,
    )

    # Send final transcript event to trigger full turn
    event = TranscriptEvent(
        session_id="sess-realtime-test",
        call_id="call-realtime-test",
        text="Aabathu irukku, kapathunga please",
        is_final=True,
        language="ta-IN",
        confidence=0.95,
    )

    await orch.handle_transcript_event(event)

    # Verify orchestration was executed
    assert orch.latest_orchestration is not None
    assert len(orch.orchestration_results) == 1
    assert orch.latest_orchestration.call_id == "call-realtime-test"

    # Verify orchestration events broadcasted
    event_names = [e[0] for e in events]
    assert "ORCHESTRATION_STARTED" in event_names
    assert "ORCHESTRATION_COMPLETED" in event_names or "ORCHESTRATION_DEGRADED" in event_names
    assert "OPERATOR_BRIEFING_GENERATED" in event_names
