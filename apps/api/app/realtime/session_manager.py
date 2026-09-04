import asyncio
import logging
from collections import deque
from datetime import datetime, timezone
from typing import Any, Deque, Dict, List, Optional, Set
from fastapi import WebSocket

from app.core.config import get_settings
from app.core.telephony_state import CallState, CallStateMachine
from app.realtime.conversation_orchestrator import ConversationOrchestrator
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
        self.created_at: str = datetime.now(timezone.utc).isoformat()
        self.connected_at: Optional[str] = None
        self.ended_at: Optional[str] = None
        self.last_activity_at: str = datetime.now(timezone.utc).isoformat()

        # Bounded frame buffers (Separate per session)
        self.inbound_buffer: Deque[AudioFrame] = deque(maxlen=max_buffer_frames)
        self.outbound_queue: asyncio.Queue[bytes] = asyncio.Queue()

        # Phase 2 & 3 Conversational AI & Event History
        self.orchestrator: Optional[ConversationOrchestrator] = None
        self.event_history: Deque[Dict[str, Any]] = deque(maxlen=100)
        self.saved_utterances: List[Dict[str, Any]] = []

        # Phase 4 Deterministic Safety Signals
        self.active_safety_signals: List[Dict[str, Any]] = []
        self.saved_safety_state: str = "NONE"
        self.saved_safety_signals: List[Dict[str, Any]] = []

        # Phase 5 Deterministic SVI Assessments
        self.svi_history: List[Dict[str, Any]] = []
        self.latest_svi: Optional[Dict[str, Any]] = None

        # Phase 6 Deterministic Acoustic Assessments
        self.acoustic_history: List[Dict[str, Any]] = []
        self.latest_acoustic: Optional[Dict[str, Any]] = None

        # Phase 7 Adaptive Conversation Policy
        self.adaptive_history: List[Dict[str, Any]] = []
        self.latest_adaptive_strategy: Optional[Dict[str, Any]] = None

        # Metrics and sequence validation
        self.last_sequence_number: int = 0
        self.inbound_frames_count: int = 0
        self.inbound_bytes_count: int = 0
        self.sequence_gaps_count: int = 0
        self.dropped_frames_count: int = 0

        # Subscribed callbacks for downstream consumers
        self.frame_consumers: Set[Any] = set()

    def touch(self) -> None:
        self.last_activity_at = datetime.now(timezone.utc).isoformat()

    def record_event(self, envelope: Any) -> None:
        """Stores a serialized event in the bounded session event history and tracks safety signals."""
        try:
            dumped = None
            if hasattr(envelope, "model_dump"):
                dumped = envelope.model_dump()
            elif isinstance(envelope, dict):
                dumped = envelope

            if dumped:
                self.event_history.append(dumped)
                # If safety signal, record in active safety signals
                ev_type_str = str(dumped.get("event_type", ""))
                if "SAFETY_SIGNAL" in ev_type_str:
                    sig_payload = dumped.get("payload", {})
                    # Prevent duplicates by signal_id
                    if not any(s.get("signal_id") == sig_payload.get("signal_id") for s in self.active_safety_signals):
                        self.active_safety_signals.append(sig_payload)
                elif "SVI_UPDATED" in ev_type_str:
                    svi_payload = dumped.get("payload", {})
                    self.latest_svi = svi_payload
                    self.svi_history.append(svi_payload)
                elif "ACOUSTIC_UPDATE" in ev_type_str:
                    ac_payload = dumped.get("payload", {})
                    self.latest_acoustic = ac_payload
                    self.acoustic_history.append(ac_payload)
                elif "ADAPTIVE_STRATEGY_SELECTED" in ev_type_str:
                    ad_payload = dumped.get("payload", {})
                    self.latest_adaptive_strategy = ad_payload
                    self.adaptive_history.append(ad_payload)
        except Exception as e:
            logger.error(f"Error recording event in session {self.session_id}: {e}")

    def record_svi_assessment(self, assessment: Any) -> None:
        """Stores SVI assessment in session history."""
        dumped = assessment.model_dump() if hasattr(assessment, "model_dump") else assessment
        self.latest_svi = dumped
        self.svi_history.append(dumped)

    def get_latest_svi(self) -> Optional[Dict[str, Any]]:
        """Returns latest SVI assessment dictionary."""
        return self.latest_svi

    def get_svi_history(self) -> List[Dict[str, Any]]:
        """Returns complete SVI assessment history list."""
        return list(self.svi_history)

    def record_acoustic_assessment(self, assessment: Any) -> None:
        """Stores Acoustic assessment in session history."""
        dumped = assessment.model_dump() if hasattr(assessment, "model_dump") else assessment
        self.latest_acoustic = dumped
        self.acoustic_history.append(dumped)

    def get_latest_acoustic(self) -> Optional[Dict[str, Any]]:
        """Returns latest acoustic assessment dictionary."""
        return self.latest_acoustic

    def get_acoustic_history(self) -> List[Dict[str, Any]]:
        """Returns complete acoustic assessment history list."""
        return list(self.acoustic_history)

    def record_adaptive_strategy(self, strategy: Any) -> None:
        """Stores Adaptive strategy in session history."""
        dumped = strategy.model_dump() if hasattr(strategy, "model_dump") else strategy
        self.latest_adaptive_strategy = dumped
        self.adaptive_history.append(dumped)

    def get_latest_adaptive_strategy(self) -> Optional[Dict[str, Any]]:
        """Returns latest adaptive strategy dictionary."""
        return self.latest_adaptive_strategy

    def get_adaptive_history(self) -> List[Dict[str, Any]]:
        """Returns complete adaptive strategy history list."""
        return list(self.adaptive_history)

    def acknowledge_signal(self, signal_id: str, acknowledged_by: str = "operator") -> Optional[Dict[str, Any]]:
        """Records operator acknowledgment on an active safety signal."""
        for sig in self.active_safety_signals:
            if sig.get("signal_id") == signal_id:
                sig["acknowledged"] = True
                sig["acknowledged_at"] = datetime.now(timezone.utc).isoformat()
                sig["acknowledged_by"] = acknowledged_by
                return sig
        return None

    def calculate_duration(self) -> float:
        """Calculates call duration in seconds based on connected_at and ended_at/now."""
        start_str = self.connected_at or self.created_at
        if not start_str:
            return 0.0
        try:
            start_dt = datetime.fromisoformat(start_str)
            if self.ended_at:
                end_dt = datetime.fromisoformat(self.ended_at)
            else:
                end_dt = datetime.now(timezone.utc)
            return max(0.0, round((end_dt - start_dt).total_seconds(), 2))
        except Exception:
            return 0.0

    def get_utterances(self) -> List[Dict[str, Any]]:
        """Returns ordered list of conversation utterances."""
        if self.orchestrator and self.orchestrator.utterances:
            return [
                {
                    "utterance_id": u.utterance_id,
                    "speaker": u.speaker.value if hasattr(u.speaker, "value") else str(u.speaker),
                    "text": u.text,
                    "language": u.language.value if hasattr(u.language, "value") else str(u.language),
                    "confidence": u.confidence,
                    "is_final": u.is_final,
                    "intent": getattr(u, "intent", None),
                    "safety_flag": getattr(u, "safety_flag", False),
                    "created_at": getattr(u, "created_at", datetime.now(timezone.utc).isoformat()),
                    "timestamp": getattr(u, "created_at", datetime.now(timezone.utc).isoformat()),
                }
                for u in self.orchestrator.utterances
            ]
        return list(self.saved_utterances)

    def get_summary_dict(self) -> Dict[str, Any]:
        """Returns dictionary summary for REST API and operator console."""
        conv_state = self.orchestrator.state.value if self.orchestrator else "ENDED"
        current_lang = self.orchestrator.current_language.value if self.orchestrator else "unknown"
        safety_state = self.orchestrator.current_safety_state if self.orchestrator else getattr(self, "saved_safety_state", "NONE")
        utts = self.get_utterances()

        latest_svi_score = self.latest_svi.get("score") if self.latest_svi else None
        latest_svi_band = self.latest_svi.get("band") if self.latest_svi else "LOW"

        latest_acoustic_quality = self.latest_acoustic.get("quality") if self.latest_acoustic else "GOOD"
        latest_acoustic_confidence = self.latest_acoustic.get("confidence") if self.latest_acoustic else 1.0
        latest_acoustic_signals_count = len(self.latest_acoustic.get("signals", [])) if self.latest_acoustic else 0

        return {
            "session_id": self.session_id,
            "call_id": self.call_id,
            "provider_call_id": self.provider_call_id,
            "provider": self.provider,
            "caller_masked_number": self.masked_caller_number,
            "state": self.state_machine.current_state.value,
            "created_at": self.created_at,
            "connected_at": self.connected_at,
            "ended_at": self.ended_at,
            "last_activity_at": self.last_activity_at,
            "duration_seconds": self.calculate_duration(),
            "conversation_state": conv_state,
            "current_language": current_lang,
            "safety_state": safety_state,
            "safety_signals": list(self.active_safety_signals),
            "safety_signals_count": len(self.active_safety_signals),
            "svi_score": latest_svi_score,
            "svi_band": latest_svi_band,
            "latest_svi": self.latest_svi,
            "acoustic_quality": latest_acoustic_quality,
            "acoustic_confidence": latest_acoustic_confidence,
            "acoustic_signals_count": latest_acoustic_signals_count,
            "latest_acoustic": self.latest_acoustic,
            "latest_adaptive_strategy": self.latest_adaptive_strategy,
            "adaptive_action": self.latest_adaptive_strategy.get("action") if self.latest_adaptive_strategy else None,
            "adaptive_priority": self.latest_adaptive_strategy.get("priority") if self.latest_adaptive_strategy else None,
            "utterances_count": len(utts),
            "events_count": len(self.event_history),
            "is_active": self.state_machine.is_active,
        }

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

        # Feed frame to attached orchestrator for STT & voice activity detection
        if self.orchestrator:
            self.orchestrator.on_inbound_audio_frame(frame)

        # Feed frame to acoustic engine for realtime acoustic analysis (Phase 6)
        try:
            from app.services.acoustic_engine import acoustic_engine
            acoustic_engine.ingest_frame(
                session_id=self.session_id,
                call_id=self.call_id,
                frame_bytes=frame.get_raw_bytes(),
            )
        except Exception as e:
            logger.debug(f"Acoustic frame ingestion error: {e}")

        # Broadcast frame to attached consumers
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
        conv_state = self.orchestrator.state.value if self.orchestrator else None
        current_lang = self.orchestrator.current_language.value if self.orchestrator else None
        utts_count = len(self.orchestrator.utterances) if self.orchestrator else 0
        safety_state = self.orchestrator.current_safety_state if self.orchestrator else getattr(self, "saved_safety_state", "NONE")

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
            conversation_state=conv_state,
            current_language=current_lang,
            utterances_count=utts_count,
            safety_state=safety_state,
            safety_signals_count=len(self.active_safety_signals),
            is_active=self.state_machine.is_active,
        )


