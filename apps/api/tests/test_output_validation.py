"""Tests for OutputValidator in SAMVED Phase 9."""

import pytest
from app.orchestration.models import AgentRequest, AgentResponse, AgentStatus
from app.orchestration.validation import OutputValidator


def test_validator_identifier_mismatch():
    validator = OutputValidator()
    req = AgentRequest(call_id="call-actual", turn_id="turn-actual", task_type="test")
    resp = AgentResponse(
        request_id=req.request_id,
        call_id="call-wrong",
        turn_id="turn-actual",
        agent_name="test_agent",
        status=AgentStatus.SUCCESS,
    )
    validated = validator.validate(req, resp)
    assert validated.status == AgentStatus.FAILED
    assert any("Call ID mismatch" in w for w in validated.warnings)


def test_validator_prohibited_claims_sanitized():
    validator = OutputValidator()
    req = AgentRequest(call_id="call-1", turn_id="turn-1", task_type="test")
    resp = AgentResponse(
        request_id=req.request_id,
        call_id="call-1",
        turn_id="turn-1",
        agent_name="conversation_context_agent",
        status=AgentStatus.SUCCESS,
        result={"assessment": "We provide a clinical diagnosis of PTSD and police dispatched immediately"},
    )
    validated = validator.validate(req, resp)
    assert "[REDACTED_UNAUTHORIZED_CLAIM]" in validated.result["assessment"]
    assert any("Sanitized prohibited claim pattern" in w for w in validated.warnings)


def test_validator_safety_immutability():
    validator = OutputValidator()
    req = AgentRequest(call_id="call-1", turn_id="turn-1", task_type="test")
    # Advisory LLM agent trying to assert authoritative safety
    resp = AgentResponse(
        request_id=req.request_id,
        call_id="call-1",
        turn_id="turn-1",
        agent_name="conversation_context_agent",
        status=AgentStatus.SUCCESS,
        result={"safety_state": "SAFE", "is_authoritative": True},
    )
    validated = validator.validate(req, resp)
    assert "is_authoritative" not in validated.result
    assert any("Stripped unauthorized is_authoritative" in w for w in validated.warnings)
