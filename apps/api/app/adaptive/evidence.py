"""Evidence aggregator and fact extraction layer for Adaptive Conversation Engine.

Extracts structured facts and intents from caller statements without external LLMs.
Handles contradiction detection and temporal recency precedence.
"""

from datetime import datetime, timezone
import re
from typing import Any, Dict, List, Optional, Set, Tuple

from app.adaptive.models import ConversationFact, FactPriority


class EvidenceExtractor:
    """Deterministic extractor for caller intent, facts, refusals, and contradiction resolution."""

    # Human request keywords across English, Tamil, and Hindi
    HUMAN_REQUEST_PATTERNS = [
        r"\b(person|human|officer|counselor|agent|operator|supervisor)\b",
        r"\b(talk to (a )?human|speak to (a )?person|connect me)\b",
        r"(மனிதர்|ஆலோசகர்|அதிகாரி|யாராவது பேசுங்கள்|மனிதரிடம்)",
        r"(इंसान|मानव|अधिकारी|परामर्शदाता|किसी से बात|ऑपरेटर)",
    ]

    # Caller refusal keywords
    REFUSAL_PATTERNS = [
        r"\b(don'?t want to (answer|say|tell)|won'?t answer|skip this|none of your business)\b",
        r"(பதில் சொல்ல மாட்டேன்|சொல்ல விரும்பவில்லை|கேட்காதீர்கள்|வேண்டாம்)",
        r"(नहीं बताना|जवाब नहीं दूंगा|छोड़ो|पूछना बंद करो)",
    ]

    # Caller stop / pause requests
    PAUSE_PATTERNS = [
        r"\b(stop|pause|wait a minute|can'?t talk right now|hold on)\b",
        r"(நிறுத்துங்கள்|காத்திருங்கள்|இப்போது பேச முடியாது|ஒரு நிமிடம்)",
        r"(रुकिए|ठहरिए|अभी बात नहीं कर सकता|एक मिनट)",
    ]

    # Immediate danger affirmations
    DANGER_AFFIRM_PATTERNS = [
        r"\b(yes|in danger|he is (here|outside|hitting)|attacking|hurting|knife|gun|weapon|threat)\b",
        r"(ஆமாம்|ஆபத்து|அடிக்கிறான்|வெளியே நிற்கிறான்|கத்தி|துப்பாக்கி)",
        r"(हाँ|खतरा|मार रहा है|बाहर खड़ा है|चाकू|हथियार|हमला)",
    ]

    # Safety / safe now affirmations
    SAFE_NOW_PATTERNS = [
        r"\b(safe (now|here)|no danger|mother is with me|friend is here|all fine now|in safe room)\b",
        r"(இப்போது பாதுகாப்பாக|ஆபத்து இல்லை|அம்மா கூட இருக்கிறார்|நண்பர் இருக்கிறார்)",
        r"(सुरक्षित हूँ|अब कोई खतरा नहीं|माताजी साथ हैं|दोस्त पास है)",
    ]

    # Location indicator patterns
    LOCATION_PATTERNS = [
        r"\b(in|from|at)\s+([A-Z][a-z]+|[A-Za-z]+(?:\s+[A-Za-z]+)?)\b",
        r"(சென்னை|மதுரை|கோவை|திருச்சி|சேலம்|பெங்களூர்|தில்லி|மும்பை)",
        r"(चेन्नई|दिल्ली|मुंबई|जयपुर|भोपाल|लखनऊ|कोलकाता|बेंगलुरु)",
    ]

    @classmethod
    def extract_caller_intent(cls, text: str) -> Dict[str, bool]:
        """Detects high-priority caller conversational intents deterministically."""
        clean = text.lower().strip()
        intents = {
            "requests_human": False,
            "refuses_question": False,
            "requests_pause": False,
            "affirms_danger": False,
            "affirms_safe": False,
        }

        for pat in cls.HUMAN_REQUEST_PATTERNS:
            if re.search(pat, clean, re.IGNORECASE):
                intents["requests_human"] = True
                break

        for pat in cls.REFUSAL_PATTERNS:
            if re.search(pat, clean, re.IGNORECASE):
                intents["refuses_question"] = True
                break

        for pat in cls.PAUSE_PATTERNS:
            if re.search(pat, clean, re.IGNORECASE):
                intents["requests_pause"] = True
                break

        for pat in cls.DANGER_AFFIRM_PATTERNS:
            if re.search(pat, clean, re.IGNORECASE):
                intents["affirms_danger"] = True
                break

        for pat in cls.SAFE_NOW_PATTERNS:
            if re.search(pat, clean, re.IGNORECASE):
                intents["affirms_safe"] = True
                break

        return intents

    @classmethod
    def extract_facts_from_turn(
        cls,
        text: str,
        turn_id: str,
        turn_index: int,
        existing_facts: Dict[str, ConversationFact],
    ) -> Tuple[List[ConversationFact], bool]:
        """Extracts new conversation facts from turn and detects contradictions."""
        new_facts: List[ConversationFact] = []
        contradiction_detected = False
        now_iso = datetime.now(timezone.utc).isoformat()
        intents = cls.extract_caller_intent(text)

        # 1. Immediate danger fact
        if intents["affirms_danger"]:
            # Check contradiction: was previously safe_now = True?
            if "safe_now" in existing_facts and existing_facts["safe_now"].value is True:
                existing_facts["safe_now"].superseded = True
                contradiction_detected = True
            new_facts.append(
                ConversationFact(
                    key="immediate_danger",
                    value=True,
                    source="caller_statement",
                    source_turn_id=turn_id,
                    confidence=0.95,
                    priority=FactPriority.CRITICAL,
                    observed_at=now_iso,
                )
            )

        elif intents["affirms_safe"]:
            # Check contradiction: was previously immediate_danger = True?
            if "immediate_danger" in existing_facts and existing_facts["immediate_danger"].value is True:
                existing_facts["immediate_danger"].superseded = True
                contradiction_detected = True
            new_facts.append(
                ConversationFact(
                    key="safe_now",
                    value=True,
                    source="caller_statement",
                    source_turn_id=turn_id,
                    confidence=0.90,
                    priority=FactPriority.CRITICAL,
                    observed_at=now_iso,
                )
            )

        # 2. Refusal tracking
        if intents["refuses_question"]:
            new_facts.append(
                ConversationFact(
                    key="caller_refusal",
                    value=True,
                    source="caller_statement",
                    source_turn_id=turn_id,
                    confidence=1.0,
                    priority=FactPriority.IMPORTANT,
                    observed_at=now_iso,
                )
            )

        # 3. Human request tracking
        if intents["requests_human"]:
            new_facts.append(
                ConversationFact(
                    key="requests_human",
                    value=True,
                    source="caller_statement",
                    source_turn_id=turn_id,
                    confidence=1.0,
                    priority=FactPriority.CRITICAL,
                    observed_at=now_iso,
                )
            )

        # 4. Location extraction (simple heuristics)
        for pat in cls.LOCATION_PATTERNS:
            m = re.search(pat, text, re.IGNORECASE)
            if m:
                loc_val = m.group(2) if m.lastindex and m.lastindex >= 2 else m.group(0)
                if len(loc_val.strip()) > 2 and loc_val.lower() not in ("danger", "room", "phone", "here"):
                    new_facts.append(
                        ConversationFact(
                            key="location",
                            value=loc_val.strip(),
                            source="caller_statement",
                            source_turn_id=turn_id,
                            confidence=0.85,
                            priority=FactPriority.IMPORTANT,
                            observed_at=now_iso,
                        )
                    )
                    break

        return new_facts, contradiction_detected
