"""FastAPI REST API routes for SAMVED Phase 12 Follow-up Workflow & Continuity Engine."""

import logging
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, Query, status

from app.followup.audit import get_audit_logger
from app.followup.models import FollowupAttempt, FollowupRecord, FollowupWorkqueueSummary
from app.followup.schemas import (
    ApproveFollowupRequest,
    AssignFollowupRequest,
    CancelFollowupRequest,
    CompleteFollowupRequest,
    CreateFollowupRequest,
    FollowupActionResponse,
    FollowupListResponse,
    RecordAttemptRequest,
    RescheduleFollowupRequest,
    RevokeConsentRequest,
    ScheduleFollowupRequest,
    StartFollowupRequest,
)
from app.followup.service import get_followup_service
from app.schemas.events import ConsentState, FollowupPriority, FollowupStatus

logger = logging.getLogger("samved.api.followup")

router = APIRouter(tags=["Follow-up Workflow & Continuity"])


@router.get("/followups/status", response_model=Dict[str, Any])
async def get_followup_subsystem_status():
    """Returns operational status, queue metrics, and safety disclaimer for Follow-up Subsystem."""
    svc = get_followup_service()
    summary = await svc.get_workqueue_summary()
    return {
        "subsystem": "followup_workflow",
        "status": "ready",
        "policy_version": "v1.0",
        "workqueue_summary": summary.model_dump(),
        "safety_disclaimer": "Follow-up workflows are human-supervised continuity tasks. SAMVED does not autonomously contact callers, infer consent, or perform emergency outreach.",
    }


@router.get("/followups/summary", response_model=FollowupWorkqueueSummary)
async def get_workqueue_summary(case_id: Optional[str] = Query(None)):
    """Returns aggregated summary metrics for the operator follow-up workqueue."""
    svc = get_followup_service()
    return await svc.get_workqueue_summary(case_id=case_id)


@router.get("/followups", response_model=FollowupListResponse)
async def list_followups(
    case_id: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    priority: Optional[str] = Query(None),
    assigned_to: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    """Lists follow-up tasks filtered by case, status, priority, or assignee."""
    svc = get_followup_service()
    items, total = await svc.list_followups(
        case_id=case_id,
        status=status,
        priority=priority,
        assigned_to=assigned_to,
        limit=limit,
        offset=offset,
    )
    summary = await svc.get_workqueue_summary(case_id=case_id)
    return FollowupListResponse(
        items=items,
        total=total,
        limit=limit,
        offset=offset,
        summary=summary,
    )


@router.get("/cases/{case_id}/followups", response_model=FollowupListResponse)
async def list_case_followups(
    case_id: str,
    status: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    """Lists all follow-up tasks specifically belonging to a given case."""
    svc = get_followup_service()
    items, total = await svc.list_followups(
        case_id=case_id,
        status=status,
        limit=limit,
        offset=offset,
    )
    summary = await svc.get_workqueue_summary(case_id=case_id)
    return FollowupListResponse(
        items=items,
        total=total,
        limit=limit,
        offset=offset,
        summary=summary,
    )


@router.get("/followups/{followup_id}", response_model=FollowupRecord)
async def get_followup_detail(followup_id: str):
    """Retrieves details of a specific follow-up task."""
    svc = get_followup_service()
    item = await svc.get_followup(followup_id)
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Follow-up task '{followup_id}' not found.",
        )
    return item


@router.get("/followups/{followup_id}/attempts", response_model=List[FollowupAttempt])
async def get_followup_attempts(followup_id: str):
    """Retrieves execution attempt logs for a follow-up task."""
    svc = get_followup_service()
    item = await svc.get_followup(followup_id)
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Follow-up task '{followup_id}' not found.",
        )
    return await svc.get_attempts(followup_id)


@router.get("/followups/{followup_id}/audit", response_model=List[Dict[str, Any]])
async def get_followup_audit_trail(followup_id: str):
    """Retrieves chronological immutable audit trail for a follow-up task."""
    audit_logger = get_audit_logger()
    records = audit_logger.get_logs_for_followup(followup_id)
    return [r.model_dump() for r in records]


