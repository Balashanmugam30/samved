# Google Gemini Conversational Intelligence Integration

## 1. Overview
SAMVED uses **Google Gemini** (`gemini-2.5-flash`) as its real-time conversational reasoning engine. Gemini evaluates incoming victim transcripts, maintains dialogue context, flags immediate physical safety concerns, and crafts short, empathetic spoken responses tailored for telephone delivery.

---

## 2. Centralized Prompt Architecture
Prompts are versioned and stored as modular markdown documents under `apps/api/app/prompts/v1/`:
- `base.md`: Persona definition for NHAA 14566, strict 1-2 sentence spoken length rules, and phone etiquette.
- `safety.md`: Imminent danger detection, self-harm protocol, location verification, and `safety_flag` generation.
- `languages.md`: Rules for Tamil, Hindi, and Indian English phrasing and code-switching handling.

All prompts are compiled into a unified system instruction by `apps/api/app/prompts/loader.py`.

---

## 3. Structured JSON Turn Schema
To ensure reliable parsing and avoid free-form hallucination, Gemini responds with a strict JSON schema:

```json
{
  "response_text": "Spoken 1-2 sentence response without markdown formatting.",
  "detected_intent": "Intent label (e.g., GREETING_ACK, IMMEDIATE_SAFETY_CHECK, INQUIRY_DE_ADDICTION)",
  "conversation_state": "Dialogue state (e.g., ENGAGED, CLARIFYING, EMERGENCY_SUPPORT)",
  "next_action": "CONTINUE | CLARIFY | SAFETY_HOOK | END_CALL",
  "language": "Detected response language code (ta-IN, hi-IN, en-IN)",
  "confidence": 0.95,
  "safety_flag": false
}
```

### 3.1 Spoken Audio Text Sanitization
Helpline speech synthesis cannot pronounce markdown syntax, asterisks, bullet points, or overly long paragraphs. `sanitize_voice_response()` enforces:
1. Stripping markdown formatting (`*`, `#`, `_`, `[]`, `>`).
2. Collapsing whitespace.
3. Enforcing a strict word budget ($\le 35$ words) ending at natural sentence terminals (`.`, `?`, `!`, `।`).

---

## 4. Latency Budget & SLA
To provide a natural telephone conversation, SAMVED targets an end-to-end turn turnaround under **800 ms**:

| Stage | Target Budget | Monitored Event |
| :--- | :--- | :--- |
| STT Final Transcript | $\le 200\text{ ms}$ | `TRANSCRIPT_FINAL` |
| Gemini 2.5 Flash Reasoning | $\le 400\text{ ms}$ | `AI_RESPONSE_STARTED` |
| TTS Audio First Frame | $\le 200\text{ ms}$ | `TTS_STARTED` |
| **Total Round-Trip Turn** | **$\le 800\text{ ms}$** | `TURN_LATENCY` |

---

## 5. Unconfigured & Fallback Behavior
When running without live `GEMINI_API_KEY`:
- In `DEV` and `SIMULATION` mode, `MockLLMProvider` generates structured conversational turns in Tamil, Hindi, and English.
- In `LIVE` mode, `GeminiLLMProvider` safely falls back to pre-compiled crisis acknowledgments in the caller's language without crashing the active phone call.
