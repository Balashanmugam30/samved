import pytest
from app.core.errors import AppException
from app.core.telephony_state import CallState, CallStateMachine


def test_valid_call_state_lifecycle():
    sm = CallStateMachine("call-test-01")
    assert sm.current_state == CallState.NEW
    assert sm.is_active is True
    assert sm.is_streaming is False

    sm.transition_to(CallState.RINGING, reason="phone_ringing")
    assert sm.current_state == CallState.RINGING

    sm.transition_to(CallState.CONNECTING, reason="exotel_handshake")
    assert sm.current_state == CallState.CONNECTING

    sm.transition_to(CallState.CONNECTED, reason="call_answered")
    assert sm.current_state == CallState.CONNECTED

    sm.transition_to(CallState.STREAMING, reason="audio_stream_active")
    assert sm.current_state == CallState.STREAMING
    assert sm.is_streaming is True

    sm.transition_to(CallState.ENDING, reason="caller_hanging_up")
    assert sm.current_state == CallState.ENDING

    sm.transition_to(CallState.ENDED, reason="normal_hangup")
    assert sm.current_state == CallState.ENDED
    assert sm.is_active is False
    assert sm.is_streaming is False
    assert sm.ended_at is not None
    assert sm.disconnect_reason == "normal_hangup"


def test_invalid_state_transition_raises_app_exception():
    sm = CallStateMachine("call-test-02")
    assert sm.current_state == CallState.NEW

    # NEW cannot jump straight to STREAMING
    with pytest.raises(AppException) as exc_info:
        sm.transition_to(CallState.STREAMING)

    assert exc_info.value.code == "INVALID_STATE_TRANSITION"
    assert "call-test-02" in exc_info.value.message


def test_transition_to_failed():
    sm = CallStateMachine("call-test-03")
    sm.transition_to(CallState.FAILED, reason="provider_network_error")
    assert sm.current_state == CallState.FAILED
    assert sm.is_active is False
    assert sm.disconnect_reason == "provider_network_error"


def test_terminal_state_cannot_transition():
    sm = CallStateMachine("call-test-04")
    sm.transition_to(CallState.RINGING)
    sm.transition_to(CallState.ENDED, reason="busy")

    with pytest.raises(AppException):
        sm.transition_to(CallState.CONNECTING)