def create_session_orchestrator(session: TelephonySession) -> ConversationOrchestrator:
    """Factory creating conversation orchestrator with appropriate live or mock providers."""
    settings = get_settings()
    from app.providers.gemini import GeminiLLMProvider
    from app.providers.mocks import (
        MockLLMProvider,
        MockSpeechToTextProvider,
        MockTextToSpeechProvider,
    )
    from app.providers.sarvam_stt import SarvamSTTProvider
    from app.providers.sarvam_tts import SarvamTTSProvider
    from app.realtime.connection_manager import manager
    from app.schemas.events import EventEnvelope, EventType

    # Use live providers only if in LIVE mode with credentials
    if settings.is_live() and settings.SARVAM_API_KEY and settings.GEMINI_API_KEY:
        stt = SarvamSTTProvider()
        llm = GeminiLLMProvider()
        tts = SarvamTTSProvider()
        logger.info(f"Initialized LIVE Sarvam STT, Gemini, and Sarvam TTS for session {session.session_id}")
    else:
        stt = MockSpeechToTextProvider()
        llm = MockLLMProvider()
        tts = MockTextToSpeechProvider()
        logger.info(f"Initialized MOCK STT, LLM, and TTS for session {session.session_id}")

    def broadcast_to_operator(event_type_str: str, payload: Dict[str, Any]):
        try:
            try:
                ev_type = EventType(event_type_str)
            except ValueError:
                ev_type = EventType.AI_RESPONSE_STARTED

            envelope = EventEnvelope(
                event_type=ev_type,
                session_id=session.session_id,
                call_id=session.call_id,
                payload=payload,
            )
            # Record in session bounded event history
            session.record_event(envelope)

            # Fire-and-forget broadcast to all active operator dashboard WebSockets
            asyncio.create_task(manager.broadcast_global(envelope))
        except Exception as e:
            logger.error(f"Error broadcasting event {event_type_str}: {e}")

    return ConversationOrchestrator(
        session_id=session.session_id,
        call_id=session.call_id,
        stt_provider=stt,
        llm_provider=llm,
        tts_provider=tts,
        outbound_queue=session.outbound_queue,
        event_broadcaster=broadcast_to_operator,
    )


