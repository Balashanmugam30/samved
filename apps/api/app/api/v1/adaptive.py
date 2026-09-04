import logging
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from app.adaptive.models import (
    AdaptiveHistoryResponse,
    AdaptivePlanRequest,
    AdaptivePolicyResponse,
    AdaptiveStatusResponse,
    ConversationStrategy,
    OperatorOverride,
)
from app.adaptive.planner import AdaptivePlanner
from app.adaptive.service import adaptive_engine
from app.realtime.session_manager import telephony_session_manager

logger = logging.getLogger("samved.api.adaptive")

router = APIRouter(prefix="/adaptive", tags=["Adaptive Conversation"])


class OverrideRequest(BaseModel):
    action: str
    reason: str
    operator_id: str = "operator_counselor_1"


@router.get("/status", response_model=AdaptiveStatusResponse)
async def get_adaptive_status():
    """
    Returns the operational status, version, and ethical boundaries of the Adaptive Conversation Engine.
    Emphasizes safety precedence, explainability, and non-clinical constraints.
    """
    return adaptive_engine.get_status()


@router.get("/policy", response_model=AdaptivePolicyResponse)
async def get_adaptive_policy():
    """
    Returns the catalog of deterministic conversational actions, priority tiers (P0-P5),
    and reason codes.
    """
    return adaptive_engine.get_policy_catalog()


@router.post("/plan", response_model=ConversationStrategy)
async def plan_conversation_turn(req: AdaptivePlanRequest):
    """
    Deterministically computes the next conversational strategy given known state, facts,
    safety context, SVI score, and acoustic cues.
    Used for unit testing, CI pipelines, and operator simulation lab.
    """
    return AdaptivePlanner.evaluate_request(req)


@router.get("/calls/{call_id}", response_model=ConversationStrategy)
async def get_call_strategy(call_id: str):
    """
    Returns the current active strategy for an active or completed call.
    """
    strat = await telephony_session_manager.get_call_adaptive(call_id)
    if not strat:
        # Check engine directly
        strat_obj = adaptive_engine.get_latest_strategy(call_id)
        if strat_obj:
            return strat_obj
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Adaptive strategy for call '{call_id}' not found",
        )
    if isinstance(strat, ConversationStrategy):
        return strat
    return ConversationStrategy(**strat)


@router.get("/calls/{call_id}/history", response_model=AdaptiveHistoryResponse)
async def get_call_strategy_history(call_id: str):
    """
    Returns the turn-by-turn strategy progression and audit history for a call.
    """
    hist = await telephony_session_manager.get_call_adaptive_history(call_id)
    override = adaptive_engine.get_operator_override(call_id)
    if hist is None:
        # Fallback to engine
        engine_resp = adaptive_engine.get_call_history(call_id)
        if engine_resp.total_strategies == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Adaptive history for call '{call_id}' not found",
            )
        return engine_resp

    parsed_strategies = [
        ConversationStrategy(**s) if isinstance(s, dict) else s for s in hist
    ]
    return AdaptiveHistoryResponse(
        call_id=call_id,
        total_strategies=len(parsed_strategies),
        strategies=parsed_strategies,
        active_override=override,
    )


@router.post("/calls/{call_id}/override", response_model=OperatorOverride)
async def apply_operator_override(call_id: str, req: OverrideRequest):
    """
    Applies a human operator override to an active call.
    Supports force human handoff, pause adaptive questions, resume, safety check request.
    """
    res = await telephony_session_manager.apply_call_operator_override(
        call_id=call_id,
        action=req.action,
        reason=req.reason,
        operator_id=req.operator_id,
    )
    if not res:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Could not apply override '{req.action}' for call '{call_id}'. Verify action validity.",
        )
    return OperatorOverride(**res)
