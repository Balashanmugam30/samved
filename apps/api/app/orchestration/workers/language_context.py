"""LanguageContextAgent: Rule-based transcript language, dialect, and code-switching analyzer."""

import re
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


class LanguageContextAgent(BaseAgentWorker):
    """Rule worker analyzing caller language, code-switching patterns, and dialect cues."""

    # Unicode ranges
    TAMIL_RANGE = re.compile(r"[\u0B80-\u0BFF]")
    DEVANAGARI_RANGE = re.compile(r"[\u0900-\u097F]")
    LATIN_RANGE = re.compile(r"[A-Za-z]")

    # Common code-switching vocabulary cues
    TANGLISH_MARKERS = {"romba", "konjam", "yenna", "inga", "theriyala", "please", "sir", "madam", "help", "call", "police"}
    HINGLISH_MARKERS = {"bohot", "thoda", "kya", "yahan", "pata", "nahi", "please", "sir", "madam", "help", "call", "police"}

    def __init__(self):
        spec = AgentSpec(
            name="language_context_agent",
            version="1.0.0",
            agent_type=AgentType.RULE_WORKER,
            capabilities=["language_detection", "code_switch_analysis", "script_detection"],
            timeout_tier=AgentTimeoutTier.REALTIME_CRITICAL,
            max_latency_ms=50,
            safety_classification=AgentSafetyClassification.OPERATIONAL,
            requires_human_review=False,
            is_realtime_capable=True,
            enabled=True,
        )
        super().__init__(spec)

    async def execute(self, request: AgentRequest) -> AgentResponse:
        start_time = time.perf_counter()
        ctx = request.relevant_context or {}
        transcript = ctx.get("transcript") or ctx.get("text") or ""
        expected_lang = request.language or ctx.get("language") or "ta-IN"

        # Character script detection
        has_tamil = bool(self.TAMIL_RANGE.search(transcript))
        has_devanagari = bool(self.DEVANAGARI_RANGE.search(transcript))
        has_latin = bool(self.LATIN_RANGE.search(transcript))

        detected_scripts = []
        if has_tamil:
            detected_scripts.append("Tamil")
        if has_devanagari:
            detected_scripts.append("Devanagari")
        if has_latin:
            detected_scripts.append("Latin")

        # Code-switching detection
        words = set(re.findall(r"\w+", transcript.lower()))
        code_switched = False
        dialect_notes: List[str] = []

        if expected_lang.startswith("ta"):
            if has_latin and has_tamil:
                code_switched = True
                dialect_notes.append("Tamil-English mixed script")
            elif has_latin and (words & self.TANGLISH_MARKERS):
                code_switched = True
                dialect_notes.append("Tanglish (Tamil in Latin script)")
        elif expected_lang.startswith("hi"):
            if has_latin and has_devanagari:
                code_switched = True
                dialect_notes.append("Hindi-English mixed script")
            elif has_latin and (words & self.HINGLISH_MARKERS):
                code_switched = True
                dialect_notes.append("Hinglish (Hindi in Latin script)")

        evidence_refs: List[str] = []
        if code_switched:
            evidence_refs.append("lang:code_switching_detected")
        for s in detected_scripts:
            evidence_refs.append(f"script:{s.lower()}")

        result: Dict[str, Any] = {
            "primary_language": expected_lang,
            "detected_scripts": detected_scripts,
            "code_switching_detected": code_switched,
            "dialect_notes": dialect_notes,
            "recommended_response_language": expected_lang,
            "response_style": "simplified_colloquial" if code_switched else "standard_compassionate",
        }

        latency_ms = (time.perf_counter() - start_time) * 1000
        return self.create_success_response(
            request=request,
            result=result,
            confidence=0.9,
            evidence_refs=evidence_refs,
            latency_ms=latency_ms,
        )
