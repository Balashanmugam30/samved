import base64
import logging
import math
import statistics
import struct
import time
from collections import deque
from datetime import datetime, timezone
from typing import Any, Deque, Dict, List, Optional, Tuple

from app.schemas.acoustic import (
    AcousticAssessment,
    AcousticEvaluationRequest,
    AcousticFrameFeatures,
    AcousticOperationalSignal,
    AcousticQuality,
    AcousticRuleItem,
    AcousticRulesResponse,
    AcousticStatusResponse,
    EnergyMetrics,
    InterruptionMetrics,
    OperationalSignalCode,
    PauseMetrics,
    PitchMetrics,
    TurnMetrics,
    VoiceActivityMetrics,
)

logger = logging.getLogger("samved.acoustic.engine")


class AcousticEngine:
    """
    Deterministic, explainable Acoustic Analysis Engine for canonical 8kHz telephony audio.
    Extracts physical voice activity, pause metrics, energy variability, clipping, and bounded F0.
    Produces evidence-based operational support signals without clinical or psychological inference.
    """

    FRAME_SIZE_BYTES = 320  # 20ms at 8000 Hz, 16-bit mono PCM (160 samples * 2 bytes)
    SAMPLE_RATE_HZ = 8000
    FRAME_DURATION_MS = 20
    SAMPLES_PER_FRAME = 160

    VAD_RMS_THRESHOLD = 300.0
    LOW_SIGNAL_RMS_THRESHOLD = 25.0
    CLIPPING_AMPLITUDE = 32000
    PROLONGED_SILENCE_THRESHOLD_MS = 3000
    MIN_PAUSE_MS = 400  # Minimum consecutive silence to register as a pause

    def __init__(self, max_history_frames: int = 1500) -> None:
        self.engine_version = "v1.0.0"
        self.max_history_frames = max_history_frames
        # Per-session rolling frame history: session_id -> Deque[AcousticFrameFeatures]
        self._session_frames: Dict[str, Deque[AcousticFrameFeatures]] = {}
        # Per-session interruptions counter
        self._session_interruptions: Dict[str, int] = {}
        # Per-session latest assessment cache
        self._latest_assessments: Dict[str, AcousticAssessment] = {}
        # Per-session assessment history
        self._session_assessments: Dict[str, List[AcousticAssessment]] = {}

    def extract_frame_features(self, pcm_bytes: bytes) -> AcousticFrameFeatures:
        """Extracts low-level physical features from a single 20ms PCM frame."""
        if not pcm_bytes or len(pcm_bytes) < 2:
            return AcousticFrameFeatures()

        count = len(pcm_bytes) // 2
        try:
            samples = struct.unpack(f"<{count}h", pcm_bytes[: count * 2])
        except Exception as e:
            logger.debug(f"Error unpacking PCM frame: {e}")
            return AcousticFrameFeatures()

        if count == 0:
            return AcousticFrameFeatures()

        # 1. RMS Energy
        sum_sq = sum(s * s for s in samples)
        rms = math.sqrt(sum_sq / count)

        # 2. Clipping detection
        clipped_count = sum(1 for s in samples if abs(s) >= self.CLIPPING_AMPLITUDE)
        is_clipping = clipped_count > 0

        # 3. Zero-crossing rate
        zcr = 0.0
        if count > 1:
            crossings = sum(1 for i in range(1, count) if (samples[i] >= 0) != (samples[i - 1] >= 0))
            zcr = crossings / (count - 1)

        # 4. Voice Activity
        is_speech = rms >= self.VAD_RMS_THRESHOLD and not (is_clipping and clipped_count > count * 0.5)

        # 5. Bounded Pitch (F0) estimation via autocorrelation for voiced frames
        f0_hz: Optional[float] = None
        if is_speech and count >= 100:
            # Range for 8kHz: 80 Hz (lag 100) to 350 Hz (lag 23)
            min_lag = 23
            max_lag = min(100, count - 1)
            best_lag = -1
            max_corr = -1.0
            e0 = sum_sq

            if e0 > 1000:
                for lag in range(min_lag, max_lag + 1):
                    corr = sum(samples[n] * samples[n + lag] for n in range(count - lag))
                    # Normalized correlation
                    e_lag = sum(samples[n + lag] * samples[n + lag] for n in range(count - lag))
                    denom = math.sqrt(e0 * e_lag) if e_lag > 0 else 0
                    norm_corr = corr / denom if denom > 0 else 0
                    if norm_corr > max_corr:
                        max_corr = norm_corr
                        best_lag = lag

                if max_corr > 0.35 and best_lag > 0:
                    f0_hz = round(self.SAMPLE_RATE_HZ / best_lag, 1)

        return AcousticFrameFeatures(
            energy_rms=round(rms, 2),
            is_speech=is_speech,
            is_clipping=is_clipping,
            zero_crossing_rate=round(zcr, 4),
            f0_hz=f0_hz,
        )

    def ingest_frame(
        self,
        session_id: str,
        call_id: str,
        frame_bytes: bytes,
        is_interruption: bool = False,
    ) -> AcousticFrameFeatures:
        """Processes and stores a 20ms audio frame for an active telephony session."""
        features = self.extract_frame_features(frame_bytes)

        if session_id not in self._session_frames:
            self._session_frames[session_id] = deque(maxlen=self.max_history_frames)
            self._session_interruptions[session_id] = 0
            self._session_assessments[session_id] = []

        self._session_frames[session_id].append(features)

        if is_interruption:
            self._session_interruptions[session_id] = self._session_interruptions.get(session_id, 0) + 1

        return features

    def record_interruption(self, session_id: str) -> None:
        """Explicitly increments the caller interruption counter for the session."""
        self._session_interruptions[session_id] = self._session_interruptions.get(session_id, 0) + 1

    def evaluate_window(
        self,
        call_id: str,
        session_id: str,
        window_frames: Optional[List[AcousticFrameFeatures]] = None,
        turn_id: Optional[str] = None,
    ) -> AcousticAssessment:
        """Aggregates frame features across a window or turn and evaluates operational signals."""
        t_start = time.perf_counter()

        frames = window_frames
        if frames is None:
            frames = list(self._session_frames.get(session_id, []))

        total_frames = len(frames)
        duration_ms = total_frames * self.FRAME_DURATION_MS
        interruptions = self._session_interruptions.get(session_id, 0)

        # 1. Base case: Insufficient signal
        if total_frames < 10:  # < 200ms
            signals = [
                AcousticOperationalSignal(
                    code=OperationalSignalCode.SIGNAL_INSUFFICIENT,
                    evidence=f"Insufficient audio frames for assessment ({duration_ms}ms < 200ms)",
                    confidence=0.5,
                )
            ]
            assessment = AcousticAssessment(
                call_id=call_id,
                session_id=session_id,
                turn_id=turn_id,
                window_start_ms=0,
                window_end_ms=duration_ms,
                quality=AcousticQuality.INSUFFICIENT,
                confidence=0.4,
                voice_activity=VoiceActivityMetrics(
                    speech_activity_ratio=0.0,
                    silence_ratio=1.0,
                    total_voiced_ms=0,
                    total_silence_ms=duration_ms,
                ),
                pause_metrics=PauseMetrics(),
                turn_metrics=TurnMetrics(turn_duration_ms=duration_ms),
                interruption_metrics=InterruptionMetrics(interruption_count=interruptions),
                energy_metrics=EnergyMetrics(),
                pitch_metrics=PitchMetrics(),
                operational_signals=signals,
                engine_version=self.engine_version,
            )
            self._cache_assessment(session_id, assessment)
            return assessment

        # 2. Voice Activity & Pause Analysis
        voiced_frames = sum(1 for f in frames if f.is_speech)
        silent_frames = total_frames - voiced_frames
        speech_ratio = voiced_frames / total_frames
        silence_ratio = silent_frames / total_frames

        # Run-length silence decoding for pause metrics
        pauses_ms: List[int] = []
        current_silent_run = 0
        sustained_silences = 0

        for f in frames:
            if not f.is_speech:
                current_silent_run += self.FRAME_DURATION_MS
            else:
                if current_silent_run >= self.MIN_PAUSE_MS:
                    pauses_ms.append(current_silent_run)
                    if current_silent_run >= self.PROLONGED_SILENCE_THRESHOLD_MS:
                        sustained_silences += 1
                current_silent_run = 0

        # Account for trailing silence
        if current_silent_run >= self.MIN_PAUSE_MS:
            pauses_ms.append(current_silent_run)
            if current_silent_run >= self.PROLONGED_SILENCE_THRESHOLD_MS:
                sustained_silences += 1

        longest_pause_ms = max(pauses_ms) if pauses_ms else 0
        pause_count = len(pauses_ms)
        avg_pause_duration_ms = round(statistics.mean(pauses_ms), 1) if pauses_ms else 0.0

        # 3. Energy Metrics
        energies = [f.energy_rms for f in frames]
        mean_rms = statistics.mean(energies) if energies else 0.0
        peak_rms = max(energies) if energies else 0.0
        std_rms = statistics.stdev(energies) if len(energies) > 1 else 0.0
        energy_variability = round(std_rms / mean_rms, 2) if mean_rms > 1.0 else 0.0

        low_signal_frames = sum(1 for f in frames if f.energy_rms < self.LOW_SIGNAL_RMS_THRESHOLD)
        low_signal_ratio = low_signal_frames / total_frames
        clipped_frames = sum(1 for f in frames if f.is_clipping)
        clipping_ratio = clipped_frames / total_frames

        # 4. Pitch Metrics
        f0_values = [f.f0_hz for f in frames if f.f0_hz is not None]
        median_f0: Optional[float] = None
        f0_var: Optional[float] = None
        if f0_values:
            median_f0 = round(statistics.median(f0_values), 1)
            if len(f0_values) > 1:
                f0_var = round(statistics.stdev(f0_values), 1)

        # 5. Quality Determination
        if clipping_ratio >= 0.12 or low_signal_ratio >= 0.75:
            quality = AcousticQuality.POOR
        elif clipping_ratio >= 0.04 or low_signal_ratio >= 0.40:
            quality = AcousticQuality.DEGRADED
        elif total_frames >= 50 and mean_rms >= 250.0 and clipping_ratio < 0.01:
            quality = AcousticQuality.EXCELLENT
        else:
            quality = AcousticQuality.GOOD

        # Confidence calculation
        confidence = 1.0 - (clipping_ratio * 1.5) - (low_signal_ratio * 0.4)
        if duration_ms < 1000:
            confidence *= 0.8
        confidence = max(0.2, min(1.0, round(confidence, 2)))

        # 6. Operational Signals Classification
        signals: List[AcousticOperationalSignal] = []

        if longest_pause_ms >= self.PROLONGED_SILENCE_THRESHOLD_MS:
            signals.append(
                AcousticOperationalSignal(
                    code=OperationalSignalCode.PROLONGED_SILENCE_OBSERVED,
                    evidence=f"{longest_pause_ms}ms sustained low-activity window",
                    confidence=round(confidence, 2),
                    threshold_applied=f">={self.PROLONGED_SILENCE_THRESHOLD_MS}ms",
                )
            )

        if interruptions >= 2:
            signals.append(
                AcousticOperationalSignal(
                    code=OperationalSignalCode.FREQUENT_INTERRUPTION_PATTERN,
                    evidence=f"{interruptions} interruptions observed in active turn",
                    confidence=0.9,
                    threshold_applied=">=2 interruptions",
                )
            )

        if speech_ratio >= 0.85 and duration_ms >= 2000:
            signals.append(
                AcousticOperationalSignal(
                    code=OperationalSignalCode.HIGH_SPEECH_ACTIVITY,
                    evidence=f"Continuous caller speech ({round(speech_ratio * 100)}% voiced)",
                    confidence=round(confidence, 2),
                    threshold_applied=">=85% speech activity",
                )
            )
        elif speech_ratio <= 0.15 and duration_ms >= 2000:
            signals.append(
                AcousticOperationalSignal(
                    code=OperationalSignalCode.LOW_VOICE_ACTIVITY,
                    evidence=f"Extended caller hesitation ({round(speech_ratio * 100)}% voiced)",
                    confidence=round(confidence, 2),
                    threshold_applied="<=15% speech activity",
                )
            )

        if energy_variability >= 0.50 and quality in (AcousticQuality.GOOD, AcousticQuality.EXCELLENT):
            signals.append(
                AcousticOperationalSignal(
                    code=OperationalSignalCode.ELEVATED_ENERGY_VARIABILITY,
                    evidence=f"Substantial volume modulation detected (CV {energy_variability})",
                    confidence=round(confidence * 0.9, 2),
                    threshold_applied="CV >= 0.50",
                )
            )

        if quality == AcousticQuality.POOR:
            signals.append(
                AcousticOperationalSignal(
                    code=OperationalSignalCode.AUDIO_QUALITY_LOW,
                    evidence=f"Degraded telemetry (clipping {round(clipping_ratio * 100)}%, low-signal {round(low_signal_ratio * 100)}%)",
                    confidence=0.85,
                    threshold_applied="POOR quality",
                )
            )
        elif quality == AcousticQuality.DEGRADED:
            signals.append(
                AcousticOperationalSignal(
                    code=OperationalSignalCode.AUDIO_QUALITY_DEGRADED,
                    evidence="Moderate line noise or clipping detected",
                    confidence=0.8,
                    threshold_applied="DEGRADED quality",
                )
            )

        assessment = AcousticAssessment(
            call_id=call_id,
            session_id=session_id,
            turn_id=turn_id,
            window_start_ms=0,
            window_end_ms=duration_ms,
            quality=quality,
            confidence=confidence,
            voice_activity=VoiceActivityMetrics(
                speech_activity_ratio=round(speech_ratio, 2),
                silence_ratio=round(silence_ratio, 2),
                total_voiced_ms=voiced_frames * self.FRAME_DURATION_MS,
                total_silence_ms=silent_frames * self.FRAME_DURATION_MS,
            ),
            pause_metrics=PauseMetrics(
                pause_count=pause_count,
                avg_pause_duration_ms=avg_pause_duration_ms,
                longest_pause_ms=longest_pause_ms,
                sustained_silence_count=sustained_silences,
            ),
            turn_metrics=TurnMetrics(
                turn_duration_ms=duration_ms,
                speech_segment_duration_ms=voiced_frames * self.FRAME_DURATION_MS,
                turn_density=round(speech_ratio, 2),
            ),
            interruption_metrics=InterruptionMetrics(
                interruption_count=interruptions,
                rapid_interruption_detected=interruptions >= 2,
            ),
            energy_metrics=EnergyMetrics(
                mean_energy_rms=round(mean_rms, 1),
                energy_variability=energy_variability,
                peak_energy_rms=round(peak_rms, 1),
                low_signal_ratio=round(low_signal_ratio, 2),
                clipping_ratio=round(clipping_ratio, 2),
            ),
            pitch_metrics=PitchMetrics(
                median_f0_hz=median_f0,
                f0_variability=f0_var,
                voiced_frame_ratio=round(len(f0_values) / total_frames, 2) if total_frames > 0 else 0.0,
            ),
            operational_signals=signals,
            engine_version=self.engine_version,
            evaluated_at=datetime.now(timezone.utc).isoformat(),
        )

        latency_ms = round((time.perf_counter() - t_start) * 1000, 2)
        logger.debug(f"Acoustic evaluation completed for {session_id} in {latency_ms}ms (Quality: {quality.value})")

        self._cache_assessment(session_id, assessment)
        return assessment

    def evaluate_synthetic(self, request: AcousticEvaluationRequest) -> AcousticAssessment:
        """
        Deterministic synthetic evaluator for simulation lab, preset testing, and API verification.
        Generates synthetic 20ms frames matching requested parameters and evaluates them.
        """
        # If raw_pcm_base64 is supplied, decode and slice into frames
        if request.raw_pcm_base64:
            raw_bytes = base64.b64decode(request.raw_pcm_base64)
            frames: List[AcousticFrameFeatures] = []
            for i in range(0, len(raw_bytes), self.FRAME_SIZE_BYTES):
                chunk = raw_bytes[i : i + self.FRAME_SIZE_BYTES]
                if len(chunk) < self.FRAME_SIZE_BYTES:
                    chunk += b"\x00" * (self.FRAME_SIZE_BYTES - len(chunk))
                frames.append(self.extract_frame_features(chunk))
            return self.evaluate_window(
                call_id=request.call_id or "sim-call",
                session_id=request.session_id or "sim-session",
                window_frames=frames,
                turn_id=request.turn_id,
            )

        # Synthesize frame list based on request parameters
        num_frames = max(1, request.audio_duration_ms // self.FRAME_DURATION_MS)
        voiced_frames_count = int(num_frames * request.speech_ratio)
        silent_frames_count = num_frames - voiced_frames_count

        frames: List[AcousticFrameFeatures] = []

        # Create silent frames block if max_silence_ms is set
        silence_run_frames = min(silent_frames_count, max(1, request.max_silence_ms // self.FRAME_DURATION_MS))
        for _ in range(silence_run_frames):
            frames.append(
                AcousticFrameFeatures(
                    energy_rms=30.0,
                    is_speech=False,
                    is_clipping=False,
                    zero_crossing_rate=0.05,
                    f0_hz=None,
                )
            )

        # Remaining silent frames
        remaining_silence = silent_frames_count - silence_run_frames
        for _ in range(max(0, remaining_silence)):
            frames.append(
                AcousticFrameFeatures(
                    energy_rms=45.0,
                    is_speech=False,
                    is_clipping=False,
                    zero_crossing_rate=0.06,
                    f0_hz=None,
                )
            )

        # Voiced frames with requested energy & clipping
        num_clipped = math.ceil(num_frames * request.clipping_ratio)
        for i in range(voiced_frames_count):
            rms_val = request.mean_rms
            if request.energy_variability > 0:
                mod = math.sin(i / 5.0) * (request.mean_rms * request.energy_variability)
                rms_val = max(100.0, rms_val + mod)
            clip_frame = i < num_clipped
            frames.append(
                AcousticFrameFeatures(
                    energy_rms=round(rms_val, 1),
                    is_speech=True,
                    is_clipping=clip_frame,
                    zero_crossing_rate=0.18,
                    f0_hz=165.0,
                )
            )

        session_id = request.session_id or "sim-synthetic"
        self._session_interruptions[session_id] = request.interruptions

        return self.evaluate_window(
            call_id=request.call_id or "sim-call",
            session_id=session_id,
            window_frames=frames,
            turn_id=request.turn_id,
        )

    def _cache_assessment(self, session_id: str, assessment: AcousticAssessment) -> None:
        self._latest_assessments[session_id] = assessment
        if session_id not in self._session_assessments:
            self._session_assessments[session_id] = []
        self._session_assessments[session_id].append(assessment)

    def get_latest_assessment(self, session_id: str) -> Optional[AcousticAssessment]:
        return self._latest_assessments.get(session_id)

    def get_assessment_history(self, session_id: str) -> List[AcousticAssessment]:
        return list(self._session_assessments.get(session_id, []))

    def get_rules(self) -> AcousticRulesResponse:
        rules = [
            AcousticRuleItem(
                signal_code="PROLONGED_SILENCE_OBSERVED",
                description="Flags sustained absence of vocal energy exceeding 3000ms, indicating potential hesitation, distress, or environmental caution.",
                threshold="Max silence >= 3000ms",
                category="pause",
            ),
            AcousticRuleItem(
                signal_code="FREQUENT_INTERRUPTION_PATTERN",
                description="Flags repeated caller barge-in interruptions over assistant speech, indicating acute urgency or conversational collision.",
                threshold="Interruption count >= 2 in turn",
                category="interruption",
            ),
            AcousticRuleItem(
                signal_code="HIGH_SPEECH_ACTIVITY",
                description="Flags continuous unpaused speech exceeding 85% voice activity in turns longer than 2000ms.",
                threshold="Voiced frame ratio >= 0.85",
                category="voice_activity",
            ),
            AcousticRuleItem(
                signal_code="LOW_VOICE_ACTIVITY",
                description="Flags sparse vocal activity under 15% in turns longer than 2000ms.",
                threshold="Voiced frame ratio <= 0.15",
                category="voice_activity",
            ),
            AcousticRuleItem(
                signal_code="ELEVATED_ENERGY_VARIABILITY",
                description="Flags substantial vocal volume dynamic modulation where coefficient of variation exceeds 0.50.",
                threshold="RMS std / mean >= 0.50",
                category="energy",
            ),
            AcousticRuleItem(
                signal_code="AUDIO_QUALITY_LOW",
                description="Flags severe line distortion, acoustic clipping (>= 12%), or audio attenuation (low signal >= 75%).",
                threshold="Clipping >= 12% or low signal >= 75%",
                category="quality",
            ),
            AcousticRuleItem(
                signal_code="AUDIO_QUALITY_DEGRADED",
                description="Flags moderate line noise or clipping (>= 4%).",
                threshold="Clipping >= 4% or low signal >= 40%",
                category="quality",
            ),
            AcousticRuleItem(
                signal_code="SIGNAL_INSUFFICIENT",
                description="Flags audio duration under 200ms insufficient for reliable feature extraction.",
                threshold="Audio duration < 200ms",
                category="quality",
            ),
        ]
        return AcousticRulesResponse(
            engine_version=self.engine_version,
            rules_count=len(rules),
            rules=rules,
            sample_rate_hz=self.SAMPLE_RATE_HZ,
            frame_size_bytes=self.FRAME_SIZE_BYTES,
        )

    def get_status(self) -> AcousticStatusResponse:
        return AcousticStatusResponse(
            status="ready",
            engine_version=self.engine_version,
            canonical_sample_rate_hz=self.SAMPLE_RATE_HZ,
            frame_duration_ms=self.FRAME_DURATION_MS,
            is_operational_support_only=True,
            disclaimer=(
                "Acoustic analysis is an operational support signal and is not a clinical, medical, "
                "diagnostic, lie-detection, credibility, or psychological state classifier."
            ),
        )


# Global singleton instance
acoustic_engine = AcousticEngine()
