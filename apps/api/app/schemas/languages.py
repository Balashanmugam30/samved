from enum import Enum
from typing import Dict, Optional
from pydantic import BaseModel


class LanguageCode(str, Enum):
    """Canonical Indian language codes for SAMVED telephony & speech pipelines."""
    TA = "ta-IN"       # Tamil (Primary SIH Target)
    HI = "hi-IN"       # Hindi (National Helpline Standard)
    EN = "en-IN"       # Indian English
    UNKNOWN = "unknown"

    @classmethod
    def from_str(cls, val: Optional[str]) -> "LanguageCode":
        if not val:
            return cls.UNKNOWN
        v = val.strip().lower()
        if "ta" in v or "tamil" in v:
            return cls.TA
        if "hi" in v or "hindi" in v:
            return cls.HI
        if "en" in v or "english" in v:
            return cls.EN
        return cls.UNKNOWN


class LanguageInfo(BaseModel):
    code: LanguageCode
    name: str
    native_name: str
    sarvam_code: str
    gemini_instruction: str


LANGUAGE_REGISTRY: Dict[LanguageCode, LanguageInfo] = {
    LanguageCode.TA: LanguageInfo(
        code=LanguageCode.TA,
        name="Tamil",
        native_name="தமிழ்",
        sarvam_code="ta-IN",
        gemini_instruction="Respond naturally in Tamil. Use simple, warm, conversational colloquial Tamil appropriate for a helpline.",
    ),
    LanguageCode.HI: LanguageInfo(
        code=LanguageCode.HI,
        name="Hindi",
        native_name="हिन्दी",
        sarvam_code="hi-IN",
        gemini_instruction="Respond naturally in Hindi. Use simple, empathetic, conversational Hindustani appropriate for a helpline.",
    ),
    LanguageCode.EN: LanguageInfo(
        code=LanguageCode.EN,
        name="Indian English",
        native_name="English",
        sarvam_code="en-IN",
        gemini_instruction="Respond naturally in clear, empathetic Indian English. Keep sentences short and conversational.",
    ),
    LanguageCode.UNKNOWN: LanguageInfo(
        code=LanguageCode.UNKNOWN,
        name="Unknown",
        native_name="Unknown",
        sarvam_code="unknown",
        gemini_instruction="Respond in simple English or acknowledge the caller with empathy.",
    ),
}


def get_language_info(code: LanguageCode) -> LanguageInfo:
    return LANGUAGE_REGISTRY.get(code, LANGUAGE_REGISTRY[LanguageCode.UNKNOWN])