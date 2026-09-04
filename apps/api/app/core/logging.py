import json
import logging
import sys
from datetime import datetime, timezone
from typing import Any, Dict, Optional


class JSONLogFormatter(logging.Formatter):
    """Structured JSON formatter adhering to SAMVED security and privacy standards."""

    SENSITIVE_KEYS = {
        "authorization",
        "api_key",
        "secret",
        "password",
        "token",
        "access_token",
        "caller_number",
        "phone_number",
        "raw_audio",
    }

    def format(self, record: logging.LogRecord) -> str:
        log_obj: Dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "service": "samved-api",
        }

        # Contextual metadata if attached to record
        if hasattr(record, "request_id"):
            log_obj["request_id"] = record.request_id
        if hasattr(record, "session_id"):
            log_obj["session_id"] = record.session_id
        if hasattr(record, "call_id"):
            log_obj["call_id"] = record.call_id
        if hasattr(record, "extra_data") and isinstance(record.extra_data, dict):
            # Scrub sensitive keys
            clean_extra = {}
            for k, v in record.extra_data.items():
                if any(s in k.lower() for s in self.SENSITIVE_KEYS):
                    clean_extra[k] = "[REDACTED]"
                else:
                    clean_extra[k] = v
            log_obj["data"] = clean_extra

        if record.exc_info:
            log_obj["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_obj)


def setup_logging(log_level: str = "INFO", structured: bool = True) -> logging.Logger:
    logger = logging.getLogger("samved")
    logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))
    logger.handlers.clear()

    handler = logging.StreamHandler(sys.stdout)
    if structured:
        handler.setFormatter(JSONLogFormatter())
    else:
        handler.setFormatter(
            logging.Formatter("[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s")
        )
    logger.addHandler(handler)
    return logger
