import asyncio
import uuid
from typing import Any, AsyncIterator, Dict, List, Optional
from app.providers.base import (
    LLMProvider,
    SpeechToTextProvider,
    TelephonyProvider,
    TextToSpeechProvider,
)


class MockTelephonyProvider:
    """Deterministic mock telephony provider for testing and DEV mode."""

    def __init__(self, configured: bool = True):
        self.configured = configured
        self.active_calls: Dict[str, Dict[str, Any]] = {}

    async def initiate_call(self, to_number: str, from_number: str, metadata: Dict[str, Any]) -> str:
        call_id = f"mock-call-{uuid.uuid4().hex[:8]}"
        self.active_calls[call_id] = {
            "to": to_number,
            "from": from_number,
            "status": "connected",
            "metadata": metadata,
        }
        return call_id

    async def terminate_call(self, call_id: str, reason: str = "normal_hangup") -> bool:
        if call_id in self.active_calls:
            self.active_calls[call_id]["status"] = "terminated"
            self.active_calls[call_id]["reason"] = reason
            return True
        return False

    async def health_check(self) -> Dict[str, Any]:
        return {
            "provider": "MockTelephony",
            "status": "healthy" if self.configured else "unconfigured",
            "active_calls_count": len(self.active_calls),
        }


class MockSpeechToTextProvider:
    """Deterministic mock STT provider yielding predictable transcript chunks."""

    def __init__(self):
        self.sessions: Dict[str, List[bytes]] = {}

    async def start_stream(self, session_id: str, language_code: str) -> bool:
        self.sessions[session_id] = []
        return True

    async def send_audio_chunk(self, session_id: str, chunk_bytes: bytes) -> None:
        if session_id in self.sessions:
            self.sessions[session_id].append(chunk_bytes)

    async def receive_transcripts(self, session_id: str) -> AsyncIterator[Dict[str, Any]]:
        # Emit one partial then one final mock event
        yield {
            "speaker": "caller",
            "text": "Namaste, mujhe sahayata...",
            "confidence": 0.85,
            "is_final": False,
            "language": "hi-IN",
        }
        await asyncio.sleep(0.01)
        yield {
            "speaker": "caller",
            "text": "Namaste, mujhe sahayata chahiye.",
            "confidence": 0.96,
            "is_final": True,
            "language": "hi-IN",
        }

    async def close_stream(self, session_id: str) -> None:
        self.sessions.pop(session_id, None)


class MockTextToSpeechProvider:
    """Deterministic mock TTS provider returning synthetic PCM audio frames."""

    async def synthesize(self, text: str, language_code: str, voice_id: Optional[str] = None) -> bytes:
        # Generate dummy 100-byte PCM frame for deterministic testing
        return b"\x00\x01" * 50

    async def synthesize_stream(
        self, text_iterator: AsyncIterator[str], language_code: str
    ) -> AsyncIterator[bytes]:
        async for chunk in text_iterator:
            yield b"\x00\x02" * len(chunk.encode("utf-8"))


class MockLLMProvider:
    """Deterministic mock LLM provider returning structured responses without API calls."""

    async def generate_response(
        self,
        system_prompt: str,
        messages: List[Dict[str, str]],
        temperature: float = 0.2,
    ) -> str:
        last_message = messages[-1]["content"] if messages else ""
        return f"Mock response acknowledging: '{last_message[:30]}...'"

    async def generate_structured_output(
        self,
        system_prompt: str,
        messages: List[Dict[str, str]],
        schema_model: Any,
    ) -> Dict[str, Any]:
        return {
            "intent": "INQUIRY_DE_ADDICTION",
            "entities": {"location": "Jaipur", "substance": "alcohol"},
            "recommended_next_step": "CHECK_WITHDRAWAL_SEVERITY",
            "confidence": 0.92,
        }
