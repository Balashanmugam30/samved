import asyncio
import pytest
from app.providers.mocks import (
    MockLLMProvider,
    MockSpeechToTextProvider,
    MockTextToSpeechProvider,
)
from app.realtime.conversation_orchestrator import ConversationOrchestrator
from app.schemas.conversation import TranscriptEvent
from app.schemas.languages import LanguageCode


@pytest.mark.asyncio
async def test_concurrent_sessions_language_and_context_isolation():
    q_a = asyncio.Queue()
    q_b = asyncio.Queue()

    stt_a = MockSpeechToTextProvider()
    stt_a.set_scripted_turns("sess-multi-a", [])
    stt_b = MockSpeechToTextProvider()
    stt_b.set_scripted_turns("sess-multi-b", [])

    orch_a = ConversationOrchestrator(
        session_id="sess-multi-a",
        call_id="call-multi-a",
        stt_provider=stt_a,
        llm_provider=MockLLMProvider(),
        tts_provider=MockTextToSpeechProvider(),
        outbound_queue=q_a,
    )
    orch_b = ConversationOrchestrator(
        session_id="sess-multi-b",
        call_id="call-multi-b",
        stt_provider=stt_b,
        llm_provider=MockLLMProvider(),
        tts_provider=MockTextToSpeechProvider(),
        outbound_queue=q_b,
    )

    await orch_a.start()
    await orch_b.start()

    # Turn for session A (Tamil)
    event_a = TranscriptEvent(
        session_id="sess-multi-a",
        call_id="call-multi-a",
        speaker="caller",
        text="வணக்கம், எனக்கு உதவி வேண்டும்.",
        confidence=0.99,
        is_final=True,
        language="ta-IN",
    )

    # Turn for session B (Hindi)
    event_b = TranscriptEvent(
        session_id="sess-multi-b",
        call_id="call-multi-b",
        speaker="caller",
        text="नमस्ते, मुझे सहायता चाहिए।",
        confidence=0.99,
        is_final=True,
        language="hi-IN",
    )

    # Dispatch concurrently
    await asyncio.gather(
        orch_a.handle_transcript_event(event_a),
        orch_b.handle_transcript_event(event_b),
    )

    await asyncio.sleep(0.1)

    # Verify session A
    assert orch_a.current_language == LanguageCode.TA
    assert len(orch_a.utterances) == 2
    assert "வணக்கம்" in orch_a.utterances[0].text
    assert "வணக்கம்" in orch_a.utterances[1].text  # Mock AI responds in Tamil

    # Verify session B
    assert orch_b.current_language == LanguageCode.HI
    assert len(orch_b.utterances) == 2
    assert "नमस्ते" in orch_b.utterances[0].text
    assert "नमस्ते" in orch_b.utterances[1].text  # Mock AI responds in Hindi

    # Verify NO cross-contamination
    assert not any("नमस्ते" in u.text for u in orch_a.utterances)
    assert not any("வணக்கம்" in u.text for u in orch_b.utterances)

    await orch_a.stop()
    await orch_b.stop()