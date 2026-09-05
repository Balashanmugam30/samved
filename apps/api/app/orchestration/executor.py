"""DAGExecutor: Concurrent worker execution, bounded timeouts, and cancellation."""

import asyncio
import logging
import time
from typing import Dict, List, Optional

from app.orchestration.contracts import BaseAgentWorker
from app.orchestration.models import (
    AgentRequest,
    AgentResponse,
    AgentSafetyClassification,
    AgentStatus,
)

logger = logging.getLogger(__name__)


class DAGExecutor:
    """Executes agent workers concurrently with bounded deadlines and cancellation support."""

    async def execute_worker(
        self,
        worker: BaseAgentWorker,
        request: AgentRequest,
        cancel_event: Optional[asyncio.Event] = None,
    ) -> AgentResponse:
        """Execute an individual worker with hard timeout and cancellation checks."""
        start_time = time.perf_counter()

        # Check early cancellation
        if cancel_event and cancel_event.is_set():
            return worker.create_fallback_response(
                request=request,
                status=AgentStatus.CANCELLED,
                error_msg="Cancelled prior to execution (barge-in or stale turn)",
            )

        timeout_sec = max(0.01, worker.max_latency_ms / 1000.0)

        try:
            # Create worker execution task
            worker_task = asyncio.create_task(worker.execute(request))

            if cancel_event:
                # Monitor cancel event alongside worker task
                wait_cancel = asyncio.create_task(cancel_event.wait())
                done, pending = await asyncio.wait(
                    [worker_task, wait_cancel],
                    timeout=timeout_sec,
                    return_when=asyncio.FIRST_COMPLETED,
                )

                for task in pending:
                    task.cancel()

                if cancel_event.is_set():
                    worker_task.cancel()
                    elapsed = (time.perf_counter() - start_time) * 1000
                    return worker.create_fallback_response(
                        request=request,
                        status=AgentStatus.CANCELLED,
                        error_msg="Interrupted by caller barge-in",
                        latency_ms=elapsed,
                    )

                if worker_task in done:
                    response = worker_task.result()
                else:
                    # Timeout occurred
                    elapsed = (time.perf_counter() - start_time) * 1000
                    return worker.create_fallback_response(
                        request=request,
                        status=AgentStatus.TIMED_OUT,
                        error_msg=f"Worker exceeded deadline of {worker.max_latency_ms}ms",
                        latency_ms=elapsed,
                    )
            else:
                response = await asyncio.wait_for(worker_task, timeout=timeout_sec)

            # Validate response
            response = worker.validate_output(response)
            return response

        except asyncio.TimeoutError:
            elapsed = (time.perf_counter() - start_time) * 1000
            logger.warning(f"Agent {worker.name} timed out after {elapsed:.1f}ms")
            return worker.create_fallback_response(
                request=request,
                status=AgentStatus.TIMED_OUT,
                error_msg=f"Worker timed out after {worker.max_latency_ms}ms",
                latency_ms=elapsed,
            )
        except asyncio.CancelledError:
            elapsed = (time.perf_counter() - start_time) * 1000
            logger.info(f"Agent {worker.name} cancelled after {elapsed:.1f}ms")
            return worker.create_fallback_response(
                request=request,
                status=AgentStatus.CANCELLED,
                error_msg="Task cancelled",
                latency_ms=elapsed,
            )
        except Exception as e:
            elapsed = (time.perf_counter() - start_time) * 1000
            logger.exception(f"Agent {worker.name} failed with exception: {e}")
            return worker.create_fallback_response(
                request=request,
                status=AgentStatus.FAILED,
                error_msg=f"Worker exception: {str(e)}",
                latency_ms=elapsed,
            )

    async def execute_stage(
        self,
        workers: List[BaseAgentWorker],
        request: AgentRequest,
        cancel_event: Optional[asyncio.Event] = None,
    ) -> Dict[str, AgentResponse]:
        """Execute a group of workers in parallel."""
        if not workers:
            return {}

        tasks = [
            self.execute_worker(worker, request, cancel_event=cancel_event)
            for worker in workers
        ]
        results = await asyncio.gather(*tasks, return_exceptions=False)

        response_map: Dict[str, AgentResponse] = {}
        for worker, response in zip(workers, results):
            response_map[worker.name] = response

        return response_map


dag_executor = DAGExecutor()
