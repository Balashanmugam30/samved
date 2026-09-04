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