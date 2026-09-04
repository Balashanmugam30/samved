from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
import uuid
from pydantic import BaseModel, Field


class AcousticQuality(str, Enum):
    EXCELLENT = "EXCELLENT"
    GOOD = "GOOD"
    DEGRADED = "DEGRADED"
    POOR = "POOR"
    INSUFFICIENT = "INSUFFICIENT"


class OperationalSignalCode(str, Enum):
    PROLONGED_SILENCE_OBSERVED = "PROLONGED_SILENCE_OBSERVED"
    FREQUENT_INTERRUPTION_PATTERN = "FREQUENT_INTERRUPTION_PATTERN"
    HIGH_SPEECH_ACTIVITY = "HIGH_SPEECH_ACTIVITY"
    LOW_VOICE_ACTIVITY = "LOW_VOICE_ACTIVITY"
    ELEVATED_ENERGY_VARIABILITY = "ELEVATED_ENERGY_VARIABILITY"
    AUDIO_QUALITY_LOW = "AUDIO_QUALITY_LOW"
    AUDIO_QUALITY_DEGRADED = "AUDIO_QUALITY_DEGRADED"
    SIGNAL_INSUFFICIENT = "SIGNAL_INSUFFICIENT"
    ACOUSTIC_UNAVAILABLE = "ACOUSTIC_UNAVAILABLE"
    ACOUSTIC_LOW_CONFIDENCE = "ACOUSTIC_LOW_CONFIDENCE"


class AcousticOperationalSignal(BaseModel):
    code: OperationalSignalCode
    evidence: str = Field(..., description="Explainable factual evidence chip")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    threshold_applied: Optional[str] = None


class VoiceActivityMetrics(BaseModel):
    speech_activity_ratio: float = Field(..., ge=0.0, le=1.0, description="Voiced frames / total frames")
    silence_ratio: float = Field(..., ge=0.0, le=1.0, description="Silent frames / total frames")
    total_voiced_ms: int = Field(default=0, ge=0)
    total_silence_ms: int = Field(default=0, ge=0)


class PauseMetrics(BaseModel):
    pause_count: int = Field(default=0, ge=0)
    avg_pause_duration_ms: float = Field(default=0.0, ge=0.0)
    longest_pause_ms: int = Field(default=0, ge=0)
    sustained_silence_count: int = Field(default=0, ge=0, description="Pauses >= 3000ms")


class TurnMetrics(BaseModel):
    turn_duration_ms: int = Field(default=0, ge=0)
    speech_segment_duration_ms: int = Field(default=0, ge=0)
    turn_density: float = Field(default=0.0, ge=0.0)


class InterruptionMetrics(BaseModel):
    interruption_count: int = Field(default=0, ge=0)
    assistant_speech_cancelled_count: int = Field(default=0, ge=0)
    overlap_count: int = Field(default=0, ge=0)
    rapid_interruption_detected: bool = False


class EnergyMetrics(BaseModel):
    mean_energy_rms: float = Field(default=0.0, ge=0.0)
    energy_variability: float = Field(default=0.0, ge=0.0, description="Standard deviation / mean RMS")
    peak_energy_rms: float = Field(default=0.0, ge=0.0)
    low_signal_ratio: float = Field(default=0.0, ge=0.0, le=1.0)
    clipping_ratio: float = Field(default=0.0, ge=0.0, le=1.0)


class PitchMetrics(BaseModel):
    median_f0_hz: Optional[float] = Field(default=None, description="Bounded fundamental frequency in 80–350 Hz")
    f0_variability: Optional[float] = Field(default=None)
    voiced_frame_ratio: float = Field(default=0.0, ge=0.0, le=1.0)


class AcousticFrameFeatures(BaseModel):
    energy_rms: float = 0.0
    is_speech: bool = False
    is_clipping: bool = False
    zero_crossing_rate: float = 0.0
    f0_hz: Optional[float] = None


class AcousticAssessment(BaseModel):
    assessment_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    call_id: str
    session_id: str
    turn_id: Optional[str] = None
    window_start_ms: int = 0
    window_end_ms: int = 0
    quality: AcousticQuality = AcousticQuality.GOOD
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    voice_activity: VoiceActivityMetrics
    pause_metrics: PauseMetrics
    turn_metrics: TurnMetrics
    interruption_metrics: InterruptionMetrics
    energy_metrics: EnergyMetrics
    pitch_metrics: PitchMetrics
    operational_signals: List[AcousticOperationalSignal] = Field(default_factory=list)
    engine_version: str = "v1.0.0"
    is_supporting_signal: bool = True
    disclaimer: str = (
        "Acoustic analysis is an operational support signal and is not a clinical, medical, "
        "diagnostic, lie-detection, credibility, or psychological state classifier."
    )
    evaluated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class AcousticEvaluationRequest(BaseModel):
    call_id: Optional[str] = "sim-call-acoustic"
    session_id: Optional[str] = "sim-sess-acoustic"
    turn_id: Optional[str] = None
    audio_duration_ms: int = Field(default=4000, ge=100, le=60000)
    speech_ratio: float = Field(default=0.65, ge=0.0, le=1.0)
    max_silence_ms: int = Field(default=1200, ge=0)
    interruptions: int = Field(default=0, ge=0)
    energy_variability: float = Field(default=0.25, ge=0.0)
    clipping_ratio: float = Field(default=0.0, ge=0.0, le=1.0)
    mean_rms: float = Field(default=450.0, ge=0.0)
    raw_pcm_base64: Optional[str] = None


class AcousticStatusResponse(BaseModel):
    status: str = "ready"
    engine_version: str = "v1.0.0"
    canonical_sample_rate_hz: int = 8000
    frame_duration_ms: int = 20
    is_operational_support_only: bool = True
    disclaimer: str


class AcousticRuleItem(BaseModel):
    signal_code: str
    description: str
    threshold: str
    category: str


class AcousticRulesResponse(BaseModel):
    engine_version: str = "v1.0.0"
    rules_count: int
    rules: List[AcousticRuleItem]
    sample_rate_hz: int = 8000
    frame_size_bytes: int = 320


class AcousticHistoryResponse(BaseModel):
    call_id: str
    assessments_count: int
    assessments: List[AcousticAssessment]
