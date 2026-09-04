from app.core.config import Settings


def test_default_settings():
    settings = Settings()
    assert settings.APP_NAME == "samved-api"
    assert settings.APP_VERSION == "0.1.0"
    assert settings.APP_MODE == "DEV"
    assert settings.is_dev() is True
    assert settings.is_live() is False
    assert settings.is_simulation() is False


def test_cors_parsing_from_string():
    settings = Settings(CORS_ORIGINS="http://localhost:3000,http://example.com")
    assert "http://localhost:3000" in settings.CORS_ORIGINS
    assert "http://example.com" in settings.CORS_ORIGINS


def test_live_mode_settings():
    settings = Settings(APP_MODE="LIVE")
    assert settings.is_live() is True
    assert settings.is_dev() is False
