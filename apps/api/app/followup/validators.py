"""Input validators and sanitization guards for SAMVED Follow-up Workflow."""

import html
import re
from typing import Optional

SAFE_WINDOW_PATTERN = re.compile(r"^([01]\d|2[0-3]):[0-5]\d-([01]\d|2[0-3]):[0-5]\d$")


def sanitize_text(text: Optional[str]) -> str:
    """Sanitizes user and operator text inputs, preventing XSS and injection."""
    if not text:
        return ""
    # Strip dangerous HTML entities and trim
    cleaned = html.escape(text.strip())
    return cleaned


def validate_safe_window_format(window_str: Optional[str]) -> bool:
    """Validates HH:MM-HH:MM window format."""
    if not window_str:
        return True
    return bool(SAFE_WINDOW_PATTERN.match(window_str.strip()))


def validate_case_ownership(followup_case_id: str, requested_case_id: str) -> bool:
    """IDOR prevention: ensures followup belongs to the requested case."""
    return followup_case_id == requested_case_id
