import asyncio
import json
import logging
from typing import Any, AsyncIterator, Dict, Optional
import websockets
from websockets.exceptions import ConnectionClosed

from app.core.config import get_settings
from app.schemas.conversation import TranscriptEvent
from app.schemas.languages import LanguageCode

logger = logging.getLogger("samved.providers.sarvam_stt")


class SarvamSTTProvider:
    """Production provider for Sarvam AI Realtime Streaming Speech-to-Text via WebSockets."""

    def __init__(self, api_key: Optional[str] = None):
        settings = get_settings()
        self.api_key = api_key or settings.SARVAM_API_KEY
        self.ws_url = "wss://api.sarvam.ai/speech-to-text-realtime/ws"
        self._active_connections: Dict[str, websockets.WebSocketClientProtocol] = {}
        self._event_queues: Dict[str, asyncio.Queue[TranscriptEvent]] = {}
        self._listen_tasks: Dict[str, asyncio.Task] = {}

    @property
    def is_configured(self) -> bool:
        return bool(self.api_key and len(self.api_key.strip()) > 8)

    async def start_stream(self, session_id: str, language_code: str = "unknown") -> bool:
        """Establishes bidirectional streaming WebSocket with Sarvam STT engine."""
        if not self.is_configured:
            logger.warning(f"Cannot start Sarvam STT stream for {session_id}: missing SARVAM_API_KEY")
            return False

        headers = {
            "api-subscription-key": self.api_key,
        }

        try:
            ws = await websockets.connect(
                self.ws_url,
                additional_headers=headers,
                ping_interval=20,
                ping_timeout=10,
            )
            self._active_connections[session_id] = ws
            self._event_queues[session_id] = asyncio.Queue()

            # Send initial configuration frame
            config_msg = {
                "model": "saaras:v3",
                "language_code": language_code if language_code != "unknown" else "unknown",
                "mode": "transcribe",
                "sample_rate": 8000,
                "encoding": "pcm_s16le",
            }
            await ws.send(json.dumps(config_msg))
            logger.info(f"Connected to Sarvam STT WebSocket for session {session_id} (lang: {language_code})")

            # Launch background listener task
            task = asyncio.create_task(self._listen_loop(session_id, ws))
            self._listen_tasks[session_id] = task
            return True

        except Exception as e:
            logger.error(f"Failed to connect to Sarvam STT for session {session_id}: {e}")
            return False

    async def _listen_loop(self, session_id: str, ws: websockets.WebSocketClientProtocol):
        q = self._event_queues.get(session_id)
        if not q:
            return

        try:
            async for raw_msg in ws:
                try:
                    data = json.loads(raw_msg)
                except json.JSONDecodeError:
                    continue

                text = data.get("transcript") or data.get("text") or ""
                if not text.strip():
                    continue

                is_final = bool(data.get("is_final", False))
                lang = data.get("language_code") or "unknown"
                confidence = float(data.get("confidence", 0.9))

                event = TranscriptEvent(
                    session_id=session_id,
                    call_id=session_id,
                    speaker="caller",
                    text=text.strip(),
                    confidence=confidence,
                    is_final=is_final,
                    language=lang,
                )
                await q.put(event)

        except (ConnectionClosed, asyncio.CancelledError):
            pass
        except Exception as e:
            logger.error(f"Error in Sarvam STT listener for {session_id}: {e}")

    async def send_audio_chunk(self, session_id: str, chunk_bytes: bytes) -> None:
        """Sends raw 16-bit 8000Hz PCM chunk to Sarvam STT WebSocket."""
        ws = self._active_connections.get(session_id)
        if ws and not ws.closed:
            try:
                await ws.send(chunk_bytes)
            except Exception as e:
                logger.error(f"Failed to send audio chunk to Sarvam STT {session_id}: {e}")

    async def receive_transcripts(self, session_id: str) -> AsyncIterator[TranscriptEvent]:
        """Yields transcript events as they are received from Sarvam STT."""
        q = self._event_queues.get(session_id)
        if not q:
            return

        while True:
            try:
                event = await q.get()
                yield event
                q.task_done()
            except asyncio.CancelledError:
                break

    async def close_stream(self, session_id: str) -> None:
        """Closes Sarvam STT session and frees resources."""
        task = self._listen_tasks.pop(session_id, None)
        if task and not task.done():
            task.cancel()

        ws = self._active_connections.pop(session_id, None)
        if ws:
            try:
                await ws.close()
            except Exception:
                pass

        self._event_queues.pop(session_id, None)
        logger.info(f"Closed Sarvam STT stream for session {session_id}")