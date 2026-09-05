"""FastAPI router for SAMVED Phase 14 Scenario Simulation & Operator Training Sandbox."""

import logging
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query, status

from app.simulation.models import (
    BenchmarkSuiteType,
    SimulationScenario,
    WERMetricResult,
)
from app.simulation.schemas import (
    BenchmarkRunRequest,
    BenchmarkRunResponse,
    ScenarioItemResponse,
    SimulationStatusResponse,
    TrainingDrillItemResponse,
    TrainingSessionResponse,
    TrainingSessionStartRequest,
    TrainingTurnResponse,
    TrainingTurnSubmitRequest,
    WERCalculateRequest,
)
from app.simulation.service import simulation_service

logger = logging.getLogger("samved.api.simulation")

router = APIRouter(prefix="", tags=["Scenario Simulation & Training Sandbox"])


@router.get("/status", response_model=SimulationStatusResponse)
async def get_simulation_status():
    """Returns the operational health and catalog status of the simulation engine."""
    stat = simulation_service.get_status()
    return SimulationStatusResponse(**stat)


@router.get("/scenarios", response_model=List[ScenarioItemResponse])
async def list_scenarios(
    band: Optional[str] = Query(None, description="Filter by risk band (LOW, MODERATE, HIGH, CRITICAL)"),
    language: Optional[str] = Query(None, description="Filter by language code (e.g. hi-IN, ta-IN, en-IN)"),
    tag: Optional[str] = Query(None, description="Filter by scenario tag (e.g. smoke, overdose, negation)"),
):
    """Lists synthetic benchmark scenarios with optional filtering."""
    scenarios = simulation_service.list_scenarios(band=band, language=language, tag=tag)
    return [
        ScenarioItemResponse(
            scenario_id=s.scenario_id,
            title=s.title,
            description=s.description,
            language=s.language,
            expected_svi_band=s.expected_svi_band,
            expected_score_range=s.expected_score_range,
            expected_safety_triggers=s.expected_safety_triggers,
            prohibited_safety_triggers=s.prohibited_safety_triggers,
            noise_profile=s.noise_profile,
            turns_count=len(s.synthetic_dialogue),
            tags=s.tags,
        )
        for s in scenarios
    ]


@router.get("/scenarios/{scenario_id}", response_model=SimulationScenario)
async def get_scenario(scenario_id: str):
    """Retrieves full details and turns for a specific benchmark scenario."""
    scenario = simulation_service.get_scenario(scenario_id)
    if not scenario:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Scenario '{scenario_id}' not found in benchmark catalog",
        )
    return scenario


@router.post("/benchmark/run", response_model=BenchmarkRunResponse)
async def trigger_benchmark_run(payload: BenchmarkRunRequest):
    """Triggers an automated benchmark evaluation run across synthetic scenarios."""
    try:
        run = simulation_service.run_benchmark(suite_type=payload.suite)
        return BenchmarkRunResponse(
            run_id=run.run_id,
            suite=run.suite,
            status=run.status,
            started_at=run.started_at.isoformat(),
            completed_at=run.completed_at.isoformat() if run.completed_at else None,
            total_scenarios=run.total_scenarios,
            passed_scenarios=run.passed_scenarios,
            failed_scenarios=run.failed_scenarios,
            pass_rate=run.pass_rate,
            mean_wer=run.mean_wer,
            mean_cer=run.mean_cer,
            safety_recall_rate=run.safety_recall_rate,
            svi_band_accuracy=run.svi_band_accuracy,
            p95_latency_ms=run.p95_latency_ms,
            critical_safety_passed=run.critical_safety_passed,
            results=run.results,
        )
    except Exception as e:
        logger.error(f"Benchmark execution error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Benchmark execution failed: {str(e)}",
        )


@router.get("/benchmark/runs", response_model=List[BenchmarkRunResponse])
async def list_benchmark_runs():
    """Lists completed benchmark runs, newest first."""
    runs = simulation_service.list_benchmark_runs()
    return [
        BenchmarkRunResponse(
            run_id=r.run_id,
            suite=r.suite,
            status=r.status,
            started_at=r.started_at.isoformat(),
            completed_at=r.completed_at.isoformat() if r.completed_at else None,
            total_scenarios=r.total_scenarios,
            passed_scenarios=r.passed_scenarios,
            failed_scenarios=r.failed_scenarios,
            pass_rate=r.pass_rate,
            mean_wer=r.mean_wer,
            mean_cer=r.mean_cer,
            safety_recall_rate=r.safety_recall_rate,
            svi_band_accuracy=r.svi_band_accuracy,
            p95_latency_ms=r.p95_latency_ms,
            critical_safety_passed=r.critical_safety_passed,
            results=r.results,
        )
        for r in runs
    ]


