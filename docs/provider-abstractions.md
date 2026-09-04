# SAMVED — Provider Abstractions & Adapter Architecture

## 1. Architectural Motivation
Vendor lock-in is a critical risk for government-grade systems. SAMVED isolates all external telephony, speech, and AI provider mechanics behind strict Python Protocols and abstract interfaces.

### Core Benefits
1. **Replaceability**: The system can switch between Exotel and Twilio, Sarvam and alternative speech engines, or Google Gemini and OpenAI without altering core business rules or safety logic.
2. **Cost & Credit Conservation**: During local development and automated CI testing, deterministic mock providers simulate real audio streams without incurring API costs.
3. **Resilience & Fallback**: Runtime fallback mechanisms can route to secondary providers if a primary provider experiences downtime.

---

## 2. Core Provider Interfaces

### 1. `TelephonyProvider` (`app/providers/base.py`)
```python
class TelephonyProvider(Protocol):
    async def initiate_call(self, to_number: str, from_number: str, metadata: Dict[str, Any]) -> str: ...
    async def terminate_call(self, call_id: str, reason: str = "normal_hangup") -> bool: ...
    async def health_check(self) -> Dict[str, Any]: ...
```
- **Phase 0 Status**: `MockTelephonyProvider` implemented for testing.
- **Target LIVE Provider**: Exotel Voice Streaming API (Phase 1).
- **Secondary Provider**: Twilio Media Streams.

---

### 2. `SpeechToTextProvider` (`app/providers/base.py`)
```python
class SpeechToTextProvider(Protocol):
    async def start_stream(self, session_id: str, language_code: str) -> bool: ...
    async def send_audio_chunk(self, session_id: str, chunk_bytes: bytes) -> None: ...
    async def receive_transcripts(self, session_id: str) -> AsyncIterator[Dict[str, Any]]: ...
    async def close_stream(self, session_id: str) -> None: ...
```
- **Phase 0 Status**: `MockSpeechToTextProvider` yielding deterministic partial and final transcript events.
- **Target LIVE Provider**: Sarvam AI Indian-Language Streaming STT (Phase 2).

---

### 3. `TextToSpeechProvider` (`app/providers/base.py`)
```python
class TextToSpeechProvider(Protocol):
    async def synthesize(self, text: str, language_code: str, voice_id: Optional[str] = None) -> bytes: ...
    async def synthesize_stream(self, text_iterator: AsyncIterator[str], language_code: str) -> AsyncIterator[bytes]: ...
```
- **Phase 0 Status**: `MockTextToSpeechProvider` returning synthetic PCM frames.
- **Target LIVE Provider**: Sarvam AI Multilingual Bulbul TTS (Phase 2).

---

### 4. `LLMProvider` (`app/providers/base.py`)
```python
class LLMProvider(Protocol):
    async def generate_response(self, system_prompt: str, messages: List[Dict[str, str]], temperature: float = 0.2) -> str: ...
    async def generate_structured_output(self, system_prompt: str, messages: List[Dict[str, str]], schema_model: Any) -> Dict[str, Any]: ...
```
- **Phase 0 Status**: `MockLLMProvider` returning structured intent and entity payloads without external calls.
- **Target LIVE Provider**: Google Gemini 1.5/2.0 Pro & Flash via Vertex AI / Google AI Studio.
- **Alternative Providers**: OpenRouter, OpenAI GPT-4o.
