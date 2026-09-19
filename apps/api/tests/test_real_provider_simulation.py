import pytest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import app
from app.providers.gemini import GeminiLLMProvider
from app.providers.mocks import MockLLMProvider, MockSpeechToTextProvider, MockTextToSpeechProvider
from app.providers.sarvam_stt import SarvamSTTProvider
from app.providers.sarvam_tts import SarvamTTSProvider
from app.realtime.session_manager import TelephonySession, create_session_orchestrator


def _make_dummy_session(session_id: str = "TEST-SESS-1") -> TelephonySession:
    return TelephonySession(
        session_id=session_id,
        call_id="TEST-CALL-1",
        provider_call_id="TEST-PROV-1",
        caller_number="+919876543210",
        provider="simulation",
    )


def test_1_default_real_provider_simulation_is_false():
    """1. Verify default REAL_PROVIDER_SIMULATION is False."""
    settings = Settings()
    assert settings.REAL_PROVIDER_SIMULATION is False
    assert settings.is_real_provider_simulation() is False
    assert settings.EXOTEL_ENABLED is False


def test_2_dev_simulation_false_yields_mock_providers():
    """2. DEV + REAL_PROVIDER_SIMULATION=False -> mock providers."""
    custom_settings = Settings(
        APP_MODE="DEV",
        REAL_PROVIDER_SIMULATION=False,
        SARVAM_API_KEY="sarvam-test-key-12345",
        GEMINI_API_KEY="gemini-test-key-12345",
    )
    with patch("app.realtime.session_manager.get_settings", return_value=custom_settings):
        session = _make_dummy_session()
        orchestrator = create_session_orchestrator(session)
        assert isinstance(orchestrator.stt, MockSpeechToTextProvider)
        assert isinstance(orchestrator.llm, MockLLMProvider)
        assert isinstance(orchestrator.tts, MockTextToSpeechProvider)


def test_3_dev_simulation_true_with_valid_credentials_yields_real_providers():
    """3. DEV + REAL_PROVIDER_SIMULATION=True + valid credentials -> real providers."""
    custom_settings = Settings(
        APP_MODE="DEV",
        REAL_PROVIDER_SIMULATION=True,
        SARVAM_API_KEY="sarvam-test-key-12345",
        GEMINI_API_KEY="gemini-test-key-12345",
    )
    with patch("app.realtime.session_manager.get_settings", return_value=custom_settings):
        session = _make_dummy_session()
        orchestrator = create_session_orchestrator(session)
        assert isinstance(orchestrator.stt, SarvamSTTProvider)
        assert isinstance(orchestrator.llm, GeminiLLMProvider)
        assert isinstance(orchestrator.tts, SarvamTTSProvider)


def test_4_dev_simulation_true_missing_sarvam_yields_mock_fallback():
    """4. DEV + REAL_PROVIDER_SIMULATION=True + missing Sarvam credential -> safe mock fallback."""
    custom_settings = Settings(
        APP_MODE="DEV",
        REAL_PROVIDER_SIMULATION=True,
        SARVAM_API_KEY=None,
        GEMINI_API_KEY="gemini-test-key-12345",
    )
    with patch("app.realtime.session_manager.get_settings", return_value=custom_settings):
        session = _make_dummy_session()
        orchestrator = create_session_orchestrator(session)
        assert isinstance(orchestrator.stt, MockSpeechToTextProvider)
        assert isinstance(orchestrator.llm, MockLLMProvider)
        assert isinstance(orchestrator.tts, MockTextToSpeechProvider)


def test_5_dev_simulation_true_missing_gemini_yields_mock_fallback():
    """5. DEV + REAL_PROVIDER_SIMULATION=True + missing Gemini credential -> safe mock fallback."""
    custom_settings = Settings(
        APP_MODE="DEV",
        REAL_PROVIDER_SIMULATION=True,
        SARVAM_API_KEY="sarvam-test-key-12345",
        GEMINI_API_KEY=None,
    )
    with patch("app.realtime.session_manager.get_settings", return_value=custom_settings):
        session = _make_dummy_session()
        orchestrator = create_session_orchestrator(session)
        assert isinstance(orchestrator.stt, MockSpeechToTextProvider)
        assert isinstance(orchestrator.llm, MockLLMProvider)
        assert isinstance(orchestrator.tts, MockTextToSpeechProvider)


