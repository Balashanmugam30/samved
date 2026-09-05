"""SAMVED Phase 15: Adaptive Rate Limiting & Abuse Prevention Tests.

Tests sliding-window rate tracking, quota exhaustion, progressive blocking, and 429 response formatting.
"""

import time
import pytest
from fastapi.testclient import TestClient
from fastapi import HTTPException

from app.security.rate_limit import RateLimiter, enforce_rate_limit


def test_sliding_window_rate_limiter_allows_under_quota():
    """Verifies that requests within limit and window are allowed."""
    limiter = RateLimiter()
    key = "client-ip-1.2.3.4"

    for i in range(5):
        res = limiter.check(key=key, limit=5, window_seconds=10)
        assert res.allowed is True
        assert res.current_count == i + 1


def test_sliding_window_blocks_over_quota():
    """Verifies that requests exceeding limit are denied with retry_after."""
    limiter = RateLimiter()
    key = "client-flooder"

    # Fill quota of 3 requests
    for _ in range(3):
        res = limiter.check(key=key, limit=3, window_seconds=5)
        assert res.allowed is True

    # 4th request must be blocked
    denied = limiter.check(key=key, limit=3, window_seconds=5)
    assert denied.allowed is False
    assert denied.retry_after_seconds > 0


def test_enforce_rate_limit_raises_http_429():
    """Verifies that enforce_rate_limit raises 429 with Retry-After header."""
    key = "test_endpoint_flood"
    # Exhaust quota
    for _ in range(2):
        enforce_rate_limit(key=key, limit=2, window_seconds=10)

    with pytest.raises(HTTPException) as exc_info:
        enforce_rate_limit(key=key, limit=2, window_seconds=10)

    assert exc_info.value.status_code == 429
    assert "Rate limit exceeded" in exc_info.value.detail
    assert "Retry-After" in exc_info.value.headers


def test_progressive_blocking_on_abuse_strikes():
    """Verifies that deliberate abuse strikes trigger a temporary block."""
    limiter = RateLimiter()
    key = "malicious-actor"

    limiter.record_abuse_strike(key=key, strikes=3)
    assert limiter.is_blocked(key) is True

    # Check must return denied while blocked
    res = limiter.check(key=key, limit=100, window_seconds=60)
    assert res.allowed is False
    assert res.retry_after_seconds > 0
