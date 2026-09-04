import logging
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, status

from app.schemas.acoustic import (
    AcousticAssessment,
    AcousticEvaluationRequest,
    AcousticHistoryResponse,
    AcousticRulesResponse,
    AcousticStatusResponse,
)
from app.services.acoustic_engine import acoustic_engine
from app.realtime.session_manager import telephony_session_manager

logger = logging.getLogger("samved.api.acoustic")

router = APIRouter(prefix="/acoustic", tags=["Acoustic Analysis"])


@router.get("/status", response_model=AcousticStatusResponse)
async def get_acoustic_status():
    """
    Returns the operational status, version, and ethical boundaries of the Acoustic Analysis Engine.
    Emphasizes non-clinical, non-diagnostic operational support constraints.
    """
    return acoustic_engine.get_status()


@router.get("/rules", response_model=AcousticRulesResponse)
async def get_acoustic_rules():
    """
    Returns the loaded acoustic classification rules, detection thresholds, and parameter bounds.
    """
    return acoustic_engine.get_rules()


@router.post("/evaluate", response_model=AcousticAssessment)
async def evaluate_acoustic(req: AcousticEvaluationRequest):
    """
    Evaluates audio frames or synthetic acoustic parameters deterministically.
    Sub-5ms, offline execution, 100% reproducible.
    Used for unit testing, CI pipelines, and operator simulation lab.
    """
    assessment = acoustic_engine.evaluate_synthetic(req)
    return assessment


@router.get("/calls/{call_id}", response_model=AcousticAssessment)
async def get_call_acoustic(call_id: str):
    """
    Returns the latest acoustic assessment for an active or completed call.
    """
    acoustic_data = await telephony_session_manager.get_call_acoustic(call_id)
    if not acoustic_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Acoustic assessment for call '{call_id}' not found",
        )
    if isinstance(acoustic_data, AcousticAssessment):
        return acoustic_data
    return AcousticAssessment.model_validate(acoustic_data)


@router.get("/calls/{call_id}/history", response_model=AcousticHistoryResponse)
async def get_call_acoustic_history(call_id: str):
    """
    Returns the turn-by-turn acoustic assessment history for an active or completed call.
    """
    history = await telephony_session_manager.get_call_acoustic_history(call_id)
    if history is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Call '{call_id}' not found in active or recent sessions",
        )

    assessments: List[AcousticAssessment] = []
    for item in history:
        if isinstance(item, AcousticAssessment):
            assessments.append(item)
        elif isinstance(item, dict):
            try:
                assessments.append(AcousticAssessment.model_validate(item))
            except Exception as e:
                logger.debug(f"Error parsing acoustic assessment history item: {e}")

    session = await telephony_session_manager.get_by_call_id(call_id)
    session_id = session.session_id if session else "completed-session"

    return AcousticHistoryResponse(
        call_id=call_id,
        session_id=session_id,
        assessments_count=len(assessments),
        assessments=assessments,
        engine_version=acoustic_engine.engine_version,
    )
