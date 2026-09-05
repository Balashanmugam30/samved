"""SAMVED Phase 16: SIH 2026 Presentation Demo Models & Contracts.

Defines schemas for flagship demo scenario definitions, multi-stage replay execution results,
and deterministic demo environment state management.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
import uuid
from pydantic import BaseModel, Field


class DemoSpeakerRole(str, Enum):
    CALLER = "CALLER"
    AGENT = "AGENT"
    OPERATOR = "OPERATOR"


class DemoDialogueTurn(BaseModel):
    turn_index: int
    speaker: DemoSpeakerRole
    text: str
    transcription_raw: str
    translation_en: str
    detected_language: str
    acoustic_stress_score: float = Field(ge=0.0, le=1.0)
    delay_ms: int = 400


class DemoStageStatus(str, Enum):
    SUCCESS = "SUCCESS"
    VERIFIED = "VERIFIED"
    DEGRADED = "DEGRADED"
    FALLBACK = "FALLBACK"


class DemoReplayStageResult(BaseModel):
    stage_number: int
    stage_name: str
    subsystem: str
    status: DemoStageStatus = DemoStageStatus.SUCCESS
    duration_ms: float
    description: str
    payload: Dict[str, Any] = Field(default_factory=dict)
    verified_assertions: List[str] = Field(default_factory=list)


class DemoReplayExecutionResult(BaseModel):
    execution_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    scenario_id: str
    title: str
    language: str
    duration_total_ms: float
    svi_score: int
    svi_band: str
    protocol_activated: str
    safety_triggers: List[str]
    warm_transfer_ready: bool
    warm_transfer_briefing: str
    rag_citations: List[Dict[str, str]]
    case_entity_id: str
    followup_window: str
    audit_event_hash: str
    stages: List[DemoReplayStageResult]
    executed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class DemoScenario(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    scenario_id: str
    title: str
    description: str
    problem_statement: str = "SIH 2026 PS-26093"
    language_pair: str
    caller_profile: Dict[str, Any]
    dialogue: List[DemoDialogueTurn]
    expected_safety_triggers: List[str]
    expected_svi: Dict[str, Any]
    expected_protocol: str
    expected_warm_transfer: Dict[str, Any]
    expected_rag_citations: List[Dict[str, str]]
    expected_case_linkage: Dict[str, Any]
    expected_followup: Dict[str, Any]
    tags: List[str] = Field(default_factory=list)


class DemoResetResponse(BaseModel):
    status: str
    message: str
    reset_timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    cleared_items: Dict[str, int]
    demo_mode_enabled: bool


class DemoStatusResponse(BaseModel):
    demo_mode_enabled: bool
    environment: str
    app_mode: str
    flagship_scenario_id: str
    flagship_scenario_title: str
    available_scenarios_count: int
    replays_conducted_count: int
    is_safe_to_reset: bool
