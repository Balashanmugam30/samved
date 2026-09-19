import pytest
from app.prompts.loader import load_system_prompt
from app.providers.gemini import GeminiLLMProvider, sanitize_voice_response
from app.providers.mocks import MockLLMProvider
from app.schemas.conversation import ConversationalResponse


def test_system_prompt_loading():
    prompt = load_system_prompt()
    assert "SAMVED" in prompt
    assert "Tamil" in prompt
    assert "safety_flag" in prompt


def test_sanitize_voice_response():
    raw_markdown = "**Hello!** *Please* stay calm. # Help is on the way."
    cleaned = sanitize_voice_response(raw_markdown)
    assert "*" not in cleaned
    assert "#" not in cleaned
    assert "Hello! Please stay calm." in cleaned


@pytest.mark.asyncio
async def test_mock_llm_tamil_and_safety_detection():
    llm = MockLLMProvider()

    # 1. Normal Tamil greeting
    messages_tamil = [{"role": "user", "content": "Vanakkam, enakku oru kelvi irukku."}]
    resp: ConversationalResponse = await llm.generate_conversational_response(messages_tamil)
    assert resp.language == "ta-IN"
    assert resp.safety_flag is False

    # 2. Safety / threat trigger
    messages_threat = [{"role": "user", "content": "A person is threatening me with a weapon outside."}]
    resp_threat: ConversationalResponse = await llm.generate_conversational_response(messages_threat)
    assert resp_threat.safety_flag is True
    assert resp_threat.next_action == "SAFETY_HOOK"
    assert "safe" in resp_threat.response_text.lower()


@pytest.mark.asyncio
async def test_gemini_fallback_when_unconfigured():
    gemini = GeminiLLMProvider(api_key=None)
    assert gemini.is_configured is False

    fallback = await gemini.generate_conversational_response(
        messages=[{"role": "user", "content": "test"}],
        language="ta-IN",
    )
    assert fallback.language == "ta-IN"
    assert "வணக்கம்" in fallback.response_text


def test_gemini_model_configuration_defaults_and_injection():
    # 1. Default model must be gemini-3.6-flash
    gemini_default = GeminiLLMProvider(api_key=None)
    assert gemini_default.model == "gemini-3.6-flash"
    assert gemini_default.endpoint == (
        "https://generativelanguage.googleapis.com/v1beta/models/gemini-3.6-flash:generateContent"
    )

    # 2. Explicit model injection must be respected
    gemini_custom = GeminiLLMProvider(api_key=None, model="custom-test-model")
    assert gemini_custom.model == "custom-test-model"
    assert gemini_custom.endpoint == (
        "https://generativelanguage.googleapis.com/v1beta/models/custom-test-model:generateContent"
    )