class RealtimeSessionManager:
    """Concurrency-safe global manager for active and recent telephony calls."""

    def __init__(self, max_recent_history: int = 50):
        self._sessions: Dict[str, TelephonySession] = {}
        self._provider_call_id_map: Dict[str, str] = {}  # provider_call_id -> session_id
        self._call_id_map: Dict[str, str] = {}           # call_id -> session_id
        self._recent_sessions: Deque[Dict[str, Any]] = deque(maxlen=max_recent_history)
        self._recent_calls_map: Dict[str, Dict[str, Any]] = {}
        self._lock = asyncio.Lock()

    async def create_session(
        self,
        session_id: str,
        call_id: str,
        provider_call_id: str,
        caller_number: str,
        provider: str = "exotel",
        attach_ai: bool = True,
    ) -> TelephonySession:
        async with self._lock:
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

            if attach_ai:
                orchestrator = create_session_orchestrator(session)
                session.orchestrator = orchestrator
                await orchestrator.start()

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

            # 1. Snapshot utterances, safety state and mark ended timestamp
            session.saved_utterances = session.get_utterances()
            session.saved_safety_state = session.orchestrator.current_safety_state if session.orchestrator else "NONE"
            session.saved_safety_signals = list(session.active_safety_signals)
            session.ended_at = datetime.now(timezone.utc).isoformat()

            # 2. Stop conversation orchestrator cleanly
            if session.orchestrator:
                try:
                    await session.orchestrator.stop()
                except Exception as e:
                    logger.error(f"Error stopping orchestrator for {session_id}: {e}")
                session.orchestrator = None

            if session.state_machine.can_transition_to(CallState.ENDED):
                session.state_machine.transition_to(CallState.ENDED, reason=reason)
            elif session.state_machine.can_transition_to(CallState.FAILED):
                session.state_machine.transition_to(CallState.FAILED, reason=reason)

            # 3. Store in bounded recent completed calls history
            summary = session.get_summary_dict()
            summary["events"] = list(session.event_history)
            summary["utterances"] = list(session.saved_utterances)
            summary["safety_signals"] = list(session.saved_safety_signals)
            summary["safety_state"] = session.saved_safety_state
            summary["latest_svi"] = session.get_latest_svi()
            summary["svi_history"] = session.get_svi_history()
            summary["latest_acoustic"] = session.get_latest_acoustic()
            summary["acoustic_history"] = session.get_acoustic_history()
            self._recent_sessions.appendleft(summary)
            self._recent_calls_map[session.call_id] = summary
            if len(self._recent_calls_map) > 100:
                oldest_key = next(iter(self._recent_calls_map))
                del self._recent_calls_map[oldest_key]

            # 4. Close WebSocket if still open
            if session.websocket:
                try:
                    await session.websocket.close()
                except Exception:
                    pass
                session.websocket = None

            # 5. Clear audio buffers
            session.inbound_buffer.clear()

            # 6. Remove from active lookup maps to prevent memory leakage
            self._provider_call_id_map.pop(session.provider_call_id, None)
            self._call_id_map.pop(session.call_id, None)
            self._sessions.pop(session_id, None)

            logger.info(f"Terminated and archived telephony session {session_id} ({reason})")
            return session

    def list_active_sessions(self) -> List[TelephonySessionInfo]:
        return [sess.to_info() for sess in self._sessions.values() if sess.state_machine.is_active]

    def list_calls(self) -> Dict[str, Any]:
        """Returns structured lists of active and recently completed calls."""
        active = [sess.get_summary_dict() for sess in self._sessions.values() if sess.state_machine.is_active]
        recent = list(self._recent_sessions)
        return {
            "active_calls": active,
            "recent_calls": recent,
            "total_active": len(active),
            "total_recent": len(recent),
        }

    async def get_call_summary(self, call_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves call summary from active sessions or recent history."""
        sess = await self.get_by_call_id(call_id)
        if sess:
            return sess.get_summary_dict()
        return self._recent_calls_map.get(call_id)

    async def get_call_transcript(self, call_id: str) -> Optional[List[Dict[str, Any]]]:
        """Retrieves ordered transcript turns for an active or completed call."""
        sess = await self.get_by_call_id(call_id)
        if sess:
            return sess.get_utterances()
        if call_id in self._recent_calls_map:
            return self._recent_calls_map[call_id].get("utterances", [])
        return None

    async def get_call_events(self, call_id: str) -> Optional[List[Dict[str, Any]]]:
        """Retrieves recent domain events for an active or completed call."""
        sess = await self.get_by_call_id(call_id)
        if sess:
            return list(sess.event_history)
        if call_id in self._recent_calls_map:
            return self._recent_calls_map[call_id].get("events", [])
        return None

    async def get_call_safety(self, call_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves safety state and active signals for an active or completed call."""
        sess = await self.get_by_call_id(call_id)
        if sess:
            state = sess.orchestrator.current_safety_state if sess.orchestrator else getattr(sess, "saved_safety_state", "NONE")
            assessments = []
            if sess.orchestrator:
                assessments = [a.model_dump() for a in sess.orchestrator.safety_assessments]
            return {
                "call_id": call_id,
                "session_id": sess.session_id,
                "safety_state": state,
                "safety_signals": list(sess.active_safety_signals),
                "safety_signals_count": len(sess.active_safety_signals),
                "assessments": assessments,
            }
        if call_id in self._recent_calls_map:
            c = self._recent_calls_map[call_id]
            return {
                "call_id": call_id,
                "session_id": c.get("session_id"),
                "safety_state": c.get("safety_state", "NONE"),
                "safety_signals": c.get("safety_signals", []),
                "safety_signals_count": len(c.get("safety_signals", [])),
                "assessments": [],
            }
        return None

    async def get_call_svi(self, call_id: str) -> Optional[Dict[str, Any]]:
        """Returns latest SVI assessment for active or completed call."""
        sess = await self.get_by_call_id(call_id)
        if sess:
            latest = sess.get_latest_svi()
            if not latest and sess.orchestrator and getattr(sess.orchestrator, "latest_svi", None):
                latest = sess.orchestrator.latest_svi.model_dump()
            return latest
        if call_id in self._recent_calls_map:
            c = self._recent_calls_map[call_id]
            return c.get("latest_svi")
        return None

    async def get_call_svi_history(self, call_id: str) -> Optional[List[Dict[str, Any]]]:
        """Returns complete SVI assessment history for active or completed call."""
        sess = await self.get_by_call_id(call_id)
        if sess:
            hist = sess.get_svi_history()
            if not hist and sess.orchestrator and getattr(sess.orchestrator, "svi_assessments", None):
                hist = [a.model_dump() for a in sess.orchestrator.svi_assessments]
            return hist
        if call_id in self._recent_calls_map:
            c = self._recent_calls_map[call_id]
            return c.get("svi_history", [])
        return None

    async def get_call_acoustic(self, call_id: str) -> Optional[Dict[str, Any]]:
        """Returns latest Acoustic assessment for active or completed call."""
        sess = await self.get_by_call_id(call_id)
        if sess:
            latest = sess.get_latest_acoustic()
            if not latest:
                from app.services.acoustic_engine import acoustic_engine
                latest_ass = acoustic_engine.get_latest_assessment(sess.session_id)
                if latest_ass:
                    latest = latest_ass.model_dump()
            return latest
        if call_id in self._recent_calls_map:
            c = self._recent_calls_map[call_id]
            return c.get("latest_acoustic")
        return None

    async def get_call_acoustic_history(self, call_id: str) -> Optional[List[Dict[str, Any]]]:
        """Returns complete Acoustic assessment history for active or completed call."""
        sess = await self.get_by_call_id(call_id)
        if sess:
            hist = sess.get_acoustic_history()
            if not hist:
                from app.services.acoustic_engine import acoustic_engine
                hist_ass = acoustic_engine.get_assessment_history(sess.session_id)
                if hist_ass:
                    hist = [a.model_dump() for a in hist_ass]
            return hist
        if call_id in self._recent_calls_map:
            c = self._recent_calls_map[call_id]
            return c.get("acoustic_history", [])
        return None

    async def get_call_adaptive(self, call_id: str) -> Optional[Dict[str, Any]]:
        """Returns latest Adaptive Strategy for active or completed call."""
        sess = await self.get_by_call_id(call_id)
        if sess:
            latest = sess.get_latest_adaptive_strategy()
            if not latest:
                from app.adaptive.service import adaptive_engine
                latest_strat = adaptive_engine.get_latest_strategy(call_id)
                if latest_strat:
                    latest = latest_strat.model_dump()
            return latest
        if call_id in self._recent_calls_map:
            c = self._recent_calls_map[call_id]
            return c.get("latest_adaptive_strategy")
        return None

    async def get_call_adaptive_history(self, call_id: str) -> Optional[List[Dict[str, Any]]]:
        """Returns complete Adaptive Strategy history for active or completed call."""
        sess = await self.get_by_call_id(call_id)
        if sess:
            hist = sess.get_adaptive_history()
            if not hist:
                from app.adaptive.service import adaptive_engine
                hist_resp = adaptive_engine.get_call_history(call_id)
                if hist_resp and hist_resp.strategies:
                    hist = [s.model_dump() for s in hist_resp.strategies]
            return hist
        if call_id in self._recent_calls_map:
            c = self._recent_calls_map[call_id]
            return c.get("adaptive_history", [])
        return None

    async def apply_call_operator_override(
        self, call_id: str, action: str, reason: str, operator_id: str = "operator"
    ) -> Optional[Dict[str, Any]]:
        """Applies manual operator override to an active call and broadcasts notification."""
        from app.adaptive.models import OperatorOverrideAction
        from app.adaptive.service import adaptive_engine

        try:
            act_enum = OperatorOverrideAction(action)
        except ValueError:
            logger.error(f"Invalid operator override action: {action}")
            return None

        override = adaptive_engine.apply_operator_override(
            call_id=call_id,
            action=act_enum,
            reason=reason,
            operator_id=operator_id,
        )

        sess = await self.get_by_call_id(call_id)
        if sess and sess.orchestrator:
            sess.orchestrator.broadcast(
                "OPERATOR_OVERRIDE_APPLIED",
                {
                    "call_id": call_id,
                    "session_id": sess.session_id,
                    "action": action,
                    "reason": reason,
                    "operator_id": operator_id,
                    "timestamp": override.applied_at,
                },
            )

        return override.model_dump()

    async def acknowledge_call_signal(
        self, call_id: str, signal_id: str, acknowledged_by: str = "operator"
    ) -> Optional[Dict[str, Any]]:
        """Acknowledges a safety signal on an active or completed call and broadcasts the event."""
        sess = await self.get_by_call_id(call_id)
        sig = None
        if sess:
            sig = sess.acknowledge_signal(signal_id, acknowledged_by=acknowledged_by)
            if sig:
                # Broadcast SAFETY_SIGNAL_ACKNOWLEDGED domain event
                from app.schemas.events import EventEnvelope, EventType
                env = EventEnvelope(
                    event_type=EventType.SAFETY_SIGNAL_ACKNOWLEDGED,
                    call_id=call_id,
                    session_id=sess.session_id,
                    payload={
                        "call_id": call_id,
                        "session_id": sess.session_id,
                        "signal_id": signal_id,
                        "acknowledged_by": acknowledged_by,
                        "acknowledged_at": sig.get("acknowledged_at"),
                    },
                )
                sess.record_event(env)
                if sess.orchestrator:
                    for sub in list(sess.orchestrator.subscribers):
                        try:
                            res = sub(env)
                            if asyncio.iscoroutine(res):
                                asyncio.create_task(res)
                        except Exception as e:
                            logger.error(f"Error broadcasting safety ack event: {e}")
                return sig

        if call_id in self._recent_calls_map:
            c = self._recent_calls_map[call_id]
            for s in c.get("safety_signals", []):
                if s.get("signal_id") == signal_id:
                    s["acknowledged"] = True
                    s["acknowledged_at"] = datetime.now(timezone.utc).isoformat()
                    s["acknowledged_by"] = acknowledged_by
                    return s
        return None

    @property
    def active_calls_count(self) -> int:
        return len([s for s in self._sessions.values() if s.state_machine.is_active])


telephony_session_manager = RealtimeSessionManager()