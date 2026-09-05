"""SAMVED Phase 16: Circuit Breaker & Fault Resilience Engine.

Provides thread-safe state tracking (CLOSED, OPEN, HALF_OPEN) for external providers
and distributed dependencies to prevent cascading failures and retry storms.
"""

import threading
import time
from enum import Enum
from typing import Dict, List, Optional


class CircuitState(str, Enum):
    CLOSED = "CLOSED"      # Normal operation
    OPEN = "OPEN"          # Tripped; fast-fail requests to protect downstream
    HALF_OPEN = "HALF_OPEN"  # Testing recovery with trial calls


class CircuitBreakerOpenException(Exception):
    """Raised when an operation is attempted on an OPEN circuit breaker."""
    pass


class CircuitBreaker:
    """Thread-safe circuit breaker protecting an external provider or dependency."""

    def __init__(
        self,
        name: str,
        failure_threshold: int = 5,
        recovery_timeout_seconds: float = 30.0,
        recovery_cooldown_seconds: Optional[float] = None,
    ):
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout_seconds = recovery_cooldown_seconds if recovery_cooldown_seconds is not None else recovery_timeout_seconds

        self._lock = threading.Lock()
        self._state: CircuitState = CircuitState.CLOSED
        self._failure_count: int = 0
        self._last_failure_time: float = 0.0
        self._last_state_change: float = time.time()
        self._consecutive_successes: int = 0

    @property
    def failure_count(self) -> int:
        return self._failure_count

    @property
    def state(self) -> CircuitState:
        with self._lock:
            self._evaluate_state()
            return self._state

    def _evaluate_state(self) -> None:
        """Evaluate if OPEN state has expired and should transition to HALF_OPEN."""
        now = time.time()
        if self._state == CircuitState.OPEN:
            if (now - self._last_failure_time) >= self.recovery_timeout_seconds:
                self._state = CircuitState.HALF_OPEN
                self._last_state_change = now
                self._consecutive_successes = 0

    def can_execute(self) -> bool:
        """Check if request is permitted through the circuit."""
        with self._lock:
            self._evaluate_state()
            if self._state == CircuitState.OPEN:
                return False
            return True

    def allow_request(self) -> bool:
        """Alias for can_execute()."""
        return self.can_execute()

    def call(self, func, *args, **kwargs):
        """Execute a callable protected by this circuit breaker."""
        if not self.can_execute():
            raise CircuitBreakerOpenException(f"Circuit breaker '{self.name}' is OPEN. Requests temporarily halted.")
        try:
            result = func(*args, **kwargs)
            self.record_success()
            return result
        except Exception as exc:
            self.record_failure(exc)
            raise exc

    def record_success(self) -> None:
        """Record successful execution."""
        with self._lock:
            if self._state == CircuitState.HALF_OPEN:
                self._consecutive_successes += 1
                if self._consecutive_successes >= 1:
                    self._state = CircuitState.CLOSED
                    self._failure_count = 0
                    self._last_state_change = time.time()
            elif self._state == CircuitState.CLOSED:
                self._failure_count = 0

    def record_failure(self, error: Optional[Exception] = None) -> None:
        """Record failed execution."""
        now = time.time()
        with self._lock:
            self._failure_count += 1
            self._last_failure_time = now

            if self._state in (CircuitState.CLOSED, CircuitState.HALF_OPEN):
                if self._failure_count >= self.failure_threshold or self._state == CircuitState.HALF_OPEN:
                    self._state = CircuitState.OPEN
                    self._last_state_change = now

    def reset(self) -> None:
        """Manually reset the circuit breaker to normal operational state."""
        with self._lock:
            self._state = CircuitState.CLOSED
            self._failure_count = 0
            self._last_failure_time = 0.0
            self._last_state_change = time.time()
            self._consecutive_successes = 0

    def get_status(self) -> dict:
        """Return diagnostic metrics for operational dashboards."""
        with self._lock:
            self._evaluate_state()
            return {
                "name": self.name,
                "state": self._state.value,
                "failure_count": self._failure_count,
                "failure_threshold": self.failure_threshold,
                "last_failure_time": self._last_failure_time,
                "time_since_failure": round(time.time() - self._last_failure_time, 1) if self._last_failure_time > 0 else None,
                "recovery_timeout_seconds": self.recovery_timeout_seconds,
            }


CORE_CIRCUIT_BREAKERS = [
    ("sarvam-stt", 5, 30.0),
    ("sarvam-tts", 5, 30.0),
    ("gemini-llm", 5, 30.0),
    ("exotel-telephony", 5, 30.0),
    ("database", 3, 15.0),
    ("redis", 3, 15.0),
]


class CircuitRegistry:
    """Singleton registry tracking all active system circuit breakers."""

    def __init__(self):
        self._lock = threading.Lock()
        self._breakers: Dict[str, CircuitBreaker] = {}
        for name, thresh, timeout in CORE_CIRCUIT_BREAKERS:
            self._breakers[name] = CircuitBreaker(
                name=name,
                failure_threshold=thresh,
                recovery_timeout_seconds=timeout,
            )

    def get_breaker(
        self,
        name: str,
        failure_threshold: int = 5,
        recovery_timeout_seconds: float = 30.0,
    ) -> CircuitBreaker:
        with self._lock:
            if name not in self._breakers:
                self._breakers[name] = CircuitBreaker(
                    name=name,
                    failure_threshold=failure_threshold,
                    recovery_timeout_seconds=recovery_timeout_seconds,
                )
            return self._breakers[name]

    def list_all(self) -> List[dict]:
        with self._lock:
            return [b.get_status() for b in self._breakers.values()]

    def reset_all(self) -> None:
        with self._lock:
            for b in self._breakers.values():
                b.reset()


_global_registry = CircuitRegistry()


def get_circuit_breaker(
    name: str,
    failure_threshold: int = 5,
    recovery_timeout_seconds: float = 30.0,
) -> CircuitBreaker:
    return _global_registry.get_breaker(
        name=name,
        failure_threshold=failure_threshold,
        recovery_timeout_seconds=recovery_timeout_seconds,
    )


def list_circuit_breakers() -> List[dict]:
    return _global_registry.list_all()


def reset_all_circuit_breakers() -> None:
    _global_registry.reset_all()
