"""SAMVED Phase 15: Adaptive Rate Limiting & Abuse Prevention Engine.

Provides thread-safe, sliding-window rate limiting for REST endpoints, WebSocket connections,
and external telephony webhook ingresses.
"""

import threading
import time
from collections import defaultdict, deque
from typing import Dict, Optional, Tuple
from fastapi import HTTPException, Request, status

from app.security.models import RateLimitResult


class RateLimiter:
    """In-memory sliding window rate limiter with burst allowance and temporary IP blocking."""

    def __init__(self):
        self._lock = threading.Lock()
        # key -> deque of timestamps (seconds)
        self._windows: Dict[str, deque[float]] = defaultdict(deque)
        # key -> blocked_until timestamp (seconds)
        self._blocked_until: Dict[str, float] = {}
        # key -> strike count
        self._strikes: Dict[str, int] = defaultdict(int)

    def check(
        self,
        key: str,
        limit: int = 60,
        window_seconds: int = 60,
        burst_allowance: int = 0,
        client_ip: Optional[str] = None,
    ) -> RateLimitResult:
        """Check if request for given key is within quota using sliding window."""
        now = time.time()
        effective_limit = limit + burst_allowance

        with self._lock:
            # Check if currently blocked due to repeated violations
            blocked_until = self._blocked_until.get(key, 0.0)
            if now < blocked_until:
                retry_after = round(blocked_until - now, 2)
                return RateLimitResult(
                    allowed=False,
                    current_count=effective_limit,
                    limit=limit,
                    window_seconds=window_seconds,
                    retry_after_seconds=retry_after,
                    client_ip=client_ip,
                )

            # Evict timestamps outside current window
            window_deq = self._windows[key]
            cutoff = now - window_seconds
            while window_deq and window_deq[0] <= cutoff:
                window_deq.popleft()

            current_count = len(window_deq)

            if current_count >= effective_limit:
                # Violating limit
                self._strikes[key] += 1
                strikes = self._strikes[key]

                # Progressive block if repeatedly hitting limit
                block_duration = 0.0
                if strikes >= 5:
                    block_duration = 300.0  # 5 minutes block
                elif strikes >= 3:
                    block_duration = 60.0  # 1 minute block

                if block_duration > 0:
                    self._blocked_until[key] = now + block_duration
                    retry_after = block_duration
                else:
                    oldest = window_deq[0]
                    retry_after = max(0.1, round((oldest + window_seconds) - now, 2))

                return RateLimitResult(
                    allowed=False,
                    current_count=current_count,
                    limit=limit,
                    window_seconds=window_seconds,
                    retry_after_seconds=retry_after,
                    client_ip=client_ip,
                )

            # Allowed - record current timestamp
            window_deq.append(now)
            return RateLimitResult(
                allowed=True,
                current_count=current_count + 1,
                limit=limit,
                window_seconds=window_seconds,
                retry_after_seconds=0.0,
                client_ip=client_ip,
            )

    def record_abuse_strike(self, key: str, strikes: int = 1) -> None:
        """Explicitly increment strikes (e.g. malformed payloads, injection attempts)."""
        now = time.time()
        with self._lock:
            self._strikes[key] += strikes
            if self._strikes[key] >= 3:
                self._blocked_until[key] = now + 120.0  # 2 min block

    def is_blocked(self, key: str) -> bool:
        """Check whether a key is currently blocked."""
        now = time.time()
        with self._lock:
            return now < self._blocked_until.get(key, 0.0)

    def reset(self, key: Optional[str] = None) -> None:
        """Reset rate limiting window and strikes for a key or all keys."""
        with self._lock:
            if key:
                self._windows.pop(key, None)
                self._blocked_until.pop(key, None)
                self._strikes.pop(key, None)
            else:
                self._windows.clear()
                self._blocked_until.clear()
                self._strikes.clear()


# Global Singleton Rate Limiter
_global_limiter = RateLimiter()


def get_rate_limiter() -> RateLimiter:
    return _global_limiter


def enforce_rate_limit(
    key: str,
    limit: int = 60,
    window_seconds: int = 60,
    burst_allowance: int = 0,
    client_ip: Optional[str] = None,
) -> RateLimitResult:
    """Enforce rate limit; raises HTTP 429 Too Many Requests if quota is exceeded."""
    res = _global_limiter.check(
        key=key,
        limit=limit,
        window_seconds=window_seconds,
        burst_allowance=burst_allowance,
        client_ip=client_ip,
    )
    if not res.allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Rate limit exceeded: quota is {res.limit} requests per {res.window_seconds}s. Try again in {res.retry_after_seconds}s.",
            headers={"Retry-After": str(int(res.retry_after_seconds) + 1)},
        )
    return res