@router.get("/benchmark/runs/{run_id}", response_model=BenchmarkRunResponse)
async def get_benchmark_run(run_id: str):
    """Retrieves detailed results for a specific benchmark run."""
    run = simulation_service.get_benchmark_run(run_id)
    if not run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Benchmark run '{run_id}' not found",
        )
    return BenchmarkRunResponse(
        run_id=run.run_id,
        suite=run.suite,
        status=run.status,
        started_at=run.started_at.isoformat(),
        completed_at=run.completed_at.isoformat() if run.completed_at else None,
        total_scenarios=run.total_scenarios,
        passed_scenarios=run.passed_scenarios,
        failed_scenarios=run.failed_scenarios,
        pass_rate=run.pass_rate,
        mean_wer=run.mean_wer,
        mean_cer=run.mean_cer,
        safety_recall_rate=run.safety_recall_rate,
        svi_band_accuracy=run.svi_band_accuracy,
        p95_latency_ms=run.p95_latency_ms,
        critical_safety_passed=run.critical_safety_passed,
        results=run.results,
    )


@router.post("/wer/evaluate", response_model=WERMetricResult)
async def evaluate_wer_cer(payload: WERCalculateRequest):
    """Computes normalized Word Error Rate (WER) and Character Error Rate (CER) on text pairs."""
    return simulation_service.evaluate_wer_cer(
        reference=payload.reference, hypothesis=payload.hypothesis
    )


@router.get("/training/drills", response_model=List[TrainingDrillItemResponse])
async def list_training_drills(
    difficulty: Optional[str] = Query(None, description="Filter by difficulty: BEGINNER, INTERMEDIATE, ADVANCED, EXPERT"),
):
    """Lists available training drills for tele-counselor practice."""
    drills = simulation_service.list_training_drills(difficulty=difficulty)
    return [
        TrainingDrillItemResponse(
            id=d.id,
            drill_key=d.drill_key,
            title=d.title,
            category=d.category,
            difficulty=d.difficulty,
            language=d.language,
            description=d.description,
            scenario_context=d.scenario_context,
            expected_competencies=d.expected_competencies,
            turns_count=len(d.turns),
        )
        for d in drills
    ]


@router.post("/training/session/start", response_model=TrainingSessionResponse)
async def start_training_session(payload: TrainingSessionStartRequest):
    """Starts a new interactive training session for a counselor trainee."""
    try:
        session = simulation_service.start_training_session(
            drill_key=payload.drill_key,
            trainee_id=payload.trainee_id or "T-1001",
            trainee_name=payload.trainee_name or "Counselor Trainee",
        )
        return TrainingSessionResponse(
            session_id=session.session_id,
            drill_id=session.drill_id,
            trainee_id=session.trainee_id,
            trainee_name=session.trainee_name,
            status=session.status,
            started_at=session.started_at.isoformat(),
            completed_at=session.completed_at.isoformat() if session.completed_at else None,
            current_turn=session.current_turn,
            total_turns=session.total_turns,
            overall_score=session.overall_score,
            performance_rating=session.performance_rating,
            competency_breakdown=session.competency_breakdown,
            recommendations=session.recommendations,
            evaluated_turns=[],
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )


@router.get("/training/session/{session_id}", response_model=TrainingSessionResponse)
async def get_training_session(session_id: str):
    """Retrieves current state and scorecard for an active or completed training session."""
    session = simulation_service.get_training_session(session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Training session '{session_id}' not found",
        )
    return TrainingSessionResponse(
        session_id=session.session_id,
        drill_id=session.drill_id,
        trainee_id=session.trainee_id,
        trainee_name=session.trainee_name,
        status=session.status,
        started_at=session.started_at.isoformat(),
        completed_at=session.completed_at.isoformat() if session.completed_at else None,
        current_turn=session.current_turn,
        total_turns=session.total_turns,
        overall_score=session.overall_score,
        performance_rating=session.performance_rating,
        competency_breakdown=session.competency_breakdown,
        recommendations=session.recommendations,
        evaluated_turns=[
            TrainingTurnResponse(
                turn_number=t.turn_number,
                trainee_input=t.trainee_input,
                score=t.score,
                safety_protocol_score=t.safety_protocol_score,
                empathy_score=t.empathy_score,
                de_escalation_score=t.de_escalation_score,
                statutory_referral_score=t.statutory_referral_score,
                feedback_hints=t.feedback_hints,
                caller_next_turn=t.caller_next_turn,
            )
            for t in session.evaluated_turns
        ],
    )


@router.post("/training/session/{session_id}/turn", response_model=TrainingTurnResponse)
async def submit_training_turn(session_id: str, payload: TrainingTurnSubmitRequest):
    """Submits a trainee counselor turn for real-time SOP scoring and next-turn progression."""
    try:
        eval_turn = simulation_service.submit_training_turn(
            session_id=session_id, trainee_input=payload.trainee_input
        )
        return TrainingTurnResponse(
            turn_number=eval_turn.turn_number,
            trainee_input=eval_turn.trainee_input,
            score=eval_turn.score,
            safety_protocol_score=eval_turn.safety_protocol_score,
            empathy_score=eval_turn.empathy_score,
            de_escalation_score=eval_turn.de_escalation_score,
            statutory_referral_score=eval_turn.statutory_referral_score,
            feedback_hints=eval_turn.feedback_hints,
            caller_next_turn=eval_turn.caller_next_turn,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
