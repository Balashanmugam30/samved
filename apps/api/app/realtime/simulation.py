import asyncio
import logging
import uuid
from typing import Any, Dict, List

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
) -> Dict[str, Any]:
    """Executes a full end-to-end multi-turn simulated conversation through the exact orchestrator pipeline."""
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

    async def execute_turns():
        try:
            for turn_idx, turn in enumerate(scenario):
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
                await asyncio.sleep(turn.get("delay_after_ms", 500) / 1000.0)

            # Let last response finish playing
            await asyncio.sleep(0.3)
        finally:
            await telephony_session_manager.end_session(session_id, reason="conversation_simulation_ended")

    # Launch background runner
    asyncio.create_task(execute_turns())

    return {
        "status": "simulation_started",
        "scenario": scenario_key,
        "call_id": call_id,
        "session_id": session_id,
        "masked_caller": session.masked_caller_number,
        "turns_count": len(scenario),
    }