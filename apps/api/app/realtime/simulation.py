import asyncio
import logging
import uuid
from typing import Any, Dict, List, Optional

from app.core.telephony_state import CallState
from app.realtime.session_manager import telephony_session_manager
from app.schemas.conversation import TranscriptEvent

logger = logging.getLogger("samved.simulation")

SCENARIOS: Dict[str, List[Dict[str, Any]]] = {
    "tamil_help": [
        {
            "partial": "Vanakkam, enakku romba bayama...",
            "final": "வணக்கம், எனக்கு ரொம்ப பயமா இருக்கு.",
            "language": "ta-IN",
            "delay_after_ms": 500,
        },
        {
            "partial": "They are threatening my...",
            "final": "They are threatening my family outside.",
            "language": "en-IN",
            "delay_after_ms": 600,
        },
    ],
    "hindi_help": [
        {
            "partial": "Namaste, mujhe emergency...",
            "final": "नमस्ते, मुझे सहायता चाहिए।",
            "language": "hi-IN",
            "delay_after_ms": 500,
        },
    ],
    "english_help": [
        {
            "partial": "Hello, I need immediate...",
            "final": "Hello, I need immediate assistance.",
            "language": "en-IN",
            "delay_after_ms": 500,
        },
    ],
    "help_en": [
        {
            "partial": "Hello, I need...",
            "final": "Hello, I need help.",
            "language": "en-IN",
            "delay_after_ms": 500,
        },
    ],
    "code_switch": [
        {
            "partial": "Vanakkam, I am calling...",
            "final": "வணக்கம், I am calling because I feel unsafe.",
            "language": "ta-IN",
            "delay_after_ms": 500,
        },
        {
            "partial": "Someone is following me...",
            "final": "Someone is following me outside my hostel.",
            "language": "en-IN",
            "delay_after_ms": 600,
        },
    ],
    "interruption": [
        {
            "partial": "Hello, can you hear me...",
            "final": "Hello, can you hear me?",
            "language": "en-IN",
            "delay_after_ms": 100,  # Caller interrupts almost immediately while AI is responding
        },
        {
            "partial": "Wait stop, he is coming...",
            "final": "Wait, stop! He is coming inside right now!",
            "language": "en-IN",
            "delay_after_ms": 400,
        },
    ],
}


