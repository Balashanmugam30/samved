import asyncio
import pytest
from app.realtime.session_manager import telephony_session_manager, create_session_orchestrator
from app.schemas.conversation import TranscriptEvent


@pytest.mark.asyncio
async def test_concurrent_call_safety_isolation():
    """
    Verify complete isolation between concurrent calls:
    Call A (Tamil active threat) -> HIGH/CRITICAL safety state
    Call B (English weapon threat) -> CRITICAL safety state
    Call C (Hindi benign inquiry) -> NONE safety state with zero signals
    No cross-session leakage of safety signals or state.
    """
    # 1. Create 3 concurrent sessions
    sess_a = await telephony_session_manager.create_session(
        session_id="sess-concur-a",
        call_id="call-concur-a",
        provider_call_id="call-a-sid",
        caller_number="+919876543211",
        provider="exotel",
        attach_ai=False,
    )
    sess_b = await telephony_session_manager.create_session(
        session_id="sess-concur-b",
        call_id="call-concur-b",
        provider_call_id="call-b-sid",
        caller_number="+919876543212",
        provider="exotel",
        attach_ai=False,
    )
    sess_c = await telephony_session_manager.create_session(
        session_id="sess-concur-c",
        call_id="call-concur-c",
        provider_call_id="call-c-sid",
        caller_number="+919876543213",
        provider="exotel",
        attach_ai=False,
    )

    # Attach orchestrators
    orch_a = create_session_orchestrator(sess_a)
    sess_a.orchestrator = orch_a
    orch_b = create_session_orchestrator(sess_b)
    sess_b.orchestrator = orch_b
    orch_c = create_session_orchestrator(sess_c)
    sess_c.orchestrator = orch_c

    # Start orchestrators
    await orch_a.start()
    await orch_b.start()
    await orch_c.start()

    # 2. Concurrently inject transcript events
    event_a = TranscriptEvent(
        session_id=sess_a.session_id,
        call_id=sess_a.call_id,
        text="தயவுசெய்து உதவுங்கள், அவர் என்னை அடிக்கிறார்!",
        language="ta-IN",
        confidence=0.95,
        is_final=True,
    )
    event_b = TranscriptEvent(
        session_id=sess_b.session_id,
        call_id=sess_b.call_id,
        text="He has a knife and is breaking the door right now!",
        language="en-IN",
        confidence=0.98,
        is_final=True,
    )
    event_c = TranscriptEvent(
        session_id=sess_c.session_id,
        call_id=sess_c.call_id,
        text="Namaste, helpline ka timing kya hai?",
        language="hi-IN",
        confidence=0.92,
        is_final=True,
    )

    await asyncio.gather(
        orch_a.handle_transcript_event(event_a),
        orch_b.handle_transcript_event(event_b),
        orch_c.handle_transcript_event(event_c),
    )

    # 3. Verify Call A: Tamil active threat
    assert orch_a.current_safety_state in ("HIGH", "CRITICAL")
    assert len(sess_a.active_safety_signals) > 0
    sig_a = sess_a.active_safety_signals[0]
    assert sig_a["call_id"] == sess_a.call_id
    assert sig_a["requires_human_review"] is True

    # 4. Verify Call B: English weapon threat
    assert orch_b.current_safety_state == "CRITICAL"
    assert len(sess_b.active_safety_signals) > 0
    assert any(s["severity"] == "CRITICAL" for s in sess_b.active_safety_signals)
    assert all(s["call_id"] == sess_b.call_id for s in sess_b.active_safety_signals)

    # 5. Verify Call C: Benign call remains completely untouched
    assert orch_c.current_safety_state == "NONE"
    assert len(sess_c.active_safety_signals) == 0

    # Verify event histories do NOT contain signals from other calls
    for ev in sess_c.event_history:
        assert ev.get("event_type") != "SAFETY_SIGNAL"

    # 6. Clean up
    await telephony_session_manager.end_session(sess_a.session_id)
    await telephony_session_manager.end_session(sess_b.session_id)
    await telephony_session_manager.end_session(sess_c.session_id)
