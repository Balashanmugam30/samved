"""AgentRegistry for SAMVED Phase 9 Multi-Agent Orchestration."""

import logging
from typing import Dict, List, Optional

from app.orchestration.contracts import BaseAgentWorker
from app.orchestration.models import AgentSafetyClassification, AgentSpec
from app.orchestration.workers import (
    AcousticContextAgent,
    CaseGraphExtractionAgent,
    ConversationContextAgent,
    FollowupRecommendationAgent,
    KnowledgeRetrievalAgent,
    LanguageContextAgent,
    OperatorBriefingAgent,
    SafetyContextAgent,
    SupportOptionsAgent,
)

logger = logging.getLogger(__name__)


class AgentRegistry:
    """Registry maintaining active agent worker instances and their specs."""

    def __init__(self, register_defaults: bool = True):
        self._workers: Dict[str, BaseAgentWorker] = {}
        if register_defaults:
            self._register_default_workers()

    def _register_default_workers(self) -> None:
        """Register the built-in Phase 9, Phase 10, Phase 11, and Phase 12 worker agents."""
        defaults = [
            SafetyContextAgent(),
            AcousticContextAgent(),
            LanguageContextAgent(),
            ConversationContextAgent(),
            SupportOptionsAgent(),
            KnowledgeRetrievalAgent(),
            CaseGraphExtractionAgent(),
            FollowupRecommendationAgent(),
            OperatorBriefingAgent(),
        ]
        for worker in defaults:
            self.register(worker)

    def register(self, worker: BaseAgentWorker) -> None:
        """Register an agent worker."""
        if worker.name in self._workers:
            logger.warning(f"Overwriting existing agent in registry: {worker.name}")
        self._workers[worker.name] = worker
        logger.info(f"Registered agent worker: {worker.name} (v{worker.spec.version})")

    def unregister(self, name: str) -> Optional[BaseAgentWorker]:
        """Unregister an agent worker by name."""
        worker = self._workers.pop(name, None)
        if worker:
            logger.info(f"Unregistered agent worker: {name}")
        return worker

    def get(self, name: str) -> Optional[BaseAgentWorker]:
        """Get an agent worker by name."""
        return self._workers.get(name)

    def is_registered(self, name: str) -> bool:
        """Check if an agent is registered."""
        return name in self._workers

    def list_agents(self) -> List[AgentSpec]:
        """List specs of all registered workers."""
        return [worker.spec for worker in self._workers.values()]

    def get_agents_by_capability(self, capability: str) -> List[BaseAgentWorker]:
        """Find all registered workers supporting a specific capability."""
        return [
            worker
            for worker in self._workers.values()
            if worker.spec.enabled and capability in worker.spec.capabilities
        ]

    def get_agents_by_safety_classification(
        self, classification: AgentSafetyClassification
    ) -> List[BaseAgentWorker]:
        """Find registered workers by safety classification."""
        return [
            worker
            for worker in self._workers.values()
            if worker.spec.enabled and worker.spec.safety_classification == classification
        ]

    def all_capabilities(self) -> List[str]:
        """List all unique capabilities provided by active agents."""
        caps = set()
        for worker in self._workers.values():
            if worker.spec.enabled:
                caps.update(worker.spec.capabilities)
        return sorted(list(caps))


# Global default registry instance
agent_registry = AgentRegistry(register_defaults=True)