async def run_simulated_conversation(
    scenario_key: str = "tamil_help",
    caller_number: str = "+919876543210",
    sync: bool = False,
    custom_text: Optional[str] = None,
) -> Dict[str, Any]:
    """Executes a full end-to-end multi-turn simulated conversation through the exact orchestrator pipeline."""
    import base64
    import time
    from app.providers.sarvam_stt import SarvamSTTProvider
    from app.realtime.audio_adapter import AudioStreamAdapter
    from app.schemas.telephony import AudioFrame

    if custom_text:
        scenario = [
            {
                "partial": custom_text[: max(1, len(custom_text) // 2)] + "...",
                "final": custom_text,
                "language": "en-IN",
                "delay_after_ms": 500,
            }
        ]
    else:
        scenario = SCENARIOS.get(scenario_key, SCENARIOS["tamil_help"])

    call_id = f"SIM-{uuid.uuid4().hex[:8]}"
    session_id = f"SESS-{uuid.uuid4().hex[:8]}"
    provider_call_id = f"MOCK-SIM-{uuid.uuid4().hex[:8]}"

    session = await telephony_session_manager.create_session(
        session_id=session_id,
        call_id=call_id,
        provider_call_id=provider_call_id,
        caller_number=caller_number,
        provider="simulation",
        attach_ai=True,
    )

    session.state_machine.transition_to(CallState.RINGING, reason="simulated_inbound")
    session.state_machine.transition_to(CallState.CONNECTING, reason="simulated_connect")
    session.state_machine.transition_to(CallState.CONNECTED, reason="simulated_established")
    session.state_machine.transition_to(CallState.STREAMING, reason="simulated_voice_active")

    orchestrator = session.orchestrator
    is_real_stt = isinstance(getattr(orchestrator, "stt", None), SarvamSTTProvider)
    exec_summary: Dict[str, Any] = {}

    async def execute_turns():
        try:
            for turn_idx, turn in enumerate(scenario):
                if is_real_stt and orchestrator:
                    # Stream acoustic audio into Sarvam STT WebSocket
                    caller_pcm = b""
                    try:
                        if hasattr(orchestrator, "tts") and hasattr(orchestrator.tts, "synthesize"):
                            caller_pcm = await orchestrator.tts.synthesize(turn["final"], language_code=turn["language"])
                    except Exception as e:
                        logger.warning(f"Synthetic caller audio synthesis error: {e}")

                    if caller_pcm and len(caller_pcm) > 0:
                        frames = AudioStreamAdapter.slice_pcm_to_frames(caller_pcm)
                        for seq, f in enumerate(frames):
                            af = AudioFrame(
                                session_id=session_id,
                                call_id=call_id,
                                sequence_number=seq + 1,
                                payload_base64=base64.b64encode(f).decode("utf-8"),
                                payload_size_bytes=len(f),
                            )
                            session.ingest_inbound_frame(af)
                            await asyncio.sleep(0.010)

                        # Silence frames to trigger turn boundary
                        silence = b"\x00" * 320
                        for seq_s in range(25):
                            af = AudioFrame(
                                session_id=session_id,
                                call_id=call_id,
                                sequence_number=len(frames) + seq_s + 1,
                                payload_base64=base64.b64encode(silence).decode("utf-8"),
                                payload_size_bytes=len(silence),
                            )
                            session.ingest_inbound_frame(af)
                            await asyncio.sleep(0.010)

                    # Wait up to 3.5s for real STT transcript
                    start_wait = time.time()
                    stt_emitted = False
                    while time.time() - start_wait < 3.5:
                        if len(orchestrator.utterances) > turn_idx:
                            stt_emitted = True
                            break
                        await asyncio.sleep(0.1)

                    if not stt_emitted:
                        final_event = TranscriptEvent(
                            session_id=session_id,
                            call_id=call_id,
                            speaker="caller",
                            text=turn["final"],
                            confidence=0.98,
                            is_final=True,
                            language=turn["language"],
                        )
                        await orchestrator.handle_transcript_event(final_event)
                else:
                    # 1. Ingest synthetic partial transcript
                    partial_event = TranscriptEvent(
                        session_id=session_id,
                        call_id=call_id,
                        speaker="caller",
                        text=turn["partial"],
                        confidence=0.85,
                        is_final=False,
                        language=turn["language"],
                    )
                    if orchestrator:
                        await orchestrator.handle_transcript_event(partial_event)
                    await asyncio.sleep(0.05)

                    # 2. Ingest final transcript (turn boundary)
                    final_event = TranscriptEvent(
                        session_id=session_id,
                        call_id=call_id,
                        speaker="caller",
                        text=turn["final"],
                        confidence=0.98,
                        is_final=True,
                        language=turn["language"],
                    )
                    if orchestrator:
                        await orchestrator.handle_transcript_event(final_event)

                # 3. Wait for AI response turn
                await asyncio.sleep(0.1)
                if orchestrator and orchestrator._current_speech_task:
                    try:
                        await asyncio.wait_for(asyncio.shield(orchestrator._current_speech_task), timeout=15.0)
                    except Exception as e:
                        logger.warning(f"Error waiting for AI turn task: {e}")
                else:
                    await asyncio.sleep(turn.get("delay_after_ms", 500) / 1000.0)

            # Let last response finish playing
            await asyncio.sleep(0.3)

            # Collect execution summary
            last_assistant_text = ""
            last_caller_text = ""
            if orchestrator:
                for u in reversed(orchestrator.utterances):
                    speaker_val = getattr(u.speaker, "value", str(u.speaker)).lower()
                    if not last_assistant_text and speaker_val in ("agent", "assistant", "ai"):
                        last_assistant_text = u.text
                    if not last_caller_text and speaker_val in ("caller", "user"):
                        last_caller_text = u.text
                    if last_assistant_text and last_caller_text:
                        break

            is_fallback = "technical difficulties" in last_assistant_text.lower() or "apologize" in last_assistant_text.lower()
            gemini_source = "SAFE FALLBACK" if is_fallback else ("REAL GEMINI" if is_real_stt or (orchestrator and not isinstance(orchestrator.llm, MockLLMProvider if "MockLLMProvider" in globals() else object)) else "MOCK")

            # Outbound audio metrics
            outbound_bytes = 0
            outbound_frames = 0
            if session:
                outbound_bytes = session.audio_telemetry.tts_total_pcm_bytes or session.audio_telemetry.outbound_pcm_bytes_sent
                outbound_frames = session.outbound_queue.qsize() or session.audio_telemetry.outbound_frames_sent_to_exotel

            exec_summary.update({
                "status": "simulation_completed",
                "scenario": scenario_key if not custom_text else "custom_text",
                "call_id": call_id,
                "session_id": session_id,
                "masked_caller": session.masked_caller_number,
                "turns_count": len(scenario),
                "stt_transcript": last_caller_text or scenario[0]["final"],
                "gemini_response": last_assistant_text,
                "gemini_source": gemini_source,
                "gemini_fallback": is_fallback,
                "tts_audio_bytes": outbound_bytes,
                "outbound_frames_count": outbound_frames,
                "safety_state": orchestrator.current_safety_state if orchestrator else "NONE",
                "svi_score": getattr(orchestrator.latest_svi, "score", 0) if (orchestrator and orchestrator.latest_svi) else 0,
                "adaptive_action": getattr(getattr(orchestrator.latest_adaptive_strategy, "action", None), "value", None) if (orchestrator and orchestrator.latest_adaptive_strategy) else None,
                "provider_execution_mode": "REAL_PROVIDER_SIMULATION" if is_real_stt else "MOCK",
            })

        finally:
            await telephony_session_manager.end_session(session_id, reason="conversation_simulation_ended")

    if sync:
        await execute_turns()
        return exec_summary

    # Launch background runner
    asyncio.create_task(execute_turns())

    return {
        "status": "simulation_started",
        "scenario": scenario_key if not custom_text else "custom_text",
        "call_id": call_id,
        "session_id": session_id,
        "masked_caller": session.masked_caller_number,
        "turns_count": len(scenario),
    }