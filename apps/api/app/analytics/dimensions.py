"""
Geographic & Time Dimensions for District Intelligence.
Supports normalized district mapping and Asia/Kolkata reporting boundaries.
"""

from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional
import zoneinfo

from app.analytics.models import District, State

REPORTING_TIMEZONE = "Asia/Kolkata"

# Standardized States
STATES: Dict[str, State] = {
    "TN": State(state_code="TN", state_name="Tamil Nadu", districts=["TN-CHE"]),
    "DL": State(state_code="DL", state_name="Delhi", districts=["DL-CEN"]),
    "MH": State(state_code="MH", state_name="Maharashtra", districts=["MH-MUM"]),
    "KA": State(state_code="KA", state_name="Karnataka", districts=["KA-BLR"]),
    "PY": State(state_code="PY", state_name="Puducherry", districts=["PY-KKL"]),
    "IN": State(state_code="IN", state_name="National / Unknown", districts=["UNKNOWN"]),
}

# Standardized Districts
DISTRICTS: Dict[str, District] = {
    "TN-CHE": District(
        district_code="TN-CHE",
        district_name="Chennai",
        state_code="TN",
        state_name="Tamil Nadu",
        aliases=["chennai", "madras", "chennai city", "tn-che"],
    ),
    "DL-CEN": District(
        district_code="DL-CEN",
        district_name="Central Delhi",
        state_code="DL",
        state_name="Delhi",
        aliases=["central delhi", "new delhi", "delhi", "delhi central", "dl-cen"],
    ),
    "MH-MUM": District(
        district_code="MH-MUM",
        district_name="Mumbai",
        state_code="MH",
        state_name="Maharashtra",
        aliases=["mumbai", "bombay", "mumbai city", "mh-mum"],
    ),
    "KA-BLR": District(
        district_code="KA-BLR",
        district_name="Bengaluru Urban",
        state_code="KA",
        state_name="Karnataka",
        aliases=["bengaluru", "bangalore", "bangalore urban", "ka-blr"],
    ),
    "PY-KKL": District(
        district_code="PY-KKL",
        district_name="Karaikal",
        state_code="PY",
        state_name="Puducherry",
        aliases=["karaikal", "py-kkl"],
    ),
    "UNKNOWN": District(
        district_code="UNKNOWN",
        district_name="Unknown District",
        state_code="IN",
        state_name="National / Unknown",
        aliases=["unknown", "unspecified", "not specified", "null", "none"],
    ),
}

# Inverted alias index for O(1) lookup
_ALIAS_TO_DISTRICT: Dict[str, str] = {}
for code, d in DISTRICTS.items():
    _ALIAS_TO_DISTRICT[code.lower()] = code
    for alias in d.aliases:
        _ALIAS_TO_DISTRICT[alias.lower()] = code


def normalize_district(raw_text: Optional[str]) -> str:
    """
    Deterministically normalizes a raw district / location string to canonical code.
    If empty, unmapped, suspect, or ambiguous, safely defaults to 'UNKNOWN'.
    Never guesses or infers beyond explicit matched tokens.
    """
    if not raw_text:
        return "UNKNOWN"

    cleaned = raw_text.strip().lower()
    # Reject suspect characters for SQL injection, script tags, or path traversal
    if any(char in cleaned for char in ["'", '"', ";", "/", "\\", "..", "--", "*", "=", "<", ">"]):
        return "UNKNOWN"

    if cleaned in _ALIAS_TO_DISTRICT:
        return _ALIAS_TO_DISTRICT[cleaned]

    # Exact alias match
    for alias, code in _ALIAS_TO_DISTRICT.items():
        if cleaned == alias:
            return code

    return "UNKNOWN"


def get_district(district_code: str) -> Optional[District]:
    return DISTRICTS.get(district_code)


def list_districts() -> List[District]:
    return list(DISTRICTS.values())


def list_states() -> List[State]:
    return list(STATES.values())


def get_local_now_ist() -> datetime:
    """Returns the current datetime in Asia/Kolkata timezone."""
    try:
        ist_tz = zoneinfo.ZoneInfo(REPORTING_TIMEZONE)
    except Exception:
        # Fallback to UTC+05:30 if zoneinfo not installed
        ist_tz = timezone(timedelta(hours=5, minutes=30))
    return datetime.now(ist_tz)
