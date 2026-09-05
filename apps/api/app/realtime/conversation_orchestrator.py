import asyncio
import logging
import time
import uuid
from collections import deque
from datetime import datetime, timezone
from typing import Any, Callable, Deque, Dict, List, Optional, Set

from app.core.config import get_settings
from app.realtime.audio_adapter import AudioStreamAdapter
from app.schemas.conversation import (
    ConversationalResponse,
    ConversationState,
    TranscriptEvent,
    TurnLatency,
    TurnSpeaker,
    Utterance,
)
from app.schemas.languages import LanguageCode
from app.schemas.telephony import AudioFrame

logger = logging.getLogger("samved.conversation.orchestrator")


class ConversationOrchestrator:
    """Coordinates STT, Gemini reasoning, and Sarvam TTS synthesis for a voice call."""

    def __init__(
        self,
        session_id: str,
        call_id: str,
        stt_provider: Any,
        llm_provider: Any,
        tts_provider: Any,
        outbound_queue: asyncio.Queue,
        event_broadcaster: Optional[Callable[[str, Dict[str, Any]], None]] = None,
        max_context_utterances: int = 12,
    ):
        self.session_id = session_id
        self.call_id = call_id
        self.stt = stt_provider
        self.llm = llm_provider
        self.tts = tts_provider
        self.outbound_queue = outbound_queue
        self.broadcast = event_broadcaster or (lambda event_type, payload: None)

        self.state = ConversationState.LISTENING
        self.current_language = LanguageCode.TA  # Default to Tamil / multilingual auto-detect
        self.utterances: Deque[Utterance] = deque(maxlen=max_context_utterances)

        # Phase 4 Deterministic Safety Engine tracking
        self.current_safety_state = "NONE"
        self.fired_safety_signals: Set[str] = set()
        self.safety_assessments: List[Any] = []

        # Phase 5 Deterministic SVI Engine tracking
        self.latest_svi: Optional[Any] = None
        self.svi_assessments: List[Any] = []

        # Phase 6 Deterministic Acoustic Engine tracking
        self.latest_acoustic: Optional[Any] = None
        self.acoustic_assessments: List[Any] = []

        # Phase 7 Deterministic Adaptive Conversation Policy tracking
        self.latest_adaptive_strategy: Optional[Any] = None
        self.adaptive_strategies: List[Any] = []

        # Phase 9 Multi-Agent Orchestration tracking
        self.latest_orchestration: Optional[Any] = None
        self.orchestration_results: List[Any] = []
        self._current_orchestration_cancel_event: Optional[asyncio.Event] = None

        # Active turn & latency tracking
        self.active_latency = TurnLatency()
        self.last_completed_latency = TurnLatency()
        self._current_speech_task: Optional[asyncio.Task] = None
        self._worker_tasks: List[asyncio.Task] = []
        self._is_running = False

    def transition_state(self, new_state: ConversationState, reason: str = "") -> None:
        old_state = self.state
        self.state = new_state
        logger.info(f"Session {self.session_id} state transition: {old_state} -> {new_state} ({reason})")
        self.broadcast(
            "CONVERSATION_STATE_CHANGED",
            {
                "session_id": self.session_id,
                "call_id": self.call_id,
                "old_state": old_state.value,
                "new_state": new_state.value,
                "reason": reason,
            },
        )

    def on_inbound_audio_frame(self, frame: AudioFrame) -> None:
        """Called for every 20ms inbound audio frame from telephony gateway."""
        if not self._is_running:
            return

        raw_pcm = frame.get_raw_bytes()

        # Barge-in / interruption detection:
        # If SAMVED is currently SPEAKING and caller produces speech, interrupt!
        if self.state == ConversationState.SPEAKING:
            if AudioStreamAdapter.is_speech_active(raw_pcm, threshold_rms=350.0):
                logger.info(f"Barge-in detected via voice activity for session {self.session_id}!")
                try:
                    from app.services.acoustic_engine import acoustic_engine
                    acoustic_engine.record_interruption(self.session_id)
                except Exception:
                    pass
                self.interrupt(reason="caller_voice_barge_in")

        # Asynchronously forward chunk to STT provider
        asyncio.create_task(self.stt.send_audio_chunk(self.session_id, raw_pcm))

    def interrupt(self, reason: str = "barge_in") -> None:
        """Interrupts ongoing AI speech immediately, clears outbound buffer, and listens."""
        if self._current_speech_task and not self._current_speech_task.done():
            self._current_speech_task.cancel()
            self._current_speech_task = None

        if self._current_orchestration_cancel_event and not self._current_orchestration_cancel_event.is_set():
            self._current_orchestration_cancel_event.set()

        # Drain outbound queue to stop audio playback on telephone line
        while not self.outbound_queue.empty():
            try:
                self.outbound_queue.get_nowait()
                self.outbound_queue.task_done()
            except (asyncio.QueueEmpty, ValueError):
                break

        self.transition_state(ConversationState.INTERRUPTED, reason=reason)
        self.broadcast(
            "SPEECH_INTERRUPTED",
            {"session_id": self.session_id, "call_id": self.call_id, "reason": reason},
        )
        # Immediately return to LISTENING
        self.transition_state(ConversationState.LISTENING, reason="interruption_cleared")

    async def handle_transcript_event(self, event: TranscriptEvent) -> None:
        """Processes partial and final transcripts from STT."""
        # 1. Check language detection / changes
        new_lang = LanguageCode.from_str(event.language)
        if new_lang != LanguageCode.UNKNOWN and new_lang != self.current_language:
            old_lang = self.current_language
            self.current_language = new_lang
            self.broadcast(
                "LANGUAGE_CHANGED",
                {
                    "session_id": self.session_id,
                    "call_id": self.call_id,
                    "old_language": old_lang.value,
                    "new_language": new_lang.value,
                },
            )

        # 2. Handle partial draft transcript
        if not event.is_final:
            if self.state == ConversationState.LISTENING:
                self.transition_state(ConversationState.TRANSCRIBING, reason="partial_transcript")
            self.broadcast(
                "TRANSCRIPT_PARTIAL",
                {
                    "session_id": self.session_id,
                    "call_id": self.call_id,
                    "speaker": "caller",
                    "text": event.text,
                    "confidence": event.confidence,
                    "language": self.current_language.value,
                },
            )
            return

        # 3. Handle final transcript (Turn boundary reached)
        self.active_latency.caller_speech_ended_at = time.time()
        self.active_latency.final_transcript_at = time.time()

        utterance = Utterance(
            speaker=TurnSpeaker.CALLER,
            text=event.text,
            language=self.current_language.value,
            confidence=event.confidence,
            is_final=True,
        )
        self.utterances.append(utterance)

        self.broadcast(
            "TRANSCRIPT_FINAL",
            {
                "session_id": self.session_id,
                "call_id": self.call_id,
                "utterance_id": utterance.utterance_id,
                "speaker": "caller",
                "text": event.text,
                "confidence": event.confidence,
                "language": self.current_language.value,
            },
        )

        # 4. Phase 4: Deterministic Safety Evaluation
        try:
            from app.services.safety_engine import safety_engine
            safety_assessment = safety_engine.evaluate_turn(
                utterance_text=event.text,
                language=self.current_language.value,
                call_id=self.call_id,
                session_id=self.session_id,
                utterance_id=utterance.utterance_id,
                previously_fired_signals=self.fired_safety_signals,
            )

            # Record in safety history
            self.safety_assessments.append(safety_assessment)

            # Update utterance safety flag
            if safety_assessment.current_state.value in ("HIGH", "CRITICAL"):
                utterance.safety_flag = True

            # Emit SAFETY_SIGNAL events for any newly triggered signals
            for sig in safety_assessment.signals:
                self.broadcast(
                    "SAFETY_SIGNAL",
                    {
                        "call_id": self.call_id,
                        "session_id": self.session_id,
                        "signal_id": sig.signal_id,
                        "signal_type": sig.signal_type.value,
                        "severity": sig.severity.value,
                        "rule_id": sig.rule_id,
                        "rule_version": sig.rule_version,
                        "reason": sig.evidence.reason,
                        "matched_phrase": sig.evidence.matched_phrase,
                        "requires_human_review": sig.requires_human_review,
                        "source_utterance_id": utterance.utterance_id,
                        "created_at": sig.created_at,
                    },
                )

            # Emit SAFETY_STATE_UPDATED if safety state changed
            new_state_val = safety_assessment.current_state.value
            if new_state_val != self.current_safety_state and new_state_val != "NONE":
                prev_state_val = self.current_safety_state
                self.current_safety_state = new_state_val
                self.broadcast(
                    "SAFETY_STATE_UPDATED",
                    {
                        "call_id": self.call_id,
                        "session_id": self.session_id,
                        "previous_state": prev_state_val,
                        "current_state": new_state_val,
                        "highest_severity": safety_assessment.highest_severity.value,
                        "requires_human_review": safety_assessment.requires_human_review,
                        "signals_count": len(safety_assessment.signals),
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    },
                )
        except Exception as e:
            logger.error(f"Error in deterministic safety evaluation for {self.session_id}: {e}")

        # 5. Phase 6: Deterministic Acoustic Analysis Evaluation
        acoustic_assessment = None
        try:
            from app.services.acoustic_engine import acoustic_engine
            acoustic_assessment = acoustic_engine.evaluate_window(
                call_id=self.call_id,
                session_id=self.session_id,
                turn_id=utterance.utterance_id,
            )
            self.latest_acoustic = acoustic_assessment
            self.acoustic_assessments.append(acoustic_assessment)

            # Broadcast ACOUSTIC_UPDATE event
            if acoustic_assessment:
                self.broadcast(
                    "ACOUSTIC_UPDATE",
                    {
                        "call_id": self.call_id,
                        "session_id": self.session_id,
                        "quality": acoustic_assessment.quality.value,
                        "confidence": acoustic_assessment.confidence,
                        "speech_activity_ratio": acoustic_assessment.voice_activity.speech_activity_ratio,
                        "silence_ratio": acoustic_assessment.voice_activity.silence_ratio,
                        "longest_pause_ms": acoustic_assessment.pause_metrics.longest_pause_ms,
                        "pause_count": acoustic_assessment.pause_metrics.pause_count,
                        "interruption_count": acoustic_assessment.interruption_metrics.interruption_count,
                        "energy_variability": acoustic_assessment.energy_metrics.energy_variability,
                        "mean_energy_rms": acoustic_assessment.energy_metrics.mean_energy_rms,
                        "median_f0_hz": acoustic_assessment.pitch_metrics.median_f0_hz,
                        "signals": [
                            {
                                "code": s.code.value if hasattr(s.code, "value") else str(s.code),
                                "evidence": s.evidence,
                                "confidence": s.confidence,
                            }
                            for s in acoustic_assessment.operational_signals
                        ],
                        "engine_version": acoustic_assessment.engine_version,
                        "disclaimer": acoustic_assessment.disclaimer,
                        "is_supporting_signal": True,
                        "evaluated_at": acoustic_assessment.evaluated_at,
                    },
                )
        except Exception as e:
            logger.error(f"Error in acoustic evaluation for {self.session_id}: {e}")

        # 6. Phase 5: Deterministic SVI Evaluation
        try:
            from app.services.svi_engine import svi_engine
            turns_data = [
                {
                    "speaker": u.speaker.value if hasattr(u.speaker, "value") else str(u.speaker),
                    "text": u.text,
                    "language": u.language.value if hasattr(u.language, "value") else str(u.language),
                }
                for u in self.utterances
            ]
            all_signals = [sig for sa in self.safety_assessments for sig in sa.signals]
            prev_score = self.latest_svi.score if self.latest_svi else None
            svi_assessment = svi_engine.evaluate_session(
                call_id=self.call_id,
                session_id=self.session_id,
                turns=turns_data,
                safety_signals=all_signals,
                previous_score=prev_score,
                turn_index=len(self.utterances),
                acoustic_assessment=acoustic_assessment,
            )
            self.latest_svi = svi_assessment
            self.svi_assessments.append(svi_assessment)

            # Broadcast SVI_UPDATED event
            self.broadcast(
                "SVI_UPDATED",
                {
                    "call_id": self.call_id,
                    "session_id": self.session_id,
                    "score": svi_assessment.score,
                    "band": svi_assessment.band.value,
                    "trend": svi_assessment.trend.value,
                    "delta": svi_assessment.delta,
                    "confidence": 1.0,
                    "assessment_completeness": svi_assessment.assessment_completeness,
                    "top_contributors": svi_assessment.top_contributors,
                    "contributing_factors": [
                        {
                            "factor": f.feature_name,
                            "weight": f.weighted_score,
                            "evidence": f.matched_phrase or f.description,
                        }
                        for f in svi_assessment.features
                    ],
                    "protective_factor_reduction": svi_assessment.protective_factor_reduction,
                    "critical_override_applied": svi_assessment.critical_override_applied,
                    "requires_human_review": svi_assessment.requires_human_review,
                    "acoustic_evidence_note": svi_assessment.acoustic_evidence_note,
                    "is_clinical_diagnosis": False,
                    "disclaimer": svi_assessment.disclaimer,
                    "evaluated_at": svi_assessment.evaluated_at,
                },
            )
        except Exception as e:
            logger.error(f"Error in deterministic SVI evaluation for {self.session_id}: {e}")

        # 7. Phase 7: Deterministic Adaptive Conversation Planning
        try:
            from app.adaptive.service import adaptive_engine
            strategy = adaptive_engine.evaluate_turn(
                call_id=self.call_id,
                session_id=self.session_id,
                turn_index=len(self.utterances),
                utterance_text=event.text,
                language=self.current_language.value,
                safety_assessment=self.safety_assessments[-1] if self.safety_assessments else None,
                svi_assessment=self.latest_svi,
                acoustic_assessment=acoustic_assessment,
            )
            self.latest_adaptive_strategy = strategy
            self.adaptive_strategies.append(strategy)

            # Broadcast ADAPTIVE_STRATEGY_SELECTED event
            self.broadcast(
                "ADAPTIVE_STRATEGY_SELECTED",
                {
                    "call_id": self.call_id,
                    "session_id": self.session_id,
                    "turn_index": strategy.turn_index,
                    "action": strategy.action.value,
                    "priority": strategy.priority.value,
                    "target_information": strategy.target_information,
                    "reason_codes": [r.value for r in strategy.reason_codes],
                    "evidence_refs": strategy.evidence_refs,
                    "language": strategy.language,
                    "confidence": strategy.confidence,
                    "constraints": strategy.constraints,
                    "requires_human_review": strategy.requires_human_review,
                    "operator_override_active": strategy.operator_override_active,
                    "fallback_applied": strategy.fallback_applied,
                    "disclaimer": strategy.disclaimer,
                    "evaluated_at": strategy.evaluated_at,
                },
            )
        except Exception as e:
            logger.error(f"Error in adaptive planning for {self.session_id}: {e}")

        # 8. Phase 9: Multi-Agent Orchestration Coordination
        try:
            from app.orchestration.service import multi_agent_orchestrator

            self._current_orchestration_cancel_event = asyncio.Event()

            orch_context = {
                "transcript": event.text,
                "text": event.text,
                "language": self.current_language.value,
                "history": [
                    {
                        "speaker": u.speaker.value if hasattr(u.speaker, "value") else str(u.speaker),
                        "text": u.text,
                    }
                    for u in self.utterances
                ],
                "safety_state": self.current_safety_state,
                "safety_evaluation": (
                    self.safety_assessments[-1].model_dump()
                    if (self.safety_assessments and hasattr(self.safety_assessments[-1], "model_dump"))
                    else {}
                ),
                "acoustic_features": (
                    acoustic_assessment.model_dump()
                    if (acoustic_assessment and hasattr(acoustic_assessment, "model_dump"))
                    else {}
                ),
                "svi": (
                    self.latest_svi.model_dump()
                    if (self.latest_svi and hasattr(self.latest_svi, "model_dump"))
                    else {}
                ),
                "adaptive": (
                    strategy.model_dump()
                    if (strategy and hasattr(strategy, "model_dump"))
                    else {}
                ),
            }

            async def _orch_callback(ev_type: str, payload: Dict[str, Any]):
                self.broadcast(ev_type, payload)

            orch_result = await multi_agent_orchestrator.orchestrate_turn(
                call_id=self.call_id,
                turn_id=utterance.utterance_id,
                context=orch_context,
                safety_state=self.current_safety_state,
                cancel_event=self._current_orchestration_cancel_event,
                event_callback=_orch_callback,
            )
            self.latest_orchestration = orch_result
            self.orchestration_results.append(orch_result)

            if orch_result.briefing:
                self.broadcast(
                    "OPERATOR_BRIEFING_GENERATED",
                    {
                        "call_id": self.call_id,
                        "turn_id": utterance.utterance_id,
                        "briefing": orch_result.briefing.model_dump(),
                        "orchestration_state": orch_result.state.value,
                        "total_latency_ms": orch_result.total_latency_ms,
                    },
                )
        except Exception as e:
            logger.error(f"Error in multi-agent orchestration for {self.session_id}: {e}")

        # If agent was speaking when final transcript landed, ensure interruption was performed
        if self.state == ConversationState.SPEAKING:
            self.interrupt(reason="final_transcript_barge_in")

        # Launch reasoning & speech generation as a cancellable task
        self._current_speech_task = asyncio.create_task(self._execute_ai_turn(utterance))

    async def _execute_ai_turn(self, caller_utterance: Utterance) -> None:
        """Executes LLM reasoning and TTS playback for an AI response turn."""
        try:
            self.broadcast(
                "AI_THINKING",
                {"session_id": self.session_id, "call_id": self.call_id, "prompt": caller_utterance.text},
            )

            # Phase 8: Check if Operator Takeover (HUMAN_ACTIVE) or Adaptive Paused
            try:
                from app.operator.service import operator_service
                if operator_service.is_human_active(self.call_id) or operator_service.is_adaptive_paused(self.call_id):
                    logger.info(
                        f"AI speech generation suppressed for call {self.call_id} (Human active or adaptive paused)"
                    )
                    self.transition_state(ConversationState.LISTENING, reason="operator_control_suppressed_ai_turn")
                    return
            except Exception as e:
                logger.debug(f"Operator control check error: {e}")

            self.transition_state(ConversationState.THINKING, reason="ai_reasoning_started")

            # Check if adaptive strategy calls for direct deterministic response template
            strategy = self.latest_adaptive_strategy
            response: Optional[ConversationalResponse] = None

            if strategy and strategy.action.value in ("ALLOW_SILENCE", "PAUSE_ADAPTIVE_QUESTIONS", "HUMAN_HANDOFF"):
                from app.adaptive.templates import get_template
                template_text = get_template(strategy.action, self.current_language.value)
                response = ConversationalResponse(
                    response_text=template_text,
                    detected_intent=strategy.action.value,
                    conversation_state="HUMAN_HANDOFF" if strategy.action.value == "HUMAN_HANDOFF" else "ENGAGED",
                    next_action="HANDOFF" if strategy.action.value == "HUMAN_HANDOFF" else "CONTINUE",
                    language=self.current_language.value,
                    confidence=1.0,
                    safety_flag=strategy.requires_human_review,
                )
            else:
                # Build recent conversational message history
                messages = [
                    {"role": "user" if u.speaker == TurnSpeaker.CALLER else "assistant", "content": u.text}
                    for u in self.utterances
                ]

                # 1. Call LLM (Gemini or Mock)
                response = await self.llm.generate_conversational_response(
                    messages=messages,
                    language=self.current_language.value,
                )

                # Validate response against Adaptive Response Policy
                if strategy:
                    from app.adaptive.validator import ResponseValidator
                    is_valid, reason, validated_text = ResponseValidator.validate_response(
                        response.response_text, strategy
                    )
                    if not is_valid:
                        logger.warning(
                            f"Response validation failed for {self.session_id}: {reason}. "
                            "Applying deterministic fallback template."
                        )
                        response.response_text = validated_text
                        strategy.fallback_applied = True

            self.active_latency.llm_response_at = time.time()

            agent_utterance = Utterance(
                speaker=TurnSpeaker.AGENT,
                text=response.response_text,
                language=response.language,
                confidence=response.confidence,
                is_final=True,
            )
            self.utterances.append(agent_utterance)

            self.broadcast(
                "AI_RESPONSE_STARTED",
                {
                    "session_id": self.session_id,
                    "call_id": self.call_id,
                    "speaker": "agent",
                    "text": response.response_text,
                    "intent": response.detected_intent,
                    "safety_flag": response.safety_flag,
                    "language": response.language,
                },
            )

            # 2. Transition to SPEAKING and synthesize TTS
            self.transition_state(ConversationState.SPEAKING, reason="tts_synthesis_started")
            self.broadcast(
                "TTS_STARTED",
                {"session_id": self.session_id, "call_id": self.call_id, "text_length": len(response.response_text)},
            )

            pcm_audio = await self.tts.synthesize(
                text=response.response_text,
                language_code=response.language,
            )

            if pcm_audio:
                self.active_latency.first_tts_frame_at = time.time()
                # Slice into 320-byte (20ms) frames
                frames = AudioStreamAdapter.slice_pcm_to_frames(pcm_audio)
                for chunk in frames:
                    # Cooperative check: if interrupted, break early
                    if self.state != ConversationState.SPEAKING:
                        logger.info(f"Playback aborted due to state change ({self.state})")
                        break
                    await self.outbound_queue.put(chunk)

            self.broadcast("TTS_ENDED", {"session_id": self.session_id, "call_id": self.call_id})
            self.broadcast(
                "AI_RESPONSE_ENDED",
                {
                    "session_id": self.session_id,
                    "call_id": self.call_id,
                    "stt_latency_ms": self.active_latency.stt_latency_ms,
                    "llm_latency_ms": self.active_latency.llm_latency_ms,
                    "tts_latency_ms": self.active_latency.tts_latency_ms,
                    "total_latency_ms": self.active_latency.total_turn_latency_ms,
                },
            )

            # Save completed latency record
            self.last_completed_latency = self.active_latency
            self.active_latency = TurnLatency()

            # Return to LISTENING for caller's next turn
            self.transition_state(ConversationState.LISTENING, reason="turn_completed")

        except asyncio.CancelledError:
            logger.info(f"AI response turn cancelled for session {self.session_id}")
            raise
        except Exception as e:
            logger.error(f"Error during AI turn for session {self.session_id}: {e}")
            self.transition_state(ConversationState.ERROR, reason=str(e))
            self.transition_state(ConversationState.LISTENING, reason="recovered_from_error")

    async def start(self) -> None:
        """Starts background STT receiver task."""
        self._is_running = True
        await self.stt.start_stream(self.session_id, language_code=self.current_language.value)

        async def stt_listener():
            try:
                async for event in self.stt.receive_transcripts(self.session_id):
                    if not self._is_running:
                        break
                    await self.handle_transcript_event(event)
            except asyncio.CancelledError:
                pass
            except Exception as e:
                logger.error(f"Error in STT listener worker for {self.session_id}: {e}")

        task = asyncio.create_task(stt_listener())
        self._worker_tasks.append(task)
        logger.info(f"Conversation orchestrator started for session {self.session_id}")

    async def stop(self) -> None:
        """Clean shutdown: cancels active tasks and closes STT streams."""
        self._is_running = False
        if self._current_speech_task and not self._current_speech_task.done():
            self._current_speech_task.cancel()

        for t in self._worker_tasks:
            if not t.done():
                t.cancel()

        await self.stt.close_stream(self.session_id)
        self.transition_state(ConversationState.ENDING, reason="session_stopped")
        logger.info(f"Conversation orchestrator stopped for session {self.session_id}")