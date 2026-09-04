import asyncio
import logging
from collections import deque
from datetime import datetime, timezone
from typing import Any, Deque, Dict, List, Optional, Set
from fastapi import WebSocket

from app.core.telephony_state import CallState, CallStateMachine
from app.schemas.telephony import (
    AudioDirection,
    AudioFormat,
    AudioFrame,
    TelephonySessionInfo,
)

logger = logging.getLogger("samved.telephony.session")


def mask_phone_number(raw_number: str) -> str:
    """Masks phone number for caller privacy: e.g. +919876543210 -> +91******3210."""
    if not raw_number:
        return "ANONYMOUS"
    clean = raw_number.strip()
    if len(clean) <= 6:
        return "****"
    prefix = clean[:3]
    suffix = clean[-4:]
    return f"{prefix}******{suffix}"


class TelephonySession:
    """Encapsulates a single active telephone call and realtime streaming session."""

    def __init__(
        self,
        session_id: str,
        call_id: str,
        provider_call_id: str,
        caller_number: str,
        provider: str = "exotel",
        max_buffer_frames: int = 500,  # ~10s of 20ms frames
    ):
        self.session_id = session_id
        self.call_id = call_id
        self.provider_call_id = provider_call_id
        self.raw_caller_number = caller_number  # Isolated internally
        self.masked_caller_number = mask_phone_number(caller_number)
        self.provider = provider
        self.state_machine = CallStateMachine(call_id=call_id)
        self.audio_format = AudioFormat()

        self.websocket: Optional[WebSocket] = None
        self.connected_at: Optional[str] = None
        self.last_activity_at: str = datetime.now(timezone.utc).isoformat()

        # Bounded frame buffers (Separate per session)
        self.inbound_buffer: Deque[AudioFrame] = deque(maxlen=max_buffer_frames)
        self.outbound_queue: asyncio.Queue[bytes] = asyncio.Queue()

        # Metrics and sequence validation
        self.last_sequence_number: int = 0
        self.inbound_frames_count: int = 0
        self.inbound_bytes_count: int = 0
        self.sequence_gaps_count: int = 0
        self.dropped_frames_count: int = 0

        # Subscribed callbacks for downstream consumers (e.g. Phase 2 STT)
        self.frame_consumers: Set[Any] = set()

    def touch(self) -> None:
        self.last_activity_at = datetime.now(timezone.utc).isoformat()

    def ingest_inbound_frame(self, frame: AudioFrame) -> None:
        self.touch()

        # Sequence gap detection
        if self.inbound_frames_count > 0:
            expected_seq = self.last_sequence_number + 1
            if frame.sequence_number > expected_seq:
                gap = frame.sequence_number - expected_seq
                self.sequence_gaps_count += gap
                logger.warning(
                    f"Sequence gap detected for session {self.session_id}: expected {expected_seq}, "
                    f"got {frame.sequence_number} (gap: {gap})"
                )
            elif frame.sequence_number < expected_seq:
                logger.warning(
                    f"Out-of-order or duplicate frame {frame.sequence_number} in session {self.session_id}"
                )

        self.last_sequence_number = frame.sequence_number
        self.inbound_frames_count += 1
        self.inbound_bytes_count += frame.payload_size_bytes

        if len(self.inbound_buffer) == self.inbound_buffer.maxlen:
            self.dropped_frames_count += 1

        self.inbound_buffer.append(frame)

        # Broadcast frame to attached consumers (Phase 2 STT hook)
        for consumer in list(self.frame_consumers):
            try:
                consumer(frame)
            except Exception as e:
                logger.error(f"Error in frame consumer for session {self.session_id}: {e}")

    def enqueue_outbound_audio(self, pcm_bytes: bytes) -> None:
        """Queues synthesized audio to stream back to Exotel telephony leg."""
        self.touch()
        self.outbound_queue.put_nowait(pcm_bytes)

    def to_info(self) -> TelephonySessionInfo:
        return TelephonySessionInfo(
            session_id=self.session_id,
            call_id=self.call_id,
            provider_call_id=self.provider_call_id,
            provider=self.provider,
            caller_masked_number=self.masked_caller_number,
            state=self.state_machine.current_state.value,
            connected_at=self.connected_at,
            last_activity_at=self.last_activity_at,
            audio_format=self.audio_format,
            inbound_frames_count=self.inbound_frames_count,
            inbound_bytes_count=self.inbound_bytes_count,
            sequence_gaps_count=self.sequence_gaps_count,
            dropped_frames_count=self.dropped_frames_count,
            is_active=self.state_machine.is_active,
        )


