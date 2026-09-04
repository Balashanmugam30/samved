import logging
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from app.schemas.safety import SafetyAssessment, SafetySignal
from app.services.safety_engine import safety_engine
from app.realtime.session_manager import telephony_session_manager

logger = logging.getLogger("samved.api.safety")

router = APIRouter(prefix="/safety", tags=["Safety"])


class SafetyEvaluateRequest(BaseModel):
    utterance_text: str = Field(..., description="The utterance text to evaluate")
    language: str = Field(default="en-IN", description="Language code e.g. en-IN, ta-IN, hi-IN")
    call_id: Optional[str] = Field(default="eval-call", description="Optional call ID")
    session_id: Optional[str] = Field(default="eval-session", description="Optional session ID")
    utterance_id: Optional[str] = Field(default=None, description="Optional utterance ID")
    previously_fired_signals: Optional[List[Dict[str, Any]]] = Field(default=None, description="Previously fired signals in this call")


class SafetyAcknowledgeRequest(BaseModel):
    signal_id: str = Field(..., description="ID of the safety signal to acknowledge")
    acknowledged_by: str = Field(default="operator", description="Identifier of the operator acknowledging the signal")


@router.post("/evaluate", response_model=SafetyAssessment)
async def evaluate_utterance(req: SafetyEvaluateRequest):
    """
    Evaluates an utterance deterministically against loaded safety rules.
    Returns explicit, explainable safety signals and updated safety state.
    """
    if not safety_engine.is_ready:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Safety engine is not initialized or rules failed to load",
        )

    assessment = safety_engine.evaluate_turn(
        utterance_text=req.utterance_text,
        language=req.language,
        call_id=req.call_id or "eval-call",
        session_id=req.session_id or "eval-session",
        utterance_id=req.utterance_id,
        previously_fired_signals=req.previously_fired_signals,
    )
    return assessment


@router.get("/status")
async def get_safety_status():
    """Returns the operational status, version, and rule counts of the Safety Engine."""
    return {
        "status": "ready" if safety_engine.is_ready else "error",
        "engine_version": "v1",
        "rules_loaded_count": len(safety_engine.rules),
        "rule_ids": list(safety_engine.rules.keys()),
        "deterministic": True,
        "llm_independent": True,
        "ethical_boundary": "Safety signals are explainable indicators requiring human review, not automated police dispatch or clinical diagnoses.",
    }


@router.get("/rules")
async def get_safety_rules():
    """Returns the loaded safety rules catalog with triggers, severities, and negative examples."""
    rules_summary = []
    seen = set()
    for rule_id, rule in safety_engine.rules.items():
        rid = rule.get("rule_id", rule_id)
        if rid in seen:
            continue
        seen.add(rid)
        rules_summary.append({
            "rule_id": rid,
            "rule_version": rule.get("rule_version", "v1"),
            "category": rule.get("category"),
            "description": rule.get("description"),
            "default_severity": rule.get("severity", "MODERATE"),
            "requires_human_review": rule.get("requires_human_review", True),
            "supported_languages": list(rule.get("patterns", {}).keys()),
            "negative_examples": rule.get("negative_examples", []),
        })
    return {
        "rules_version": "v1",
        "total_rules": len(rules_summary),
        "rules": rules_summary,
    }


@router.get("/calls/{call_id}")
async def get_call_safety_state(call_id: str):
    """Returns safety state, active signals, and history for an active or completed call."""
    safety_data = await telephony_session_manager.get_call_safety(call_id)
    if not safety_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Call '{call_id}' not found in active or recent sessions",
        )
    return safety_data


@router.post("/calls/{call_id}/acknowledge")
async def acknowledge_call_safety_signal(call_id: str, req: SafetyAcknowledgeRequest):
    """
    Records human-in-the-loop operator acknowledgment for a safety signal on a call.
    Broadcasts SAFETY_SIGNAL_ACKNOWLEDGED event to realtime subscribers.
    """
    updated_signal = await telephony_session_manager.acknowledge_call_signal(
        call_id=call_id,
        signal_id=req.signal_id,
        acknowledged_by=req.acknowledged_by,
    )
    if not updated_signal:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Safety signal '{req.signal_id}' not found on call '{call_id}'",
        )
    return {
        "status": "acknowledged",
        "call_id": call_id,
        "signal": updated_signal,
    }
