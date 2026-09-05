"""MultiAgentOrchestrator: Central service coordinating specialized AI workers."""

import asyncio
from datetime import datetime, timezone
import logging
import time
from typing import Any, Callable, Coroutine, Dict, List, Optional
import uuid

from app.orchestration.aggregation import ContextAggregator, context_aggregator
from app.orchestration.audit import OrchestrationAuditLogger, orchestration_audit_logger
from app.orchestration.executor import DAGExecutor, dag_executor
from app.orchestration.models import (
    AgentRequest,
    AgentResponse,
    AgentSpec,
    AgentStatus,
    OperatorBriefing,
    OrchestrationResult,
    OrchestrationState,
    OrchestrationStatusResponse,
    ValidatedContext,
)
from app.orchestration.registry import AgentRegistry, agent_registry
from app.orchestration.router import CapabilityRouter, capability_router
from app.orchestration.validation import OutputValidator, output_validator

logger = logging.getLogger(__name__)


class MultiAgentOrchestrator:
    """Central deterministic orchestrator for SAMVED multi-agent AI execution."""

    def __init__(
        self,
        registry: Optional[AgentRegistry] = None,
        router: Optional[CapabilityRouter] = None,
        executor: Optional[DAGExecutor] = None,
        validator: Optional[OutputValidator] = None,
        aggregator: Optional[ContextAggregator] = None,
        audit_logger: Optional[OrchestrationAuditLogger] = None,
    ):
        self.registry = registry or agent_registry
        self.router = router or capability_router
        self.executor = executor or dag_executor
        self.validator = validator or output_validator
        self.aggregator = aggregator or context_aggregator
        self.audit_logger = audit_logger or orchestration_audit_logger

    async def orchestrate_turn(
        self,
        call_id: str,
        turn_id: str,
        context: Dict[str, Any],
        safety_state: str = "SAFE",
        cancel_event: Optional[asyncio.Event] = None,
        requested_agents: Optional[List[str]] = None,
        event_callback: Optional[Callable[[str, Dict[str, Any]], Coroutine[Any, Any, None]]] = None,
    ) -> OrchestrationResult:
        """Coordinate multi-agent execution for a single conversational turn."""
        start_time = time.perf_counter()
        request_id = str(uuid.uuid4())

        # 1. Routing and Stage Planning
        plan = self.router.plan_turn(
            task_type=context.get("task_type", "turn_triage"),
            safety_state=safety_state,
            requested_agents=requested_agents,
            is_realtime=True,
        )

        # Notify orchestration started
        if event_callback:
            try:
                await event_callback("ORCHESTRATION_STARTED", {
                    "request_id": request_id,
                    "call_id": call_id,
                    "turn_id": turn_id,
                    "selected_agents": plan.all_worker_names,
                    "routing_reason": plan.routing_reason,
                })
            except Exception as e:
                logger.warning(f"Error in orchestration start callback: {e}")

        all_responses: Dict[str, AgentResponse] = {}
        warnings: List[str] = []

        # 2. Stage 1 Execution (Context Workers)
        stage_1_req = AgentRequest(
            request_id=request_id,
            call_id=call_id,
            turn_id=turn_id,
            task_type="context_extraction",
            language=context.get("language", "ta-IN"),
            relevant_context=context,
        )

        stage_1_responses = await self.executor.execute_stage(
            workers=plan.stage_1_workers,
            request=stage_1_req,
            cancel_event=cancel_event,
        )

        # Validate stage 1 responses
        for name, resp in stage_1_responses.items():
            validated_resp = self.validator.validate(stage_1_req, resp)
            all_responses[name] = validated_resp
            if validated_resp.warnings:
                warnings.extend(validated_resp.warnings)

        # Check for barge-in cancellation before stage 2
        if cancel_event and cancel_event.is_set():
            total_elapsed = (time.perf_counter() - start_time) * 1000
            cancelled_result = OrchestrationResult(
                request_id=request_id,
                call_id=call_id,
                turn_id=turn_id,
                state=OrchestrationState.DEGRADED,
                selected_agents=plan.all_worker_names,
                completed_agents=[name for name, r in all_responses.items() if r.status == AgentStatus.SUCCESS],
                cancelled_agents=[w.name for w in plan.stage_2_workers],
                agent_outputs=all_responses,
                total_latency_ms=total_elapsed,
                warnings=["Turn interrupted by caller barge-in during multi-agent execution"],
            )
            self.audit_logger.log_run(cancelled_result)
            return cancelled_result

        # 3. Context Aggregation
        validated_ctx = self.aggregator.aggregate(all_responses, context)

        # 4. Stage 2 Execution (Operator Briefing / Summaries)
        stage_2_context = dict(context)
        stage_2_context["facts"] = validated_ctx.facts
        stage_2_context["safety_info"] = validated_ctx.safety_info
        stage_2_context["acoustic_info"] = validated_ctx.acoustic_info
        stage_2_context["language_info"] = validated_ctx.language_info
        stage_2_context["support_info"] = validated_ctx.support_info

        stage_2_req = AgentRequest(
            request_id=request_id,
            call_id=call_id,
            turn_id=turn_id,
            task_type="operator_briefing",
            language=context.get("language", "ta-IN"),
            relevant_context=stage_2_context,
        )

        stage_2_responses = await self.executor.execute_stage(
            workers=plan.stage_2_workers,
            request=stage_2_req,
            cancel_event=cancel_event,
        )

        for name, resp in stage_2_responses.items():
            validated_resp = self.validator.validate(stage_2_req, resp)
            all_responses[name] = validated_resp
            if validated_resp.warnings:
                warnings.extend(validated_resp.warnings)

        # 5. Extract Operator Briefing
        briefing: Optional[OperatorBriefing] = None
        briefing_resp = all_responses.get("operator_briefing_agent")
        if briefing_resp and briefing_resp.status == AgentStatus.SUCCESS:
            b_res = briefing_resp.result
            briefing = OperatorBriefing(
                safety_summary=b_res.get("safety_summary", ""),
                svi_summary=b_res.get("svi_summary", ""),
                acoustic_summary=b_res.get("acoustic_summary", ""),
                adaptive_recommendation=b_res.get("adaptive_recommendation", ""),
                key_facts=b_res.get("key_facts", []),
                evidence_refs=briefing_resp.evidence_refs,
                confidence=briefing_resp.confidence,
                generated_at=briefing_resp.produced_at,
            )
        else:
            # Construct fallback briefing from validated context
            briefing = OperatorBriefing(
                safety_summary=f"Safety status: {safety_state}",
                svi_summary=f"SVI tier: {context.get('svi_tier', 'UNKNOWN')}",
                acoustic_summary="Acoustic metrics recorded.",
                adaptive_recommendation="Continue active listening.",
                key_facts=validated_ctx.facts.get("key_facts", []),
                evidence_refs=validated_ctx.evidence_refs,
                confidence=0.7,
            )

        # 6. Determine final state and agent groups
        completed_agents: List[str] = []
        failed_agents: List[str] = []
        timed_out_agents: List[str] = []
        cancelled_agents: List[str] = []

        for name, resp in all_responses.items():
            if resp.status == AgentStatus.SUCCESS:
                completed_agents.append(name)
            elif resp.status == AgentStatus.TIMED_OUT:
                timed_out_agents.append(name)
            elif resp.status == AgentStatus.CANCELLED:
                cancelled_agents.append(name)
            else:
                failed_agents.append(name)

        # Orchestration state determination
        if failed_agents or timed_out_agents or cancelled_agents:
            # Check if safety agent failed
            safety_resp = all_responses.get("safety_context_agent")
            if safety_resp and safety_resp.status != AgentStatus.SUCCESS:
                state = OrchestrationState.FAILED
            else:
                state = OrchestrationState.DEGRADED
        else:
            state = OrchestrationState.COMPLETED

        total_latency_ms = (time.perf_counter() - start_time) * 1000

        result = OrchestrationResult(
            request_id=request_id,
            call_id=call_id,
            turn_id=turn_id,
            state=state,
            selected_agents=plan.all_worker_names,
            completed_agents=completed_agents,
            failed_agents=failed_agents,
            timed_out_agents=timed_out_agents,
            cancelled_agents=cancelled_agents,
            briefing=briefing,
            validated_context=validated_ctx,
            agent_outputs=all_responses,
            total_latency_ms=total_latency_ms,
            warnings=warnings,
            completed_at=datetime.now(timezone.utc).isoformat(),
        )

        # Audit log
        self.audit_logger.log_run(result)

        # Notify completion
        if event_callback:
            event_type = "ORCHESTRATION_COMPLETED" if state == OrchestrationState.COMPLETED else "ORCHESTRATION_DEGRADED"
            try:
                await event_callback(event_type, {
                    "request_id": request_id,
                    "call_id": call_id,
                    "turn_id": turn_id,
                    "state": state.value,
                    "completed_agents": completed_agents,
                    "failed_agents": failed_agents,
                    "timed_out_agents": timed_out_agents,
                    "total_latency_ms": total_latency_ms,
                    "briefing": briefing.model_dump() if briefing else None,
                })
            except Exception as e:
                logger.warning(f"Error in orchestration completion callback: {e}")

        return result

    def get_status(self) -> OrchestrationStatusResponse:
        """Get overall status of the orchestration engine."""
        agents = self.registry.list_agents()
        capabilities = self.registry.all_capabilities()
        return OrchestrationStatusResponse(
            status="healthy",
            engine_version="1.0.0",
            registered_agents_count=len(agents),
            active_capabilities=capabilities,
            human_supervision_active=True,
            deterministic_safety_authoritative=True,
        )

    def list_agents(self) -> List[AgentSpec]:
        """List registered agent specifications."""
        return self.registry.list_agents()

    def get_history(self, call_id: str) -> List[OrchestrationResult]:
        """Get orchestration run history for a call."""
        return self.audit_logger.get_runs_for_call(call_id)

    def get_latest(self, call_id: str) -> Optional[OrchestrationResult]:
        """Get latest orchestration result for a call."""
        return self.audit_logger.get_latest_run_for_call(call_id)


# Global default multi-agent orchestrator instance
multi_agent_orchestrator = MultiAgentOrchestrator()
