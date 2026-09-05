"""API endpoints for SAMVED Phase 9 Multi-Agent Orchestration."""

import logging
from typing import Any, Dict, List, Optional
import uuid
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from app.orchestration.models import (
    AgentSpec,
    OrchestrationResult,
    OrchestrationStatusResponse,
)
from app.orchestration.service import multi_agent_orchestrator
from app.realtime.session_manager import telephony_session_manager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/orchestration", tags=["orchestration"])


class PlanRequest(BaseModel):
    task_type: str = "turn_triage"
    safety_state: str = "SAFE"
    requested_agents: Optional[List[str]] = None
    is_realtime: bool = True


class PlanResponse(BaseModel):
    stage_1: List[str]
    stage_2: List[str]
    routing_reason: str
    total_timeout_ms: int
    all_selected: List[str]


class RefreshRequest(BaseModel):
    requested_agents: Optional[List[str]] = None


@router.get("/status", response_model=OrchestrationStatusResponse)
async def get_orchestration_status():
    """Get the current health and capability status of the multi-agent orchestration engine."""
    return multi_agent_orchestrator.get_status()


@router.get("/agents", response_model=List[AgentSpec])
async def list_registered_agents():
    """List specifications of all registered worker agents."""
    return multi_agent_orchestrator.list_agents()


@router.post("/plan", response_model=PlanResponse)
async def plan_orchestration(request: PlanRequest):
    """Determine the deterministic execution plan for a given task and safety state."""
    plan = multi_agent_orchestrator.router.plan_turn(
        task_type=request.task_type,
        safety_state=request.safety_state,
        requested_agents=request.requested_agents,
        is_realtime=request.is_realtime,
    )
    return PlanResponse(**plan.to_dict())


@router.get("/calls/{call_id}", response_model=OrchestrationResult)
async def get_call_latest_orchestration(call_id: str):
    """Get the latest orchestration result for a specific call."""
    result = multi_agent_orchestrator.get_latest(call_id)
    if not result:
        # Check active session if available
        session = await telephony_session_manager.get_by_call_id(call_id)
        if session and session.latest_orchestration:
            return session.latest_orchestration
        raise HTTPException(
            status_code=404,
            detail=f"No orchestration runs found for call_id '{call_id}'",
        )
    return result


@router.get("/calls/{call_id}/history", response_model=List[OrchestrationResult])
async def get_call_orchestration_history(call_id: str):
    """Get the full history of orchestration runs for a specific call."""
    runs = multi_agent_orchestrator.get_history(call_id)
    if not runs:
        session = await telephony_session_manager.get_by_call_id(call_id)
        if session and session.orchestration_history:
            return session.orchestration_history
    return runs


@router.post("/calls/{call_id}/refresh", response_model=OrchestrationResult)
async def refresh_call_orchestration(call_id: str, request: Optional[RefreshRequest] = None):
    """Manually re-run orchestration on the current state of a call."""
    session = await telephony_session_manager.get_by_call_id(call_id)
    requested_agents = request.requested_agents if request else None

    if session:
        # Re-run against live session state
        utts = session.get_utterances()
        last_text = utts[-1]["text"] if utts else "Manual orchestration refresh triggered by operator"
        turn_id = f"refresh-{uuid.uuid4().hex[:8]}"

        context = {
            "transcript": last_text,
            "text": last_text,
            "language": session.orchestrator.current_language.value if session.orchestrator else "ta-IN",
            "history": utts,
            "safety_state": session.orchestrator.current_safety_state if session.orchestrator else "SAFE",
            "acoustic_features": session.latest_acoustic or {},
            "svi": session.latest_svi or {},
            "adaptive": session.latest_adaptive_strategy or {},
            "task_type": "operator_refresh",
        }

        result = await multi_agent_orchestrator.orchestrate_turn(
            call_id=call_id,
            turn_id=turn_id,
            context=context,
            safety_state=context["safety_state"],
            requested_agents=requested_agents,
        )
        session.record_orchestration_result(result)
        return result

    # Check if there is past audit history to refresh against
    past_runs = multi_agent_orchestrator.get_history(call_id)
    if past_runs:
        latest = past_runs[-1]
        turn_id = f"refresh-{uuid.uuid4().hex[:8]}"
        context = {
            "transcript": "Historical replay refresh",
            "history": [],
            "safety_state": "SAFE",
            "task_type": "historical_refresh",
        }
        result = await multi_agent_orchestrator.orchestrate_turn(
            call_id=call_id,
            turn_id=turn_id,
            context=context,
            safety_state="SAFE",
            requested_agents=requested_agents,
        )
        return result

    raise HTTPException(
        status_code=404,
        detail=f"Call '{call_id}' not found in active sessions or audit history",
    )