class RealtimeSessionManager:
    """Concurrency-safe global manager for active telephony calls and sessions."""

    def __init__(self):
        self._sessions: Dict[str, TelephonySession] = {}
        self._provider_call_id_map: Dict[str, str] = {}  # provider_call_id -> session_id
        self._call_id_map: Dict[str, str] = {}           # call_id -> session_id
        self._lock = asyncio.Lock()

    async def create_session(
        self,
        session_id: str,
        call_id: str,
        provider_call_id: str,
        caller_number: str,
        provider: str = "exotel",
    ) -> TelephonySession:
        async with self._lock:
            # Idempotency check: if session already exists for this provider_call_id, return it
            if provider_call_id in self._provider_call_id_map:
                existing_sid = self._provider_call_id_map[provider_call_id]
                logger.info(
                    f"Idempotent session retrieval for provider call {provider_call_id}: {existing_sid}"
                )
                return self._sessions[existing_sid]

            session = TelephonySession(
                session_id=session_id,
                call_id=call_id,
                provider_call_id=provider_call_id,
                caller_number=caller_number,
                provider=provider,
            )
            self._sessions[session_id] = session
            self._provider_call_id_map[provider_call_id] = session_id
            self._call_id_map[call_id] = session_id

            logger.info(
                f"Created telephony session {session_id} for call {call_id} (Provider SID: {provider_call_id})"
            )
            return session

    async def get_session(self, session_id: str) -> Optional[TelephonySession]:
        return self._sessions.get(session_id)

    async def get_by_provider_call_id(self, provider_call_id: str) -> Optional[TelephonySession]:
        sid = self._provider_call_id_map.get(provider_call_id)
        return self._sessions.get(sid) if sid else None

    async def get_by_call_id(self, call_id: str) -> Optional[TelephonySession]:
        sid = self._call_id_map.get(call_id)
        return self._sessions.get(sid) if sid else None

    async def attach_websocket(self, session_id: str, websocket: WebSocket) -> Optional[TelephonySession]:
        session = await self.get_session(session_id)
        if session:
            session.websocket = websocket
            session.connected_at = datetime.now(timezone.utc).isoformat()
            session.touch()
            if session.state_machine.can_transition_to(CallState.CONNECTED):
                session.state_machine.transition_to(CallState.CONNECTED, reason="websocket_connected")
        return session

    async def end_session(self, session_id: str, reason: str = "normal_hangup") -> Optional[TelephonySession]:
        async with self._lock:
            session = self._sessions.get(session_id)
            if not session:
                return None

            if session.state_machine.can_transition_to(CallState.ENDED):
                session.state_machine.transition_to(CallState.ENDED, reason=reason)
            elif session.state_machine.can_transition_to(CallState.FAILED):
                session.state_machine.transition_to(CallState.FAILED, reason=reason)

            # Close WebSocket if still open
            if session.websocket:
                try:
                    await session.websocket.close()
                except Exception:
                    pass
                session.websocket = None

            # Clear buffers
            session.inbound_buffer.clear()

            # Remove from lookup maps to prevent memory leakage
            self._provider_call_id_map.pop(session.provider_call_id, None)
            self._call_id_map.pop(session.call_id, None)
            self._sessions.pop(session_id, None)

            logger.info(f"Terminated and cleaned up telephony session {session_id} ({reason})")
            return session

    def list_active_sessions(self) -> List[TelephonySessionInfo]:
        return [sess.to_info() for sess in self._sessions.values() if sess.state_machine.is_active]

    @property
    def active_calls_count(self) -> int:
        return len([s for s in self._sessions.values() if s.state_machine.is_active])


telephony_session_manager = RealtimeSessionManager()