@pytest.mark.asyncio
async def test_gemini_retry_on_503_and_succeed(monkeypatch):
    """Verifies that HTTP 503 triggers retry and subsequent 200 returns valid ConversationalResponse."""
    import json
    import httpx

    async def noop_sleep(s):
        pass

    monkeypatch.setattr("asyncio.sleep", noop_sleep)

    call_count = 0
    valid_payload = {
        "candidates": [
            {
                "content": {
                    "parts": [
                        {
                            "text": json.dumps({
                                "response_text": "I am here with you. Please stay calm.",
                                "detected_intent": "INQUIRY",
                                "conversation_state": "ENGAGED",
                                "next_action": "CONTINUE",
                                "language": "en-IN",
                                "confidence": 0.95,
                                "safety_flag": False,
                            })
                        }
                    ]
                }
            }
        ]
    }

    async def mock_post(self, url, *args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return httpx.Response(503, text='{"error": "high demand"}', request=httpx.Request("POST", url))
        return httpx.Response(200, json=valid_payload, request=httpx.Request("POST", url))

    monkeypatch.setattr(httpx.AsyncClient, "post", mock_post)

    provider = GeminiLLMProvider(api_key="test-dummy-key-minimum-length-satisfied")
    resp = await provider.generate_conversational_response([{"role": "user", "content": "help"}])

    assert call_count == 2
    assert resp.detected_intent == "INQUIRY"
    assert "stay calm" in resp.response_text


@pytest.mark.asyncio
async def test_gemini_retry_on_429_and_succeed(monkeypatch):
    """Verifies that HTTP 429 triggers retry and subsequent 200 returns valid ConversationalResponse."""
    import json
    import httpx

    async def noop_sleep(s):
        pass

    monkeypatch.setattr("asyncio.sleep", noop_sleep)

    call_count = 0
    valid_payload = {
        "candidates": [
            {
                "content": {
                    "parts": [
                        {
                            "text": json.dumps({
                                "response_text": "I hear you. How can I support you?",
                                "detected_intent": "INQUIRY",
                                "conversation_state": "ENGAGED",
                                "next_action": "CONTINUE",
                                "language": "en-IN",
                                "confidence": 0.95,
                                "safety_flag": False,
                            })
                        }
                    ]
                }
            }
        ]
    }

    async def mock_post(self, url, *args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return httpx.Response(429, text='{"error": "rate limit"}', request=httpx.Request("POST", url))
        return httpx.Response(200, json=valid_payload, request=httpx.Request("POST", url))

    monkeypatch.setattr(httpx.AsyncClient, "post", mock_post)

    provider = GeminiLLMProvider(api_key="test-dummy-key-minimum-length-satisfied")
    resp = await provider.generate_conversational_response([{"role": "user", "content": "help"}])

    assert call_count == 2
    assert resp.detected_intent == "INQUIRY"
    assert "support you" in resp.response_text


@pytest.mark.asyncio
async def test_gemini_no_retry_on_404_immediate_fallback(monkeypatch):
    """Verifies that HTTP 404 does NOT retry and immediately returns safe fallback."""
    import httpx

    async def noop_sleep(s):
        pass

    monkeypatch.setattr("asyncio.sleep", noop_sleep)

    call_count = 0

    async def mock_post(self, url, *args, **kwargs):
        nonlocal call_count
        call_count += 1
        return httpx.Response(404, text='{"error": "model not found"}', request=httpx.Request("POST", url))

    monkeypatch.setattr(httpx.AsyncClient, "post", mock_post)

    provider = GeminiLLMProvider(api_key="test-dummy-key-minimum-length-satisfied")
    resp = await provider.generate_conversational_response([{"role": "user", "content": "help"}], language="en-IN")

    assert call_count == 1  # Exactly 1 call; no retries
    assert resp.detected_intent == "RECOVERY_FALLBACK"


@pytest.mark.asyncio
async def test_gemini_no_retry_on_401_403_immediate_fallback(monkeypatch):
    """Verifies that HTTP 401/403 does NOT retry and immediately returns safe fallback."""
    import httpx

    async def noop_sleep(s):
        pass

    monkeypatch.setattr("asyncio.sleep", noop_sleep)

    call_count = 0

    async def mock_post(self, url, *args, **kwargs):
        nonlocal call_count
        call_count += 1
        return httpx.Response(401, text='{"error": "invalid api key"}', request=httpx.Request("POST", url))

    monkeypatch.setattr(httpx.AsyncClient, "post", mock_post)

    provider = GeminiLLMProvider(api_key="test-dummy-key-minimum-length-satisfied")
    resp = await provider.generate_conversational_response([{"role": "user", "content": "help"}], language="en-IN")

    assert call_count == 1  # Exactly 1 call; no retries
    assert resp.detected_intent == "RECOVERY_FALLBACK"


@pytest.mark.asyncio
async def test_gemini_all_retries_exhausted_returns_fallback(monkeypatch):
    """Verifies that after all 3 retries fail with 503, provider returns safe fallback."""
    import httpx

    async def noop_sleep(s):
        pass

    monkeypatch.setattr("asyncio.sleep", noop_sleep)

    call_count = 0

    async def mock_post(self, url, *args, **kwargs):
        nonlocal call_count
        call_count += 1
        return httpx.Response(503, text='{"error": "persistent 503"}', request=httpx.Request("POST", url))

    monkeypatch.setattr(httpx.AsyncClient, "post", mock_post)

    provider = GeminiLLMProvider(api_key="test-dummy-key-minimum-length-satisfied")
    resp = await provider.generate_conversational_response([{"role": "user", "content": "help"}], language="en-IN")

    assert call_count == 3  # Exactly 3 attempts made
    assert resp.detected_intent == "RECOVERY_FALLBACK"