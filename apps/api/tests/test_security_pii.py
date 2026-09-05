"""SAMVED Phase 15: Indian Entity PII Redaction & Privacy Engine Tests.

Verifies accurate masking of Aadhaar, PAN, Indian phone numbers, emails, and bank accounts.
Also verifies log scrubbing via JSONLogFormatter.
"""

import json
import logging
import pytest
from fastapi.testclient import TestClient

from app.core.logging import JSONLogFormatter
from app.main import app
from app.security.pii import PIIScrubber, redact_pii, scrub_dict_pii


@pytest.fixture
def client():
    return TestClient(app)


def test_aadhaar_redaction():
    """Verifies that 12-digit Aadhaar numbers are masked preserving only the last 4 digits."""
    sample = "Caller provided Aadhaar number 2345 6789 0123 for verification."
    res = redact_pii(sample)
    assert res.has_pii is True
    assert "AADHAAR" in res.redaction_types
    assert "[REDACTED_AADHAAR:XXXX-XXXX-0123]" in res.scrubbed_text
    assert "2345 6789 0123" not in res.scrubbed_text

    # Hyphenated variation
    sample_hyphen = "Aadhaar: 9876-5432-1098."
    res2 = redact_pii(sample_hyphen)
    assert "[REDACTED_AADHAAR:XXXX-XXXX-1098]" in res2.scrubbed_text


def test_pan_card_redaction():
    """Verifies that 10-character PAN identifiers are masked."""
    sample = "Income tax PAN submitted is ABCDE1234F by the caller."
    res = redact_pii(sample)
    assert res.has_pii is True
    assert "PAN" in res.redaction_types
    assert "[REDACTED_PAN:ABXXXXXF]" in res.scrubbed_text
    assert "ABCDE1234F" not in res.scrubbed_text


def test_phone_number_redaction():
    """Verifies Indian mobile numbers starting with 6-9 with or without +91 prefix."""
    sample = "Call back at +91 9876543210 or 87654 32109 immediately."
    res = redact_pii(sample)
    assert res.has_pii is True
    assert "PHONE" in res.redaction_types
    assert "[REDACTED_PHONE:+91-XXXXX-3210]" in res.scrubbed_text
    assert "[REDACTED_PHONE:+91-XXXXX-2109]" in res.scrubbed_text


def test_email_redaction():
    """Verifies email addresses are replaced with standard token."""
    sample = "Send confirmation to victim.helpdesk@state.gov.in right away."
    res = redact_pii(sample)
    assert res.has_pii is True
    assert "EMAIL" in res.redaction_types
    assert "[REDACTED_EMAIL]" in res.scrubbed_text


def test_bank_account_redaction():
    """Verifies bank account mentions are masked."""
    sample = "Direct benefit transfer into A/C 12345678901234."
    res = redact_pii(sample)
    assert res.has_pii is True
    assert "BANK_ACCOUNT" in res.redaction_types
    assert "A/C [REDACTED_ACCOUNT:XXXX1234]" in res.scrubbed_text


def test_safe_text_unaltered():
    """Verifies normal operational text and metrics are not falsely scrubbed."""
    clean = "SVI score is 88, priority HIGH, triage category DOMESTIC_VIOLENCE, turn latency 240ms, case CASE-7788."
    res = redact_pii(clean)
    assert res.has_pii is False
    assert res.scrubbed_text == clean


def test_nested_dictionary_scrubbing():
    """Verifies recursive scrubbing across nested dictionaries and lists."""
    data = {
        "caller_profile": {
            "name": "Anonymous",
            "contact": "+91-9876543210",
            "email": "test@example.com",
            "notes": ["Mentioned PAN: BKXPA5543K", "No immediate medical emergency"],
        },
        "score": 92,
    }
    scrubbed = scrub_dict_pii(data)
    assert "[REDACTED_PHONE:+91-XXXXX-3210]" in scrubbed["caller_profile"]["contact"]
    assert "[REDACTED_EMAIL]" in scrubbed["caller_profile"]["email"]
    assert "[REDACTED_PAN:BKXXXXXK]" in scrubbed["caller_profile"]["notes"][0]
    assert scrubbed["score"] == 92


def test_json_log_formatter_scrubs_pii():
    """Verifies that JSONLogFormatter intercepts and redacts PII before output."""
    formatter = JSONLogFormatter()
    record = logging.LogRecord(
        name="samved.test",
        level=logging.INFO,
        pathname="test.py",
        lineno=10,
        msg="Caller Aadhaar is 4567 8901 2345 and phone is +91-9123456789",
        args=(),
        exc_info=None,
    )
    formatted = formatter.format(record)
    parsed = json.loads(formatted)
    assert "4567 8901 2345" not in parsed["message"]
    assert "[REDACTED_AADHAAR:XXXX-XXXX-2345]" in parsed["message"]
    assert "[REDACTED_PHONE:+91-XXXXX-6789]" in parsed["message"]


def test_pii_redact_api_endpoint(client):
    """Verifies POST /v1/security/pii/redact endpoint functionality."""
    payload = {"text": "My phone is 9876543210 and Aadhaar is 5555 6666 7777"}
    res = client.post("/v1/security/pii/redact", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["has_pii"] is True
    assert data["redactions_count"] >= 2
    assert "AADHAAR" in data["redaction_types"]
    assert "PHONE" in data["redaction_types"]
