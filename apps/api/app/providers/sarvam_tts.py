import asyncio
import base64
import logging
from typing import Any, AsyncIterator, Dict, Optional
import httpx

from app.core.config import get_settings
from app.schemas.languages import LanguageCode

logger = logging.getLogger("samved.providers.sarvam_tts")

DEFAULT_VOICES: Dict[str, str] = {
    "ta-IN": "meera",
    "hi-IN": "shubh",
    "en-IN": "arvind",
}


def strip_wav_header_if_present(data: bytes) -> bytes:
    """If data begins with 'RIFF' header, strips the 44-byte WAV header to expose raw PCM."""
    if len(data) > 44 and data[:4] == b"RIFF" and data[8:12] == b"WAVE":
        return data[44:]
    return data


class SarvamTTSProvider:
    """Production provider for Sarvam AI Bulbul Text-to-Speech synthesis."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "bulbul:v3",
        timeout_seconds: float = 6.0,
    ):
        settings = get_settings()
        self.api_key = api_key or settings.SARVAM_API_KEY
        self.model = model
        self.timeout_seconds = timeout_seconds
        self.endpoint = "https://api.sarvam.ai/text-to-speech"

    @property
    def is_configured(self) -> bool:
        return bool(self.api_key and len(self.api_key.strip()) > 8)

    async def synthesize(
        self,
        text: str,
        language_code: str = "en-IN",
        voice_id: Optional[str] = None,
    ) -> bytes:
        """Synthesizes text into 16-bit 8000Hz mono PCM audio bytes."""
        if not self.is_configured or not text.strip():
            logger.warning(f"Cannot synthesize TTS: configured={self.is_configured}, text_len={len(text)}")
            return b""

        speaker = voice_id or DEFAULT_VOICES.get(language_code, "shubh")

        payload = {
            "inputs": [text.strip()],
            "target_language_code": language_code if language_code != "unknown" else "en-IN",
            "speaker": speaker,
            "model": self.model,
            "audio_format": "wav",
            "sample_rate": 8000,
        }

        headers = {
            "api-subscription-key": self.api_key,
            "Content-Type": "application/json",
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                resp = await client.post(self.endpoint, json=payload, headers=headers)
                if resp.status_code == 200:
                    result = resp.json()
                    audios = result.get("audios", [])
                    if audios:
                        b64_audio = audios[0]
                        raw_bytes = base64.b64decode(b64_audio)
                        pcm_bytes = strip_wav_header_if_present(raw_bytes)
                        return pcm_bytes
                else:
                    logger.error(f"Sarvam TTS returned status {resp.status_code}: {resp.text}")
        except httpx.TimeoutException:
            logger.warning("Sarvam TTS request timed out.")
        except asyncio.CancelledError:
            logger.info("Sarvam TTS synthesis was cancelled (caller interruption).")
            raise
        except Exception as e:
            logger.error(f"Error calling Sarvam TTS: {e}")

        return b""

    async def synthesize_stream(
        self, text_iterator: AsyncIterator[str], language_code: str
    ) -> AsyncIterator[bytes]:
        """Streams synthesized chunks in 320-byte (20ms) slices."""
        full_text = []
        async for chunk in text_iterator:
            full_text.append(chunk)

        combined = " ".join(full_text).strip()
        pcm = await self.synthesize(combined, language_code=language_code)

        # Slice into 320-byte (20ms) frames
        chunk_size = 320
        for i in range(0, len(pcm), chunk_size):
            yield pcm[i : i + chunk_size]