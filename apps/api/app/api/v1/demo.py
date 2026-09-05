"""SAMVED Phase 16: SIH 2026 Presentation Demo API Router.

Provides endpoints for SIH evaluators and judges to trigger deterministic flagship scenario replays,
inspect end-to-end multi-stage pipeline performance, and perform clean environment resets.
"""

from typing import Any, Dict, List
from fastapi import APIRouter, Depends, HTTPException, status

from app.demo.models import (
    DemoReplayExecutionResult,
    DemoResetResponse,
    DemoScenario,
    DemoStatusResponse,
)
from app.demo.service import DemoService, get_demo_service

demo_router = APIRouter(tags=["SIH 2026 Presentation Demo"])


@demo_router.get("/status", response_model=DemoStatusResponse)
async def get_demo_status(
    service: DemoService = Depends(get_demo_service),
) -> DemoStatusResponse:
    """Retrieve demo configuration, active scenario metadata, and safe reset capabilities."""
    return service.get_status()


@demo_router.get("/flagship", response_model=DemoScenario)
async def get_flagship_scenario(
    service: DemoService = Depends(get_demo_service),
) -> DemoScenario:
    """Retrieve the flagship SIH Tamil/English code-switching scenario specification."""
    return service.get_flagship_scenario()


@demo_router.get("/scenarios", response_model=List[DemoScenario])
async def list_scenarios(
    service: DemoService = Depends(get_demo_service),
) -> List[DemoScenario]:
    """List all scenarios available in the SIH demonstration catalog."""
    from app.demo.catalog import list_demo_scenarios
    return list_demo_scenarios()


@demo_router.post("/flagship/replay", response_model=DemoReplayExecutionResult)
async def replay_flagship(
    service: DemoService = Depends(get_demo_service),
) -> DemoReplayExecutionResult:
    """Execute a deterministic end-to-end replay of the flagship Tamil/English crisis scenario.

    Runs all 8 pipeline stages (ASR -> Safety -> SVI -> Adaptive -> Warm Transfer -> RAG -> Case Graph -> Audit)
    and returns latency metrics, verified assertions, and full payload details for judge evaluation.
    """
    return await service.replay_flagship_scenario()


@demo_router.post("/reset", response_model=DemoResetResponse)
async def reset_demo(
    service: DemoService = Depends(get_demo_service),
) -> DemoResetResponse:
    """Safely reset the demo environment back to pristine condition for subsequent judge evaluations.

    Protected: This operation is strictly prohibited in LIVE or PRODUCTION environments.
    """
    return service.reset_demo_state()


@demo_router.post("/seed")
async def seed_demo(
    service: DemoService = Depends(get_demo_service),
) -> Dict[str, Any]:
    """Idempotently seed the demonstration environment with synthetic evaluation records."""
    return service.seed_demo_data()
