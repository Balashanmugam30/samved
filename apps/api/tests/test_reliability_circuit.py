"""SAMVED Phase 16: Circuit Breaker Unit & Reliability Tests."""

import time
import pytest
from app.core.circuit import (
    CircuitBreaker,
    CircuitBreakerOpenException,
    CircuitState,
    get_circuit_breaker,
    list_circuit_breakers,
    reset_all_circuit_breakers,
)


def test_circuit_breaker_initial_state():
    breaker = CircuitBreaker("test-provider", failure_threshold=3, recovery_cooldown_seconds=1.0)
    assert breaker.state == CircuitState.CLOSED
    assert breaker.failure_count == 0
    assert breaker.allow_request() is True


def test_circuit_breaker_trip_to_open():
    breaker = CircuitBreaker("test-failing", failure_threshold=2, recovery_cooldown_seconds=0.5)

    # 1st failure
    breaker.record_failure()
    assert breaker.state == CircuitState.CLOSED
    assert breaker.failure_count == 1
    assert breaker.allow_request() is True

    # 2nd failure triggers trip
    breaker.record_failure()
    assert breaker.state == CircuitState.OPEN
    assert breaker.allow_request() is False


def test_circuit_breaker_call_wrapper():
    breaker = CircuitBreaker("test-wrapper", failure_threshold=2, recovery_cooldown_seconds=1.0)

    def passing_func():
        return "success"

    def failing_func():
        raise ValueError("Provider down")

    assert breaker.call(passing_func) == "success"
    assert breaker.state == CircuitState.CLOSED

    with pytest.raises(ValueError):
        breaker.call(failing_func)
    assert breaker.failure_count == 1

    with pytest.raises(ValueError):
        breaker.call(failing_func)
    assert breaker.state == CircuitState.OPEN

    # Subsequent calls should raise CircuitBreakerOpenException immediately without calling func
    with pytest.raises(CircuitBreakerOpenException):
        breaker.call(passing_func)


def test_circuit_breaker_half_open_recovery():
    breaker = CircuitBreaker("test-recovery", failure_threshold=1, recovery_cooldown_seconds=0.1)

    # Trip breaker
    breaker.record_failure()
    assert breaker.state == CircuitState.OPEN

    # Sleep past cooldown
    time.sleep(0.15)

    # allow_request should transition to HALF_OPEN
    assert breaker.allow_request() is True
    assert breaker.state == CircuitState.HALF_OPEN

    # Successful call resets to CLOSED
    breaker.record_success()
    assert breaker.state == CircuitState.CLOSED
    assert breaker.failure_count == 0


def test_circuit_registry_and_reset_all():
    b1 = get_circuit_breaker("reg-1", failure_threshold=1)
    b2 = get_circuit_breaker("reg-2", failure_threshold=1)

    b1.record_failure()
    b2.record_failure()
    assert b1.state == CircuitState.OPEN
    assert b2.state == CircuitState.OPEN

    circuits = list_circuit_breakers()
    assert len(circuits) >= 2

    reset_all_circuit_breakers()
    assert b1.state == CircuitState.CLOSED
    assert b2.state == CircuitState.CLOSED
