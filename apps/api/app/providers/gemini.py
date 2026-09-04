import json
import logging
import re
from typing import Any, Dict, List, Optional
import httpx

from app.core.config import get_settings
from app.prompts.loader import load_system_prompt
from app.schemas.conversation import ConversationalResponse
from app.schemas.languages import LanguageCode

logger = logging.getLogger("samved.providers.gemini")

FALLBACK_RESPONSES: Dict[str, ConversationalResponse] = {
    "ta-IN": ConversationalResponse(
        response_text="வணக்கம், நான் உங்கள் குரலைக் கேட்கிறேன். நீங்கள் இப்போது பாதுகாப்பாக இருக்கிறீர்களா?",
        detected_intent="RECOVERY_FALLBACK",
        conversation_state="RECOVERY",
        next_action="CONTINUE",
        language="ta-IN",
        confidence=0.5,
    ),
    "hi-IN": ConversationalResponse(
        response_text="नमस्ते, मैं आपकी बात सुन रहा हूँ। क्या आप इस समय सुरक्षित हैं?",
        detected_intent="RECOVERY_FALLBACK",
        conversation_state="RECOVERY",
        next_action="CONTINUE",
        language="hi-IN",
        confidence=0.5,
    ),
    "en-IN": ConversationalResponse(
        response_text="Hello, I am listening to you. Are you in a safe place right now?",
        detected_intent="RECOVERY_FALLBACK",
        conversation_state="RECOVERY",
        next_action="CONTINUE",
        language="en-IN",
        confidence=0.5,
    ),
}


def sanitize_voice_response(text: str, max_words: int = 35) -> str:
    """Sanitizes text for speech synthesis: strips markdown, enforces concise phone length."""
    # Remove markdown asterisks, hashes, backticks, brackets
    cleaned = re.sub(r"[*#`_\[\]>]", "", text)
    # Collapse whitespace
    cleaned = re.sub(r"\s+", " ", cleaned).strip()

    words = cleaned.split()
    if len(words) > max_words:
        truncated = " ".join(words[:max_words])
        # Find last sentence terminal
        match = re.search(r"([.?!।|])", truncated)
        if match:
            last_idx = max(truncated.rfind("."), truncated.rfind("?"), truncated.rfind("!"), truncated.rfind("।"))
            if last_idx > 10:
                return truncated[:last_idx + 1].strip()
        return truncated + "."
    return cleaned


_UNSET = object()


class GeminiLLMProvider:
    """Production provider for Google Gemini conversational intelligence."""

    def __init__(
        self,
        api_key: Any = _UNSET,
        model: str = "gemini-2.5-flash",
        timeout_seconds: float = 4.0,
    ):
        settings = get_settings()
        self.api_key = settings.GEMINI_API_KEY if api_key is _UNSET else (api_key or "")
        self.model = model
        self.timeout_seconds = timeout_seconds
        self.endpoint = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent"

    @property
    def is_configured(self) -> bool:
        return bool(self.api_key and len(self.api_key.strip()) > 8)

    async def generate_response(
        self,
        system_prompt: str,
        messages: List[Dict[str, str]],
        temperature: float = 0.2,
    ) -> str:
        structured = await self.generate_conversational_response(messages)
        return structured.response_text

    async def generate_conversational_response(
        self,
        messages: List[Dict[str, str]],
        language: str = "en-IN",
    ) -> ConversationalResponse:
        """Generates structured conversational turn response conforming to ConversationalResponse schema."""
        fallback = FALLBACK_RESPONSES.get(language, FALLBACK_RESPONSES["en-IN"])

        if not self.is_configured:
            logger.warning("Gemini API key unconfigured; using safe fallback response.")
            return fallback

        system_instruction = load_system_prompt()

        # Format contents for Gemini API
        contents = []
        for msg in messages:
            role = "model" if msg.get("role") in ("assistant", "model", "agent") else "user"
            contents.append({
                "role": role,
                "parts": [{"text": msg.get("content", "")}],
            })

        # Structured JSON schema instructions
        json_instruction = (
            "\nYou must respond strictly with a valid JSON object with the following fields:\n"
            "{\n"
            '  "response_text": "Spoken 1-2 sentence response without markdown",\n'
            '  "detected_intent": "Intent label (e.g. INQUIRY, REPORTING_VIOLENCE, DISTRESS)",\n'
            '  "conversation_state": "Dialogue state (e.g. GREETING, CLARIFYING, SAFETY_CHECK)",\n'
            '  "next_action": "CONTINUE | CLARIFY | SAFETY_HOOK | END_CALL",\n'
            '  "language": "Detected response language code (ta-IN, hi-IN, or en-IN)",\n'
            '  "confidence": 0.95,\n'
            '  "safety_flag": false\n'
            "}"
        )

        payload = {
            "system_instruction": {
                "parts": [{"text": system_instruction + json_instruction}]
            },
            "contents": contents,
            "generationConfig": {
                "temperature": 0.2,
                "response_mime_type": "application/json",
            },
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                resp = await client.post(
                    f"{self.endpoint}?key={self.api_key}",
                    json=payload,
                    headers={"Content-Type": "application/json"},
                )
                if resp.status_code == 200:
                    data = resp.json()
                    candidates = data.get("candidates", [])
                    if candidates:
                        parts = candidates[0].get("content", {}).get("parts", [])
                        if parts:
                            raw_json_str = parts[0].get("text", "")
                            parsed = json.loads(raw_json_str)
                            response_text = sanitize_voice_response(parsed.get("response_text", ""))
                            return ConversationalResponse(
                                response_text=response_text,
                                detected_intent=parsed.get("detected_intent", "GENERAL_INQUIRY"),
                                conversation_state=parsed.get("conversation_state", "ENGAGED"),
                                next_action=parsed.get("next_action", "CONTINUE"),
                                language=parsed.get("language", language),
                                confidence=float(parsed.get("confidence", 0.9)),
                                safety_flag=bool(parsed.get("safety_flag", False)),
                            )
                else:
                    logger.error(f"Gemini API returned status {resp.status_code}: {resp.text}")
        except httpx.TimeoutException:
            logger.warning("Gemini API request timed out; returning fallback.")
        except Exception as e:
            logger.error(f"Error calling Gemini API: {e}")

        return fallback

    async def generate_structured_output(
        self,
        system_prompt: str,
        messages: List[Dict[str, str]],
        schema_model: Any,
    ) -> Dict[str, Any]:
        resp = await self.generate_conversational_response(messages)
        return resp.model_dump()