"""Response Validator for verifying LLM output conforms to adaptive strategy constraints."""

import re
from typing import Tuple

from app.adaptive.models import ConversationStrategy
from app.adaptive.response_policy import get_response_policy


class ResponseValidator:
    """Validates synthesized or LLM-generated phrasing against strategy constraints."""

    # Prohibited claims
    PROHIBITED_PATTERNS = [
        r"(police (is|are) (dispatched|on the way|coming|arriving))",
        r"(ambulance (is|has been) (dispatched|sent|on the way))",
        r"(you are diagnosed with|clinical (addiction|diagnosis)|you have (clinical|severe) (addiction|depression|psychiatric)|psychiatric disorder)",
        r"(our lie detector shows|you are lying|untruthful statement)",
        r"(court will find you guilty|legal conviction|statutory crime)",
    ]

    @classmethod
    def validate_response(
        cls,
        text: str,
        strategy: ConversationStrategy,
    ) -> Tuple[bool, str, str]:
        """Validates response text against strategy.

        Returns:
            Tuple[is_valid, validation_reason, final_text]
            If invalid, final_text is replaced by the deterministic fallback template.
        """
        policy = get_response_policy(strategy.action)
        fallback = policy.get_fallback(strategy.language)

        if not text or not text.strip():
            return False, "Response was empty", fallback

        cleaned = text.strip()

        # 1. Word count limit for telephone TTS (max 45 words)
        words = cleaned.split()
        if len(words) > 45:
            return False, f"Response exceeds telephone length limit ({len(words)} words > 45)", fallback

        # 2. Check prohibited claims
        for pat in cls.PROHIBITED_PATTERNS:
            if re.search(pat, cleaned, re.IGNORECASE):
                return False, f"Response contains prohibited claim matching pattern: {pat}", fallback

        # 3. Check question count
        # In English, Tamil, and Hindi, questions end with ?
        question_count = len(re.findall(r"\?", cleaned))
        if policy.max_questions == 0 and question_count > 0:
            # Policy explicitly forbids questions for this action
            return False, f"Action {strategy.action.value} requires 0 questions, found {question_count}", fallback

        if policy.max_questions == 1 and question_count > 1:
            return False, f"Action {strategy.action.value} allows max 1 question, found {question_count}", fallback

        return True, "Valid", cleaned
