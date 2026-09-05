"""OutputValidator: Policy and schema validation for worker responses."""

import logging
from typing import Any, Dict, List

from app.orchestration.models import (
    AgentRequest,
    AgentResponse,
    AgentSafetyClassification,
    AgentStatus,
)

logger = logging.getLogger(__name__)


class OutputValidator:
    """Validates worker responses against schema, identifiers, and safety policy constraints."""

    # Prohibited claim substrings (diagnosis, legal verdict, emergency dispatch guarantees)
    PROHIBITED_CLAIM_PATTERNS = [
        "clinical diagnosis",
        "i diagnose",
        "guilty of",
        "legal determination",
        "police dispatched immediately",
        "emergency units en route",
    ]

    def validate(self, request: AgentRequest, response: AgentResponse) -> AgentResponse:
        """Validate response against request context and system policies."""
        # 1. Identifier check
        if response.call_id != request.call_id:
            response.status = AgentStatus.FAILED
            response.warnings.append(f"Call ID mismatch: expected {request.call_id}, got {response.call_id}")
            return response

        if response.turn_id != request.turn_id:
            response.status = AgentStatus.FAILED
            response.warnings.append(f"Turn ID mismatch: expected {request.turn_id}, got {response.turn_id}")
            return response

        # 2. Confidence bounding
        if response.confidence < 0.0 or response.confidence > 1.0:
            response.confidence = max(0.0, min(1.0, response.confidence))
            response.warnings.append("Confidence adjusted to [0.0, 1.0] range")

        # 3. Policy constraint: No ungrounded clinical or legal determinations
        result_str = str(response.result).lower()
        for prohibited in self.PROHIBITED_CLAIM_PATTERNS:
            if prohibited in result_str:
                logger.warning(
                    f"Agent {response.agent_name} produced prohibited claim: '{prohibited}'. Sanitizing output."
                )
                response.warnings.append(f"Sanitized prohibited claim pattern: {prohibited}")
                # Sanitize from result text if present
                if isinstance(response.result, dict):
                    sanitized_result = {}
                    for k, v in response.result.items():
                        if isinstance(v, str):
                            sanitized_result[k] = v.replace(prohibited, "[REDACTED_UNAUTHORIZED_CLAIM]")
                        else:
                            sanitized_result[k] = v
                    response.result = sanitized_result

        # 4. Safety State Immutability
        # If an agent that is NOT safety_context_agent attempts to claim 'is_authoritative' safety, strip it
        if response.agent_name != "safety_context_agent":
            if isinstance(response.result, dict) and "is_authoritative" in response.result:
                response.result.pop("is_authoritative", None)
                response.warnings.append("Stripped unauthorized is_authoritative safety flag")

        return response


output_validator = OutputValidator()
