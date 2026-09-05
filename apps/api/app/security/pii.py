"""SAMVED Phase 15: Indian Entity PII Redaction & Privacy Engine.

Provides high-accuracy regex + heuristic PII scrubbing for Indian helpline contexts:
- Aadhaar (12-digit UIDAI identifiers)
- PAN (Permanent Account Number, 10-char alphanumeric)
- Indian Mobile / Telephony (+91, 10 digits starting with 6, 7, 8, 9)
- Email Addresses
- Bank Account Numbers (9-18 digit account sequences preceded by keywords)
- Vehicle Numbers (Indian RC formats)
"""

import re
from typing import Any, Dict, List, Tuple
from app.schemas.events import PIIRedactionResult


# Regex Patterns for Indian Entities
# Aadhaar: 12 digits, optionally spaced or hyphenated into 4-4-4 blocks
AADHAAR_REGEX = re.compile(r"\b([2-9]\d{3})[ -]?(\d{4})[ -]?(\d{4})\b")

# PAN Card: 5 letters (first 3 alphabetic, 4th status, 5th name initial), 4 digits, 1 letter
PAN_REGEX = re.compile(r"\b([A-Z]{5}\d{4}[A-Z])\b", re.IGNORECASE)

# Indian Phone Numbers: +91 optional, prefix 6-9, followed by 9 digits with optional spaces or hyphens
PHONE_REGEX = re.compile(
    r"(?:\+91[\-\s]?)?(?:0)?([6-9]\d{4}[\-\s]?\d{5}|[6-9]\d{2}[\-\s]?\d{3}[\-\s]?\d{4})\b"
)

# Email address
EMAIL_REGEX = re.compile(
    r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"
)

# Indian Vehicle Registration Numbers (e.g. DL 01 AB 1234 or MH-12-DE-1433)
VEHICLE_REGEX = re.compile(
    r"\b([A-Z]{2}[\s-]?[0-9]{1,2}[\s-]?[A-Z]{1,3}[\s-]?[0-9]{4})\b",
    re.IGNORECASE,
)

# Bank Account Numbers: 9 to 18 digits preceded by keywords like 'account', 'a/c', 'acc'
BANK_ACC_REGEX = re.compile(
    r"(?i)\b(?:ac(?:count)?(?:\s*no\.?|\s*number)?|a/c)\s*[:#-]?\s*(\d{9,18})\b"
)


class PIIScrubber:
    """Core PII scrubbing engine for text, structured payloads, and log streams."""

    @staticmethod
    def redact_text(text: str) -> PIIRedactionResult:
        """Scrub Indian PII from input text and return structured redaction result."""
        if not text or not isinstance(text, str):
            return PIIRedactionResult(scrubbed_text=text or "", redactions_count=0, redaction_types=[], has_pii=False)

        scrubbed = text
        redactions_count = 0
        detected_types: List[str] = []

        # 1. Aadhaar Redaction (Mask first 8 digits, retain last 4 for reference verification if needed)
        def _mask_aadhaar(match: re.Match) -> str:
            nonlocal redactions_count
            redactions_count += 1
            if "AADHAAR" not in detected_types:
                detected_types.append("AADHAAR")
            last4 = match.group(3)
            return f"[REDACTED_AADHAAR:XXXX-XXXX-{last4}]"

        scrubbed = AADHAAR_REGEX.sub(_mask_aadhaar, scrubbed)

        # 2. PAN Card Redaction
        def _mask_pan(match: re.Match) -> str:
            nonlocal redactions_count
            redactions_count += 1
            if "PAN" not in detected_types:
                detected_types.append("PAN")
            pan_val = match.group(1).upper()
            return f"[REDACTED_PAN:{pan_val[:2]}XXXXX{pan_val[-1]}]"

        scrubbed = PAN_REGEX.sub(_mask_pan, scrubbed)

        # 3. Bank Account Redaction
        def _mask_bank(match: re.Match) -> str:
            nonlocal redactions_count
            redactions_count += 1
            if "BANK_ACCOUNT" not in detected_types:
                detected_types.append("BANK_ACCOUNT")
            acc = match.group(1)
            return f"A/C [REDACTED_ACCOUNT:XXXX{acc[-4:]}]"

        scrubbed = BANK_ACC_REGEX.sub(_mask_bank, scrubbed)

        # 4. Email Redaction
        def _mask_email(match: re.Match) -> str:
            nonlocal redactions_count
            redactions_count += 1
            if "EMAIL" not in detected_types:
                detected_types.append("EMAIL")
            return "[REDACTED_EMAIL]"

        scrubbed = EMAIL_REGEX.sub(_mask_email, scrubbed)

        # 5. Vehicle Number Redaction
        def _mask_vehicle(match: re.Match) -> str:
            nonlocal redactions_count
            redactions_count += 1
            if "VEHICLE" not in detected_types:
                detected_types.append("VEHICLE")
            return "[REDACTED_VEHICLE]"

        scrubbed = VEHICLE_REGEX.sub(_mask_vehicle, scrubbed)

        # 6. Phone Number Redaction
        def _mask_phone(match: re.Match) -> str:
            nonlocal redactions_count
            # Don't mask if it's part of an already redacted token
            span_str = match.group(0)
            if "REDACTED" in span_str:
                return span_str
            redactions_count += 1
            if "PHONE" not in detected_types:
                detected_types.append("PHONE")
            clean_digits = re.sub(r"\D", "", span_str)
            last4 = clean_digits[-4:] if len(clean_digits) >= 4 else "XXXX"
            return f"[REDACTED_PHONE:+91-XXXXX-{last4}]"

        scrubbed = PHONE_REGEX.sub(_mask_phone, scrubbed)

        return PIIRedactionResult(
            scrubbed_text=scrubbed,
            redactions_count=redactions_count,
            redaction_types=detected_types,
            has_pii=redactions_count > 0,
        )

    @classmethod
    def scrub_dict(cls, data: Any) -> Any:
        """Recursively scrub strings within dictionaries, lists, and nested objects."""
        if isinstance(data, str):
            return cls.redact_text(data).scrubbed_text
        if isinstance(data, dict):
            return {k: cls.scrub_dict(v) for k, v in data.items()}
        if isinstance(data, list):
            return [cls.scrub_dict(item) for item in data]
        return data


def redact_pii(text: str) -> PIIRedactionResult:
    """Convenience helper for PII redaction."""
    return PIIScrubber.redact_text(text)


def scrub_dict_pii(data: Any) -> Any:
    """Convenience helper for recursive dictionary PII redaction."""
    return PIIScrubber.scrub_dict(data)
