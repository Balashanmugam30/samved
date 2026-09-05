"""
FastAPI router for SAMVED Phase 14: Scenario Simulator & Evaluation Lab.
Exposes endpoints for listing scenarios, triggering offline/integrated runs,
orchestrating suites, managing baselines, computing regression diffs, and viewing findings.
"""

from __future__ import annotations

import logging
from typing import Optional
from fastapi import APIRouter, HTTPException, Query, status

from app.evaluation.models import (
    BaselineSnapshot,
    EvaluationRunRecord,
    RunDiffResult,
    ScenarioDefinition,
)
from app.evaluation.schemas import (
    BaselineCreateRequest,
    BaselineListResponse,
    DiffRequest,
    EvaluationStatusResponse,
    RunsListResponse,
    RunEvaluationRequest,
    ScenariosListResponse,
    SuiteRunRequest,
    SuiteRunResponse,
)
from app.evaluation.service import get_evaluation_service

logger = logging.getLogger("samved.api.evaluation")

router = APIRouter(prefix="", tags=["Scenario Simulator & Evaluation Lab"])


@router.get("/status", response_model=EvaluationStatusResponse)
async def get_evaluation_status():
    """Returns the operational status, catalog size, and governance guardrails of the evaluation lab."""
    service = get_evaluation_service()
    return service.get_status()


@router.get("/scenarios", response_model=ScenariosListResponse)
async def list_scenarios(
    tag: Optional[str] = Query(None, description="Filter scenarios by tag (e.g. smoke, safety, multilingual)"),
    suite: Optional[str] = Query(None, description="Filter scenarios by suite (e.g. smoke, ci, safety, multilingual)"),
):
    """Lists synthetic evaluation benchmark scenarios."""
    service = get_evaluation_service()
    scenarios = service.list_scenarios(tag=tag, suite=suite)
    return ScenariosListResponse(scenarios=scenarios, total=len(scenarios))


@router.get("/scenarios/{scenario_id}", response_model=ScenarioDefinition)
async def get_scenario(scenario_id: str):
    """Fetches full scenario definition, including turns and golden expectations."""
    service = get_evaluation_service()
    scenario = service.get_scenario(scenario_id)
    if not scenario:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Scenario with ID '{scenario_id}' not found.",
        )
    return scenario


@router.post("/runs", response_model=EvaluationRunRecord, status_code=status.HTTP_201_CREATED)
async def trigger_evaluation_run(req: RunEvaluationRequest):
    """Triggers an offline or integrated evaluation run for a synthetic scenario."""
    service = get_evaluation_service()
    try:
        record = service.run_scenario(
            scenario_id=req.scenario_id,
            mode=req.mode,
            seed=req.seed,
            baseline_id=req.baseline_id,
            fault_override=req.fault_override,
        )
        return record
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )


@router.get("/runs", response_model=RunsListResponse)
async def list_runs(
    scenario_id: Optional[str] = Query(None, description="Filter runs by scenario ID"),
    status_filter: Optional[str] = Query(None, alias="status", description="Filter runs by evaluation or execution status"),
    limit: int = Query(50, ge=1, le=200, description="Max runs to return"),
):
    """Lists past evaluation runs."""
    service = get_evaluation_service()
    runs = service.list_runs(scenario_id=scenario_id, status=status_filter, limit=limit)
    return RunsListResponse(runs=runs, total=len(runs))


@router.get("/runs/{run_id}", response_model=EvaluationRunRecord)
async def get_run(run_id: str):
    """Retrieves full evaluation run record, including assertions, findings, and metrics."""
    service = get_evaluation_service()
    run = service.get_run(run_id)
    if not run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Evaluation run with ID '{run_id}' not found.",
        )
    return run


@router.post("/runs/{run_id}/cancel")
async def cancel_run(run_id: str):
    """Cancels an in-flight or pending evaluation run."""
    service = get_evaluation_service()
    success = service.cancel_run(run_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Run '{run_id}' not found or already terminated.",
        )
    return {"status": "CANCELLED", "run_id": run_id}


@router.post("/suites/run", response_model=SuiteRunResponse)
async def trigger_suite_run(req: SuiteRunRequest):
    """Executes a full evaluation suite (e.g. smoke, safety, multilingual, full) across multiple scenarios."""
    service = get_evaluation_service()
    return service.run_suite(suite_id=req.suite_id, mode=req.mode, seed=req.seed)


@router.get("/baselines", response_model=BaselineListResponse)
async def list_baselines():
    """Lists all captured golden baseline snapshots."""
    service = get_evaluation_service()
    baselines = service.list_baselines()
    return BaselineListResponse(baselines=baselines, total=len(baselines))


@router.post("/baselines", response_model=BaselineSnapshot, status_code=status.HTTP_201_CREATED)
async def capture_baseline(req: BaselineCreateRequest):
    """Promotes a successful evaluation run into an official golden baseline."""
    service = get_evaluation_service()
    baseline = service.create_baseline(
        run_id=req.run_id, description=req.description, tag=req.tag
    )
    if not baseline:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Run '{req.run_id}' could not be found to create a baseline.",
        )
    return baseline


@router.get("/baselines/{baseline_id}", response_model=BaselineSnapshot)
async def get_baseline(baseline_id: str):
    """Retrieves a single golden baseline snapshot by ID."""
    service = get_evaluation_service()
    baseline = service.get_baseline(baseline_id)
    if not baseline:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Baseline with ID '{baseline_id}' not found.",
        )
    return baseline


@router.post("/diff", response_model=RunDiffResult)
async def compute_diff(req: DiffRequest):
    """Computes regression and drift diff between an evaluation run and a baseline or another run."""
    service = get_evaluation_service()
    diff = service.compute_diff(
        current_run_id=req.current_run_id,
        baseline_id=req.baseline_id,
        compare_run_id=req.compare_run_id,
    )
    if not diff:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unable to compute diff. Verify that current_run_id and baseline_id/compare_run_id exist.",
        )
    return diff
