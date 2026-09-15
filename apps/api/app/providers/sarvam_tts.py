import asyncio
import base64
import io
import logging
import struct
import time
import wave
from typing import Any, AsyncIterator, Dict, Optional
import httpx

from app.core.config import get_settings
from app.schemas.languages import LanguageCode

logger = logging.getLogger("samved.providers.sarvam_tts")

DEFAULT_VOICES: Dict[str, str] = {
    "ta-IN": "kavitha",
    "hi-IN": "shubh",
    "en-IN": "priya",
}

# In-memory greeting cache: maps text/language_code -> 8kHz mono PCM bytes
_GREETING_PCM_CACHE: Dict[str, bytes] = {}


def resample_pcm(pcm_data: bytes, in_rate: int, out_rate: int = 8000) -> bytes:
    """Resamples 16-bit mono PCM from in_rate to out_rate using linear interpolation."""
    if in_rate == out_rate or not pcm_data:
        return pcm_data

    n_samples = len(pcm_data) // 2
    if n_samples == 0:
        return b""

    samples = struct.unpack(f"<{n_samples}h", pcm_data)
    out_length = int(n_samples * out_rate / in_rate)
    resampled = bytearray(out_length * 2)

    step = in_rate / out_rate
    for i in range(out_length):
        pos = i * step
        idx = int(pos)
        frac = pos - idx
        if idx + 1 < n_samples:
            s = int(samples[idx] * (1.0 - frac) + samples[idx + 1] * frac)
        else:
            s = samples[idx]
        s = max(-32768, min(32767, s))
        struct.pack_into("<h", resampled, i * 2, s)

    return bytes(resampled)


def extract_pcm_from_wav(data: bytes, target_rate: int = 8000) -> bytes:
    """Extracts raw 16-bit mono PCM from WAV container, resampling to target_rate if needed."""
    if not data:
        return b""
    try:
        with wave.open(io.BytesIO(data), "rb") as w:
            in_rate = w.getframerate()
            pcm_frames = w.readframes(w.getnframes())
            if in_rate != target_rate:
                return resample_pcm(pcm_frames, in_rate=in_rate, out_rate=target_rate)
            return pcm_frames
    except Exception:
        # Fallback: strip standard 44-byte RIFF/WAVE header if present
        if len(data) > 44 and data[:4] == b"RIFF" and data[8:12] == b"WAVE":
            return data[44:]
        return data


def strip_wav_header_if_present(data: bytes) -> bytes:
    """Legacy helper maintained for backward compatibility."""
    return extract_pcm_from_wav(data, target_rate=8000)


class SarvamTTSProvider:
    """Production provider for Sarvam AI Bulbul Text-to-Speech synthesis."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "bulbul:v3",
        timeout_seconds: float = 15.0,
    ):
        settings = get_settings()
        self.api_key = api_key or settings.SARVAM_API_KEY
        self.model = model
        self.timeout_seconds = timeout_seconds
        self.endpoint = "https://api.sarvam.ai/text-to-speech"
        self._timeout_config = httpx.Timeout(
            timeout=self.timeout_seconds,
            connect=5.0,
            read=self.timeout_seconds,
            write=5.0,
        )

    @property
    def is_configured(self) -> bool:
        return bool(self.api_key and len(self.api_key.strip()) > 8)

    async def synthesize(
        self,
        text: str,
        language_code: str = "ta-IN",
        voice_id: Optional[str] = None,
    ) -> bytes:
        """Synthesizes text into 16-bit 8000Hz mono PCM audio bytes."""
        clean_text = text.strip()
        if not self.is_configured or not clean_text:
            logger.warning(f"Cannot synthesize TTS: configured={self.is_configured}, text_len={len(clean_text)}")
            return b""

        # Check in-memory greeting cache for instant delivery
        cache_key = f"{language_code}:{clean_text}"
        if cache_key in _GREETING_PCM_CACHE:
            logger.info(f"SARVAM_TTS_CACHE_HIT: text_len={len(clean_text)}, lang={language_code}")
            return _GREETING_PCM_CACHE[cache_key]

        # Normalize language and pick matching default speaker
        norm_lang = language_code if language_code and language_code != "unknown" else "ta-IN"
        if "ta" in norm_lang.lower():
            target_lang = "ta-IN"
            default_spk = "kavitha"
        elif "hi" in norm_lang.lower():
            target_lang = "hi-IN"
            default_spk = "shubh"
        elif "en" in norm_lang.lower():
            target_lang = "en-IN"
            default_spk = "priya"
        else:
            target_lang = norm_lang
            default_spk = DEFAULT_VOICES.get(target_lang, "kavitha")

        speaker = voice_id or default_spk

        payload = {
            "inputs": [clean_text],
            "target_language_code": target_lang,
            "speaker": speaker,
            "model": self.model,
            "audio_format": "wav",
            "sample_rate": 8000,
        }

        headers = {
            "api-subscription-key": self.api_key,
            "Content-Type": "application/json",
        }

        t_start = time.time()
        try:
            async with httpx.AsyncClient(timeout=self._timeout_config) as client:
                t_req_start = time.time()
                resp = await client.post(self.endpoint, json=payload, headers=headers)
                t_req_end = time.time()

                if resp.status_code == 200:
                    result = resp.json()
                    audios = result.get("audios", [])
                    if audios:
                        t_dec_start = time.time()
                        raw_bytes = base64.b64decode(audios[0])
                        pcm_bytes = extract_pcm_from_wav(raw_bytes, target_rate=8000)
                        t_dec_end = time.time()

                        http_ms = int((t_req_end - t_req_start) * 1000)
                        decode_ms = int((t_dec_end - t_dec_start) * 1000)
                        total_ms = int((t_dec_end - t_start) * 1000)

                        logger.info(
                            f"SARVAM_TTS_LATENCY: http_ms={http_ms}, decode_ms={decode_ms}, "
                            f"total_ms={total_ms}, pcm_bytes={len(pcm_bytes)}, lang={target_lang}"
                        )

                        # Cache deterministic greeting if applicable
                        if len(clean_text) < 200:
                            _GREETING_PCM_CACHE[cache_key] = pcm_bytes

                        return pcm_bytes
                    else:
                        logger.error(f"SARVAM_TTS_FAILED: empty audios array in response: {result}")
                else:
                    logger.error(f"SARVAM_TTS_FAILED: HTTP {resp.status_code} - {resp.text}")
        except httpx.TimeoutException:
            elapsed_ms = int((time.time() - t_start) * 1000)
            logger.warning(f"SARVAM_TTS_FAILED: request timed out after {elapsed_ms}ms (limit: {self.timeout_seconds}s)")
        except asyncio.CancelledError:
            logger.info("Sarvam TTS synthesis was cancelled (caller interruption).")
            raise
        except Exception as e:
            elapsed_ms = int((time.time() - t_start) * 1000)
            logger.error(f"SARVAM_TTS_FAILED: unexpected error after {elapsed_ms}ms: {e}")

        return b""

    async def synthesize_stream(
        self, text_iterator: AsyncIterator[str], language_code: str
    ) -> AsyncIterator[bytes]:
        """Streams synthesized chunks in 3200-byte slices matching Exotel requirements."""
        full_text = []
        async for chunk in text_iterator:
            full_text.append(chunk)

        combined = " ".join(full_text).strip()
        pcm = await self.synthesize(combined, language_code=language_code)

        # Slice into 3200-byte frames (100ms at 8kHz 16-bit mono)
        chunk_size = 3200
        for i in range(0, len(pcm), chunk_size):
            yield pcm[i : i + chunk_size]