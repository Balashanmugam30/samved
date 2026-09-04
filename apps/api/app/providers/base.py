from typing import Any, AsyncIterator, Dict, List, Optional, Protocol, runtime_checkable


@runtime_checkable
class TelephonyProvider(Protocol):
    """Abstract interface for telephony providers (Exotel / Twilio / Mock)."""

    async def initiate_call(self, to_number: str, from_number: str, metadata: Dict[str, Any]) -> str:
        """Initiates an outbound leg or conference leg; returns external call ID."""
        ...

    async def terminate_call(self, call_id: str, reason: str = "normal_hangup") -> bool:
        """Terminates an active telephony session."""
        ...

    async def health_check(self) -> Dict[str, Any]:
        """Checks connectivity to telephony API / gateway."""
        ...


@runtime_checkable
class SpeechToTextProvider(Protocol):
    """Abstract interface for Speech-to-Text streaming engines (Sarvam / Mock)."""

    async def start_stream(self, session_id: str, language_code: str) -> bool:
        """Establishes a bidirectional streaming session with the STT engine."""
        ...

    async def send_audio_chunk(self, session_id: str, chunk_bytes: bytes) -> None:
        """Pushes raw PCM/μ-law audio frame to the active stream."""
        ...

    async def receive_transcripts(self, session_id: str) -> AsyncIterator[Dict[str, Any]]:
        """Yields partial and final transcript events."""
        ...

    async def close_stream(self, session_id: str) -> None:
        """Gracefully closes the active STT stream."""
        ...


@runtime_checkable
class TextToSpeechProvider(Protocol):
    """Abstract interface for Text-to-Speech synthesis engines (Sarvam / Mock)."""

    async def synthesize(self, text: str, language_code: str, voice_id: Optional[str] = None) -> bytes:
        """Synthesizes complete audio buffer for a given text snippet."""
        ...

    async def synthesize_stream(
        self, text_iterator: AsyncIterator[str], language_code: str
    ) -> AsyncIterator[bytes]:
        """Streams synthesized audio chunks for low-latency playback."""
        ...


@runtime_checkable
class LLMProvider(Protocol):
    """Abstract interface for LLM reasoning engines (Gemini / OpenAI / OpenRouter / Mock)."""

    async def generate_response(
        self,
        system_prompt: str,
        messages: List[Dict[str, str]],
        temperature: float = 0.2,
    ) -> str:
        """Generates conversational text response."""
        ...

    async def generate_structured_output(
        self,
        system_prompt: str,
        messages: List[Dict[str, str]],
        schema_model: Any,
    ) -> Dict[str, Any]:
        """Enforces structured JSON extraction conforming to schema_model."""
        ...
