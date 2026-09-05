"""SAMVED Phase 16: SIH 2026 Presentation Demo Module."""

from app.demo.catalog import (
    FLAGSHIP_SCENARIO_ID,
    FLAGSHIP_TAMIL_ENG_SCENARIO,
    get_demo_scenario,
    list_demo_scenarios,
)
from app.demo.models import (
    DemoDialogueTurn,
    DemoReplayExecutionResult,
    DemoReplayStageResult,
    DemoResetResponse,
    DemoScenario,
    DemoSpeakerRole,
    DemoStageStatus,
    DemoStatusResponse,
)
from app.demo.service import DemoService, get_demo_service

__all__ = [
    "FLAGSHIP_SCENARIO_ID",
    "FLAGSHIP_TAMIL_ENG_SCENARIO",
    "get_demo_scenario",
    "list_demo_scenarios",
    "DemoDialogueTurn",
    "DemoReplayExecutionResult",
    "DemoReplayStageResult",
    "DemoResetResponse",
    "DemoScenario",
    "DemoSpeakerRole",
    "DemoStageStatus",
    "DemoStatusResponse",
    "DemoService",
    "get_demo_service",
]