@router.post("/cases/{case_id}/followups", response_model=FollowupRecord, status_code=status.HTTP_201_CREATED)
async def create_followup(case_id: str, req: CreateFollowupRequest):
    """Creates a new human-supervised follow-up task anchored to a case."""
    svc = get_followup_service()
    try:
        followup, warnings = await svc.create_followup(case_id, req)
        return followup
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.exception("Error creating follow-up")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post("/followups/{followup_id}/approve", response_model=FollowupActionResponse)
async def approve_followup(followup_id: str, req: ApproveFollowupRequest):
    """Approves a draft or pending follow-up task."""
    svc = get_followup_service()
    try:
        updated = await svc.approve_followup(followup_id, req)
        return FollowupActionResponse(
            success=True,
            message="Follow-up task approved successfully.",
            followup=updated,
        )
    except KeyError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Follow-up '{followup_id}' not found.")
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/followups/{followup_id}/schedule", response_model=FollowupActionResponse)
async def schedule_followup(followup_id: str, req: ScheduleFollowupRequest):
    """Updates the scheduled window and due date for a follow-up task."""
    svc = get_followup_service()
    try:
        updated = await svc.schedule_followup(followup_id, req)
        return FollowupActionResponse(
            success=True,
            message="Follow-up task scheduled successfully.",
            followup=updated,
        )
    except KeyError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Follow-up '{followup_id}' not found.")
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/followups/{followup_id}/assign", response_model=FollowupActionResponse)
async def assign_followup(followup_id: str, req: AssignFollowupRequest):
    """Assigns follow-up task to an authorized operator."""
    svc = get_followup_service()
    try:
        updated = await svc.assign_followup(followup_id, req)
        return FollowupActionResponse(
            success=True,
            message="Follow-up task assigned successfully.",
            followup=updated,
        )
    except KeyError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Follow-up '{followup_id}' not found.")


@router.post("/followups/{followup_id}/start", response_model=FollowupActionResponse)
async def start_followup(followup_id: str, req: StartFollowupRequest):
    """Transitions a READY or SCHEDULED follow-up task to IN_PROGRESS."""
    svc = get_followup_service()
    try:
        updated = await svc.start_followup(followup_id, req)
        return FollowupActionResponse(
            success=True,
            message="Follow-up task started.",
            followup=updated,
        )
    except KeyError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Follow-up '{followup_id}' not found.")
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/followups/{followup_id}/attempt", response_model=FollowupActionResponse)
async def record_attempt(followup_id: str, req: RecordAttemptRequest):
    """Records a discrete contact attempt by an operator."""
    svc = get_followup_service()
    try:
        updated, attempt = await svc.record_attempt(followup_id, req)
        return FollowupActionResponse(
            success=True,
            message=f"Attempt {attempt.attempt_number} recorded: {attempt.result}",
            followup=updated,
        )
    except KeyError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Follow-up '{followup_id}' not found.")
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/followups/{followup_id}/complete", response_model=FollowupActionResponse)
async def complete_followup(followup_id: str, req: CompleteFollowupRequest):
    """Completes a follow-up task with structured outcome and notes."""
    svc = get_followup_service()
    try:
        updated = await svc.complete_followup(followup_id, req)
        return FollowupActionResponse(
            success=True,
            message="Follow-up completed successfully.",
            followup=updated,
        )
    except KeyError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Follow-up '{followup_id}' not found.")
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/followups/{followup_id}/reschedule", response_model=FollowupActionResponse)
async def reschedule_followup(followup_id: str, req: RescheduleFollowupRequest):
    """Reschedules a task to a new safe contact window."""
    svc = get_followup_service()
    try:
        updated = await svc.reschedule_followup(followup_id, req)
        return FollowupActionResponse(
            success=True,
            message="Follow-up rescheduled successfully.",
            followup=updated,
        )
    except KeyError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Follow-up '{followup_id}' not found.")
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/followups/{followup_id}/cancel", response_model=FollowupActionResponse)
async def cancel_followup(followup_id: str, req: CancelFollowupRequest):
    """Cancels a follow-up task with an auditable reason."""
    svc = get_followup_service()
    try:
        updated = await svc.cancel_followup(followup_id, req)
        return FollowupActionResponse(
            success=True,
            message="Follow-up cancelled.",
            followup=updated,
        )
    except KeyError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Follow-up '{followup_id}' not found.")
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/cases/{case_id}/revoke-consent", response_model=Dict[str, Any])
async def revoke_consent(case_id: str, req: RevokeConsentRequest):
    """Revokes caller consent for a case, immediately blocking all active tasks."""
    svc = get_followup_service()
    try:
        blocked = await svc.revoke_consent(case_id, req)
        return {
            "success": True,
            "case_id": case_id,
            "blocked_tasks_count": len(blocked),
            "message": f"Caller consent revoked; {len(blocked)} active follow-up tasks transitioned to BLOCKED.",
        }
    except Exception as e:
        logger.exception("Error revoking consent")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
