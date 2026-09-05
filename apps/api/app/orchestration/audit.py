"""OrchestrationAuditLogger: In-memory structured audit trail for multi-agent runs."""

from collections import defaultdict, deque
from datetime import datetime, timezone
import logging
from typing import Any, Deque, Dict, List, Optional

from app.orchestration.models import AgentResponse, OrchestrationResult

logger = logging.getLogger(__name__)


class OrchestrationAuditLogger:
    """Thread-safe bounded audit logger for orchestration runs and worker responses."""

    def __init__(self, max_runs: int = 1000, max_runs_per_call: int = 100):
        self._max_runs = max_runs
        self._max_runs_per_call = max_runs_per_call
        self._global_runs: Deque[OrchestrationResult] = deque(maxlen=max_runs)
        self._call_runs: Dict[str, Deque[OrchestrationResult]] = defaultdict(
            lambda: deque(maxlen=self._max_runs_per_call)
        )

    def log_run(self, result: OrchestrationResult) -> None:
        """Record an orchestration run result."""
        self._global_runs.append(result)
        self._call_runs[result.call_id].append(result)
        logger.info(
            f"[AUDIT] Orchestration run completed for call={result.call_id} turn={result.turn_id} "
            f"state={result.state} latency={result.total_latency_ms:.1f}ms agents={len(result.completed_agents)}"
        )

    def get_runs_for_call(self, call_id: str) -> List[OrchestrationResult]:
        """Retrieve all recorded orchestration runs for a specific call."""
        return list(self._call_runs.get(call_id, []))

    def get_latest_run_for_call(self, call_id: str) -> Optional[OrchestrationResult]:
        """Retrieve the most recent orchestration run for a specific call."""
        runs = self._call_runs.get(call_id)
        if runs and len(runs) > 0:
            return runs[-1]
        return None

    def get_recent_runs(self, limit: int = 50) -> List[OrchestrationResult]:
        """Retrieve recent global orchestration runs."""
        runs = list(self._global_runs)
        return runs[-limit:] if limit < len(runs) else runs

    def clear(self) -> None:
        """Clear all audit records (primarily for testing)."""
        self._global_runs.clear()
        self._call_runs.clear()


orchestration_audit_logger = OrchestrationAuditLogger()
