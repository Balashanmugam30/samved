"""CapabilityRouter: Deterministic routing and stage planning for multi-agent execution."""

import logging
from typing import Any, Dict, List, Optional

from app.orchestration.contracts import BaseAgentWorker
from app.orchestration.models import AgentSafetyClassification
from app.orchestration.registry import AgentRegistry, agent_registry

logger = logging.getLogger(__name__)


class ExecutionPlan:
    """Represents a structured multi-stage execution plan."""

    def __init__(
        self,
        stage_1_workers: List[BaseAgentWorker],
        stage_2_workers: List[BaseAgentWorker],
        routing_reason: str,
        total_timeout_ms: int = 250,
    ):
        self.stage_1_workers = stage_1_workers
        self.stage_2_workers = stage_2_workers
        self.routing_reason = routing_reason
        self.total_timeout_ms = total_timeout_ms

    @property
    def all_worker_names(self) -> List[str]:
        names = [w.name for w in self.stage_1_workers]
        names.extend([w.name for w in self.stage_2_workers])
        return names

    def to_dict(self) -> Dict[str, Any]:
        return {
            "stage_1": [w.name for w in self.stage_1_workers],
            "stage_2": [w.name for w in self.stage_2_workers],
            "routing_reason": self.routing_reason,
            "total_timeout_ms": self.total_timeout_ms,
            "all_selected": self.all_worker_names,
        }


class CapabilityRouter:
    """Deterministic capability router for multi-agent turn orchestration."""

    def __init__(self, registry: Optional[AgentRegistry] = None):
        self.registry = registry or agent_registry

    def plan_turn(
        self,
        task_type: str = "turn_triage",
        safety_state: str = "SAFE",
        requested_agents: Optional[List[str]] = None,
        is_realtime: bool = True,
    ) -> ExecutionPlan:
        """Create a deterministic DAG execution plan for a turn.
        
        Stage 1: Context extraction workers run in parallel.
        Stage 2: Summary/briefing workers run after Stage 1 outputs are aggregated.
        """
        # If explicit requested_agents provided (e.g. via REST API or test), filter to those
        if requested_agents is not None:
            stage_1: List[BaseAgentWorker] = []
            stage_2: List[BaseAgentWorker] = []
            for name in requested_agents:
                worker = self.registry.get(name)
                if worker and worker.spec.enabled:
                    if worker.name == "operator_briefing_agent":
                        stage_2.append(worker)
                    else:
                        stage_1.append(worker)
            return ExecutionPlan(
                stage_1_workers=stage_1,
                stage_2_workers=stage_2,
                routing_reason=f"Explicit requested agents: {requested_agents}",
                total_timeout_ms=250 if is_realtime else 1000,
            )

        # High-risk / Critical safety state: fast-track safety context & briefing
        if safety_state in ("CRITICAL", "SAFE_WORD_TRIGGERED"):
            stage_1 = [
                w for w in [
                    self.registry.get("safety_context_agent"),
                    self.registry.get("acoustic_context_agent"),
                    self.registry.get("language_context_agent"),
                    self.registry.get("conversation_context_agent"),
                ]
                if w and w.spec.enabled
            ]
            briefing = self.registry.get("operator_briefing_agent")
            stage_2 = [briefing] if briefing and briefing.spec.enabled else []
            return ExecutionPlan(
                stage_1_workers=stage_1,
                stage_2_workers=stage_2,
                routing_reason=f"High urgency safety state: {safety_state}. Support options omitted to minimize latency.",
                total_timeout_ms=200,
            )

        # Standard triage turn
        stage_1 = [
            w for w in [
                self.registry.get("safety_context_agent"),
                self.registry.get("acoustic_context_agent"),
                self.registry.get("language_context_agent"),
                self.registry.get("conversation_context_agent"),
                self.registry.get("support_options_agent"),
            ]
            if w and w.spec.enabled
        ]
        briefing = self.registry.get("operator_briefing_agent")
        stage_2 = [briefing] if briefing and briefing.spec.enabled else []

        return ExecutionPlan(
            stage_1_workers=stage_1,
            stage_2_workers=stage_2,
            routing_reason="Standard turn triage pipeline with parallel context extraction and operator briefing.",
            total_timeout_ms=250 if is_realtime else 1000,
        )


capability_router = CapabilityRouter()
