import asyncio
import pytest
from app.providers.mocks import (
    MockLLMProvider,
    MockSpeechToTextProvider,
    MockTextToSpeechProvider,
)
from app.realtime.conversation_orchestrator import ConversationOrchestrator
from app.schemas.conversation import ConversationState, TranscriptEvent, TurnSpeaker
from app.schemas.languages import LanguageCode


@pytest.mark.asyncio
async def test_conversation_orchestrator_turn_flow():
    outbound_q = asyncio.Queue()
    broadcasted_events = []

    def mock_broadcast(ev_type: str, payload: dict):
        broadcasted_events.append((ev_type, payload))

    stt_mock = MockSpeechToTextProvider()
    stt_mock.set_scripted_turns("sess-orch-01", [])

    orchestrator = ConversationOrchestrator(
        session_id="sess-orch-01",
        call_id="call-orch-01",
        stt_provider=stt_mock,
        llm_provider=MockLLMProvider(),
        tts_provider=MockTextToSpeechProvider(),
        outbound_queue=outbound_q,
        event_broadcaster=mock_broadcast,
    )

    await orchestrator.start()
    assert orchestrator.state == ConversationState.LISTENING

    # 1. Simulate caller partial transcript
    partial = TranscriptEvent(
        session_id="sess-orch-01",
        call_id="call-orch-01",
        speaker="caller",
        text="Vanakkam, enakku bayama...",
        confidence=0.88,
        is_final=False,
        language="ta-IN",
    )
    await orchestrator.handle_transcript_event(partial)
    assert orchestrator.state == ConversationState.TRANSCRIBING
    assert orchestrator.current_language == LanguageCode.TA

    # 2. Simulate final transcript
    final = TranscriptEvent(
        session_id="sess-orch-01",
        call_id="call-orch-01",
        speaker="caller",
        text="Vanakkam, enakku romba bayama irukku.",
        confidence=0.97,
        is_final=True,
        language="ta-IN",
    )
    await orchestrator.handle_transcript_event(final)

    # Wait briefly for background AI turn to finish
    await asyncio.sleep(0.1)

    # Verify state returned to LISTENING
    assert orchestrator.state == ConversationState.LISTENING
    assert len(orchestrator.utterances) == 2
    assert orchestrator.utterances[0].speaker == TurnSpeaker.CALLER
    assert orchestrator.utterances[1].speaker == TurnSpeaker.AGENT

    # Verify audio frames were queued into outbound_queue
    assert not outbound_q.empty()
    frame = await outbound_q.get()
    assert len(frame) == 320  # 20ms 8kHz frame

    # Verify event types broadcasted
    event_names = [e[0] for e in broadcasted_events]
    assert "CONVERSATION_STATE_CHANGED" in event_names
    assert "TRANSCRIPT_PARTIAL" in event_names
    assert "TRANSCRIPT_FINAL" in event_names
    assert "AI_THINKING" in event_names
    assert "AI_RESPONSE_STARTED" in event_names
    assert "TTS_STARTED" in event_names
    assert "TTS_ENDED" in event_names
    assert "AI_RESPONSE_ENDED" in event_names

    await orchestrator.stop()
    assert orchestrator.state == ConversationState.ENDING