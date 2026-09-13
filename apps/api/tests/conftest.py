import os
import pytest

# Explicitly isolate test environment for deterministic DEV/mock unit and contract tests
os.environ["APP_MODE"] = "DEV"
os.environ["APP_ENV"] = "development"
os.environ["DEMO_MODE_ENABLED"] = "true"
os.environ["EXOTEL_ENABLED"] = "false"
os.environ["EXOTEL_VERIFY_SIGNATURE"] = "false"
os.environ["SARVAM_API_KEY"] = ""
os.environ["GEMINI_API_KEY"] = ""
os.environ["EXOTEL_ACCOUNT_SID"] = ""
os.environ["EXOTEL_API_KEY"] = ""
os.environ["EXOTEL_API_TOKEN"] = ""
os.environ["EXOTEL_WEBHOOK_SECRET"] = ""

from app.core.config import get_settings
get_settings.cache_clear()

from fastapi.testclient import TestClient
from app.main import app


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client