def test_6_live_mode_yields_real_providers_as_before():
    """6. LIVE -> real providers as before."""
    custom_settings = Settings(
        APP_MODE="LIVE",
        REAL_PROVIDER_SIMULATION=False,
        SARVAM_API_KEY="sarvam-test-key-12345",
        GEMINI_API_KEY="gemini-test-key-12345",
    )
    with patch("app.realtime.session_manager.get_settings", return_value=custom_settings):
        session = _make_dummy_session()
        orchestrator = create_session_orchestrator(session)
        assert isinstance(orchestrator.stt, SarvamSTTProvider)
        assert isinstance(orchestrator.llm, GeminiLLMProvider)
        assert isinstance(orchestrator.tts, SarvamTTSProvider)


def test_7_exotel_enabled_remains_false_regardless_of_simulation():
    """7. EXOTEL_ENABLED=false remains false regardless of REAL_PROVIDER_SIMULATION."""
    settings = Settings(
        APP_MODE="DEV",
        REAL_PROVIDER_SIMULATION=True,
        EXOTEL_ENABLED=False,
    )
    assert settings.EXOTEL_ENABLED is False
    assert settings.is_exotel_live_ready() is False


def test_8_doctor_reports_real_provider_simulation_and_safe_to_start_false():
    """8. Doctor reports REAL_PROVIDER_SIMULATION and live_mode_safe_to_start=false."""
    custom_settings = Settings(
        APP_MODE="DEV",
        REAL_PROVIDER_SIMULATION=True,
        EXOTEL_ENABLED=False,
        SARVAM_API_KEY="sarvam-test-key-12345",
        GEMINI_API_KEY="gemini-test-key-12345",
    )
    with patch("app.api.v1.telephony.settings", custom_settings):
        client = TestClient(app)
        response = client.get("/v1/telephony/doctor")
        assert response.status_code == 200
        data = response.json()
        assert data["app_mode"] == "DEV"
        assert data["provider_execution_mode"] == "REAL_PROVIDER_SIMULATION"
        assert data["real_provider_simulation"] is True
        assert data["exotel_enabled"] is False
        assert data["live_mode_safe_to_start"] is False
        assert data["pipeline_status"]["real_provider_simulation_pipeline"] == "READY"


def test_9_readiness_probe_reports_speech_sarvam_and_llm_gemini():
    """9. /ready reports speech=Sarvam, llm=Gemini when REAL_PROVIDER_SIMULATION=True."""
    custom_settings = Settings(
        APP_MODE="DEV",
        REAL_PROVIDER_SIMULATION=True,
        EXOTEL_ENABLED=False,
        SARVAM_API_KEY="sarvam-test-key-12345",
        GEMINI_API_KEY="gemini-test-key-12345",
    )
    with patch("app.api.v1.health.get_settings", return_value=custom_settings):
        client = TestClient(app)
        response = client.get("/ready")
        assert response.status_code == 200
        data = response.json()
        assert data["mode"] == "DEV"
        assert data["ready"] is True
        assert data["dependencies"]["speech"]["provider"] == "Sarvam"
        assert data["dependencies"]["speech"]["status"] == "configured"
        assert data["dependencies"]["llm"]["provider"] == "Gemini"
        assert data["dependencies"]["llm"]["status"] == "configured"


def test_10_simulation_mode_never_invokes_exotel():
    """10. No Exotel API call is initiated by simulation mode."""
    with patch("app.providers.exotel.ExotelTelephonyProvider.initiate_call") as mock_call:
        client = TestClient(app)
        response = client.post(
            "/v1/telephony/simulate",
            json={"caller_phone": "+919876543210", "duration_frames": 2, "frame_interval_ms": 10},
        )
        assert response.status_code == 201
        mock_call.assert_not_called()
