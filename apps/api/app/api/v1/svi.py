import logging
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from app.schemas.svi import (
    SVIAssessment,
    SVIEvaluationRequest,
    SVIHistoryResponse,
)
from app.services.svi_engine import svi_engine
from app.realtime.session_manager import telephony_session_manager

logger = logging.getLogger("samved.api.svi")

router = APIRouter(prefix="/svi", tags=["SVI"])


@router.post("/evaluate", response_model=SVIAssessment)
async def evaluate_svi(req: SVIEvaluationRequest):
    """
    Evaluates turns and safety signals deterministically to compute the Stress Vulnerability Index (SVI).
    Sub-5ms, offline execution, 100% reproducible.
    """
    turns_data = [
        {
            "speaker": t.speaker,
            "text": t.text,
            "language": t.language,
        }
        for t in req.turns
    ]
    assessment = svi_engine.evaluate_session(
        call_id=req.call_id or "eval-call",
        session_id=req.session_id or "eval-session",
        turns=turns_data,
        safety_signals=req.safety_signals,
        previous_score=req.previous_score,
        turn_index=req.turn_index,
    )
    return assessment


@router.get("/status")
async def get_svi_status():
    """Returns the operational status, version, and ethical boundaries of the SVI Engine."""
    return {
        "status": "ready",
        "engine_version": svi_engine.version,
        "deterministic": True,
        "llm_independent": True,
        "latency_target": "< 5ms",
        "acoustic_evidence_available": False,
        "acoustic_evidence_note": "Acoustic evidence: Not available in current phase (Phase 6 deferred)",
        "disclaimer": "Operational Prototype Priority Indicator — NOT a clinical, medical, or diagnostic score",
        "bands": svi_engine.config.get("bands", {}),
    }


@router.get("/rules")
async def get_svi_rules():
    """Returns the loaded SVI rules, category weights, and recency multipliers."""
    return {
        "version": svi_engine.version,
        "categories": svi_engine.config.get("categories", {}),
        "recency_multipliers": svi_engine.config.get("recency_multipliers", {}),
        "thresholds": svi_engine.config.get("thresholds", {}),
        "trend_threshold": svi_engine.config.get("trend_threshold", 5),
        "disclaimer": "Operational Prototype Priority Indicator — NOT a clinical, medical, or diagnostic score",
    }


@router.get("/calls/{call_id}")
async def get_call_svi(call_id: str):
    """Returns latest SVI assessment for an active or completed call."""
    svi_data = await telephony_session_manager.get_call_svi(call_id)
    if not svi_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"SVI assessment for call '{call_id}' not found",
        )
    return svi_data


@router.get("/calls/{call_id}/history", response_model=SVIHistoryResponse)
async def get_call_svi_history(call_id: str):
    """Returns turn-by-turn SVI assessment history for an active or completed call."""
    history = await telephony_session_manager.get_call_svi_history(call_id)
    if history is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Call '{call_id}' not found in active or recent sessions",
        )

    # Reconstruct SVIAssessment models
    assessments: List[SVIAssessment] = []
    for item in history:
        if isinstance(item, SVIAssessment):
            assessments.append(item)
        elif isinstance(item, dict):
            assessments.append(SVIAssessment.model_validate(item))

    sess = await telephony_session_manager.get_by_call_id(call_id)
    session_id = sess.session_id if sess else "unknown"

    latest = assessments[-1] if assessments else None

    return SVIHistoryResponse(
        call_id=call_id,
        session_id=session_id,
        total_assessments=len(assessments),
        assessments=assessments,
        latest_assessment=latest,
    )
