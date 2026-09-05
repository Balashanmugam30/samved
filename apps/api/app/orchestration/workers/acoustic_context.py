"""AcousticContextAgent: Telemetry adapter over Phase 6 Acoustic Analysis Engine."""

import time
from typing import Any, Dict, List

from app.orchestration.contracts import BaseAgentWorker
from app.orchestration.models import (
    AgentRequest,
    AgentResponse,
    AgentSafetyClassification,
    AgentSpec,
    AgentTimeoutTier,
    AgentType,
)


class AcousticContextAgent(BaseAgentWorker):
    """Deterministic adapter extracting acoustic telemetry and vocal biomarkers."""

    def __init__(self):
        spec = AgentSpec(
            name="acoustic_context_agent",
            version="1.0.0",
            agent_type=AgentType.DETERMINISTIC_ADAPTER,
            capabilities=["acoustic_telemetry", "vocal_biomarkers", "distress_signals"],
            timeout_tier=AgentTimeoutTier.REALTIME_CRITICAL,
            max_latency_ms=25,
            safety_classification=AgentSafetyClassification.OPERATIONAL,
            requires_human_review=False,
            is_realtime_capable=True,
            enabled=True,
        )
        super().__init__(spec)

    async def execute(self, request: AgentRequest) -> AgentResponse:
        start_time = time.perf_counter()
        ctx = request.relevant_context or {}

        # Read acoustic telemetry from context
        acoustic_features = ctx.get("acoustic_features") or ctx.get("acoustic") or {}

        f0_hz = acoustic_features.get("f0_hz", 0.0)
        jitter = acoustic_features.get("jitter", 0.0)
        shimmer = acoustic_features.get("shimmer", 0.0)
        snr_db = acoustic_features.get("snr_db", 0.0)
        speech_rate_wpm = acoustic_features.get("speech_rate_wpm", 0.0)
        tremor_detected = acoustic_features.get("tremor_detected", False)
        distress_crying = acoustic_features.get("distress_crying", False)
        respiratory_strain = acoustic_features.get("respiratory_strain", False)
        distress_score = acoustic_features.get("distress_score", 0.0)

        # Operational categorization
        operational_signals: List[str] = []
        if distress_crying:
            operational_signals.append("crying_detected")
        if tremor_detected:
            operational_signals.append("vocal_tremor")
        if respiratory_strain:
            operational_signals.append("respiratory_strain")
        if speech_rate_wpm > 180:
            operational_signals.append("rapid_speech")
        elif speech_rate_wpm < 80 and speech_rate_wpm > 0:
            operational_signals.append("halting_speech")

        evidence_refs = [f"acoustic:{s}" for s in operational_signals]

        result: Dict[str, Any] = {
            "f0_hz": f0_hz,
            "jitter": jitter,
            "shimmer": shimmer,
            "snr_db": snr_db,
            "speech_rate_wpm": speech_rate_wpm,
            "tremor_detected": tremor_detected,
            "distress_crying": distress_crying,
            "respiratory_strain": respiratory_strain,
            "distress_score": distress_score,
            "operational_signals": operational_signals,
            "biomarker_summary": f"Distress score {distress_score:.2f}, signals: {', '.join(operational_signals) if operational_signals else 'normal'}",
        }

        latency_ms = (time.perf_counter() - start_time) * 1000
        return self.create_success_response(
            request=request,
            result=result,
            confidence=0.95 if snr_db > 10 else 0.7,
            evidence_refs=evidence_refs,
            latency_ms=latency_ms,
        )
