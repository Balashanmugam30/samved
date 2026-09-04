import glob
import json
import logging
import os
import re
import unicodedata
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from app.schemas.safety import (
    SafetyAssessment,
    SafetyEvidence,
    SafetySeverity,
    SafetySignal,
    SafetySignalType,
    SafetyState,
)

logger = logging.getLogger("samved.safety.engine")

# Canonical Negation Tokens across supported languages
NEGATION_TOKENS = {
    "en-IN": [
        "not", "no", "never", "without", "doesn't", "does not", "didn't",
        "did not", "don't", "cannot", "can't", "has no", "have no",
        "is not", "isn't", "nobody", "none", "nothing",
    ],
    "ta-IN": [
        "இல்லை", "இல்ல", "இல்லவே", "இல்லாம", "ille", "illa", "illai", "kidayadhu", "கிடையாது",
    ],
    "hi-IN": [
        "नहीं", "ना", "मत", "nahi", "nahin", "na", "kuch nahi", "कुछ नहीं",
    ],
}

# Temporal Indicators
PAST_TOKENS = [
    "yesterday", "last night", "last week", "last month", "last year", "years ago",
    "months ago", "in the past", "earlier", "previously", "used to",
    "முன்னாடி", "நேத்து", "கடந்த", "முன்பு", "munnadi", "nethu", "munbu", "nadanthathu", "nadandhadhu", "kadantha",
    "पहले", "कल रात", "बीते", "पिछले", "pehle", "kal",
]

HYPOTHETICAL_TOKENS = [
    "if ", "if he", "if they", "what if", "maybe", "might", "in case", "suppose", "assuming",
    "ஒருவேளை", "ஆனா", "oruvelai", "aana",
    "अगर", "शायद", "यदि", "agar", "shaayad",
]

PRESENT_TOKENS = [
    "now", "right now", "currently", "at this moment", "outside right now",
    "இப்போ", "இப்பவே", "இங்க", "ippo", "ippave", "inga",
    "अभी", "इस वक्त", "यहाँ", "abhi", "is waqt", "yahan",
]


class SafetyEngine:
    """Deterministic, explainable, versioned realtime safety engine."""

    def __init__(self, rules_dir: Optional[str] = None):
        self.version = "v1"
        if rules_dir:
            self.rules_dir = Path(rules_dir)
        else:
            self.rules_dir = Path(__file__).resolve().parent.parent / "safety_rules" / "v1"
        self.rules: Dict[str, Dict[str, Any]] = {}
        self._load_rules()

    def _load_rules(self) -> None:
        """Loads all versioned safety rule definition files from the rules directory."""
        self.rules = {}
        if not self.rules_dir.exists():
            logger.warning(f"Safety rules directory {self.rules_dir} does not exist!")
            return

        json_files = glob.glob(str(self.rules_dir / "*.json"))
        for file_path in json_files:
            file_stem = Path(file_path).stem  # e.g. "active_threats", "weapons"
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    rule_list = data if isinstance(data, list) else [data]
                    for r in rule_list:
                        rid = r.get("rule_id")
                        if rid:
                            r["file_stem"] = file_stem
                            self.rules[rid] = r
                    if file_stem and file_stem not in self.rules and rule_list:
                        self.rules[file_stem] = rule_list[0]
            except Exception as e:
                logger.error(f"Failed to load safety rule file {file_path}: {e}")

        logger.info(f"SafetyEngine v1 loaded {len(self.rules)} deterministic safety rules from {self.rules_dir}")

    @property
    def is_ready(self) -> bool:
        return len(self.rules) > 0

    @property
    def rules_count(self) -> int:
        return len(self.rules)

    def normalize_text(self, text: str) -> str:
        """Normalizes Unicode, collapses whitespace, preserves Tamil and Devanagari scripts."""
        if not text:
            return ""
        # Unicode NFC normalization
        normalized = unicodedata.normalize("NFC", text)
        # Collapse multiple spaces, tabs, newlines, and lowercase
        collapsed = re.sub(r"\s+", " ", normalized).strip().lower()
        return collapsed

    def normalize(self, text: str) -> str:
        """Alias for normalize_text."""
        return self.normalize_text(text)

    def is_negated(self, text_normalized: str, match_phrase: str, lang: str = "en-IN") -> bool:
        """Determines if a matched phrase is explicitly negated in the utterance."""
        lower_text = unicodedata.normalize("NFC", text_normalized).lower()
        lower_phrase = unicodedata.normalize("NFC", match_phrase).lower()

        phrase_pos = lower_text.find(lower_phrase)
        if phrase_pos == -1:
            return False

        # Isolate the clause containing the matched phrase using punctuation / sentence breaks
        clause_start = 0
        for m in re.finditer(r"[,;.!?\n]", lower_text[:phrase_pos]):
            clause_start = m.end()

        clause_end = len(lower_text)
        m_next = re.search(r"[,;.!?\n]", lower_text[phrase_pos + len(lower_phrase):])
        if m_next:
            clause_end = phrase_pos + len(lower_phrase) + m_next.start()

        clause_before = lower_text[clause_start:phrase_pos]
        clause_after = lower_text[phrase_pos + len(lower_phrase):clause_end]

        # Restrict word distance: max 5 words before, max 3 words after within this clause
        words_before = clause_before.split()[-5:]
        words_after = clause_after.split()[:3]
        surrounding = f"{' '.join(words_before)} {' '.join(words_after)}"

        all_negations = []
        for tok_list in NEGATION_TOKENS.values():
            for t in tok_list:
                all_negations.append(unicodedata.normalize("NFC", t).lower())

        # Sort longer phrases first
        all_negations.sort(key=len, reverse=True)

        for neg in all_negations:
            if neg.isascii() and neg.isalpha():
                if re.search(rf"\b{re.escape(neg)}\b", surrounding):
                    return True
            else:
                if neg in surrounding:
                    return True
        return False

    def detect_temporal_context(self, text_normalized: str) -> str:
        """Classifies the statement's temporal framing into PRESENT, PAST, or HYPOTHETICAL."""
        lower_text = unicodedata.normalize("NFC", text_normalized).lower()

        # Check hypothetical first
        for hyp in HYPOTHETICAL_TOKENS:
            if hyp in lower_text:
                return "HYPOTHETICAL"

        # Check past
        for past in PAST_TOKENS:
            if past in lower_text:
                return "PAST"

        # Check present
        for pres in PRESENT_TOKENS:
            if pres in lower_text:
                return "PRESENT"

        # Default assumption is PRESENT for ongoing dialogue unless explicitly displaced
        return "PRESENT"

    def classify_temporal(self, text: str) -> str:
        """Alias for detect_temporal_context."""
        return self.detect_temporal_context(self.normalize_text(text))

    def evaluate_turn(
        self,
        utterance_text: str,
        language: str = "en-IN",
        call_id: str = "simulation-call",
        session_id: str = "simulation-session",
        utterance_id: Optional[str] = None,
        recent_context: Optional[List[Dict[str, Any]]] = None,
        previously_fired_signals: Optional[Any] = None,
    ) -> SafetyAssessment:
        """Evaluates an utterance against all deterministic safety rules."""
        norm_text = self.normalize_text(utterance_text)
        temporal = self.detect_temporal_context(norm_text)
        signals: List[SafetySignal] = []
        evidence_refs: List[str] = []

        fired_keys: Set[str] = set()
        if previously_fired_signals is not None:
            if isinstance(previously_fired_signals, set):
                fired_keys = previously_fired_signals
            elif isinstance(previously_fired_signals, list):
                for item in previously_fired_signals:
                    if isinstance(item, str):
                        fired_keys.add(item)
                    elif isinstance(item, dict):
                        rk = item.get("dedup_key") or f"{item.get('rule_id')}:{item.get('matched_phrase', '').lower()}"
                        fired_keys.add(rk)

        if not norm_text:
            return SafetyAssessment(
                call_id=call_id,
                session_id=session_id,
                current_state=SafetyState.NONE,
                highest_severity=SafetySeverity.NONE,
                signals=[],
            )

        lower_norm = norm_text.lower()
        evaluated_rule_ids = set()

        for rule in self.rules.values():
            rule_id = rule.get("rule_id", "UNKNOWN_RULE")
            if rule_id in evaluated_rule_ids:
                continue
            evaluated_rule_ids.add(rule_id)

            rule_version = rule.get("rule_version", "v1")
            category = rule.get("category", "ONGOING_THREAT")
            signal_type_str = rule.get("signal_type", category)
            severity_str = rule.get("severity", "MODERATE")
            reason = rule.get("reason", "Safety rule matched.")
            patterns_dict = rule.get("patterns", {})
            temporal_req = rule.get("temporal_requirement", "ANY")
            negation_sensitive = rule.get("negation_sensitive", True)

            # Skip if temporal requirement is PRESENT but statement is PAST or HYPOTHETICAL
            if temporal_req == "PRESENT" and temporal in ("PAST", "HYPOTHETICAL"):
                continue

            # Gather patterns across caller's language and all languages (supports code-switching)
            all_patterns = []
            if language in patterns_dict:
                all_patterns.extend(patterns_dict[language])
            for lang_key, pats in patterns_dict.items():
                if lang_key != language:
                    all_patterns.extend(pats)

            for pattern in all_patterns:
                pat_clean = pattern.strip()
                pat_lower = pat_clean.lower()
                matched = False

                # Latin tokenized matching
                if pat_lower in lower_norm:
                    matched = True
                # Native script exact substring
                elif pat_clean in norm_text:
                    matched = True

                if matched:
                    # Negation Check
                    if negation_sensitive and self.is_negated(norm_text, pat_clean, language):
                        logger.debug(f"Rule {rule_id} match on '{pat_clean}' negated in '{norm_text}'")
                        continue

                    # Deduplication key
                    dedup_key = f"{rule_id}:{pat_clean.lower()}"
                    if dedup_key in fired_keys:
                        continue
                    fired_keys.add(dedup_key)
                    if isinstance(previously_fired_signals, list):
                        previously_fired_signals.append(dedup_key)

                    try:
                        sig_type = SafetySignalType(signal_type_str)
                    except ValueError:
                        sig_type = SafetySignalType.ONGOING_THREAT

                    try:
                        sev = SafetySeverity(severity_str)
                    except ValueError:
                        sev = SafetySeverity.MODERATE

                    evidence = SafetyEvidence(
                        rule_id=rule_id,
                        rule_version=rule_version,
                        matched_category=category,
                        matched_phrase=pat_clean,
                        reason=reason,
                        source_utterance_id=utterance_id,
                        temporal_context=temporal,
                        negated=False,
                    )

                    signal = SafetySignal(
                        signal_type=sig_type,
                        severity=sev,
                        confidence=1.0,
                        evidence=evidence,
                        rule_id=rule_id,
                        rule_version=rule_version,
                        call_id=call_id,
                        session_id=session_id,
                        utterance_id=utterance_id,
                        requires_human_review=(sev in (SafetySeverity.HIGH, SafetySeverity.CRITICAL)),
                    )
                    signals.append(signal)
                    evidence_refs.append(f"{rule_id}:{pat_clean}")
                    break  # One match per rule is sufficient

        # Compound Logic: Escalation for compound indicators
        # If weapon mention AND active threat / violence occur together, escalate to CRITICAL
        has_weapon = any(s.signal_type in (SafetySignalType.WEAPON_MENTION, SafetySignalType.WEAPON_THREAT) for s in signals)
        has_threat = any(
            s.signal_type in (SafetySignalType.ONGOING_THREAT, SafetySignalType.ACTIVE_VIOLENCE, SafetySignalType.ACTIVE_THREAT, SafetySignalType.STALKING)
            for s in signals
        )
        if has_weapon and has_threat:
            for s in signals:
                if s.signal_type in (SafetySignalType.WEAPON_MENTION, SafetySignalType.WEAPON_THREAT):
                    s.severity = SafetySeverity.CRITICAL
                    s.signal_type = SafetySignalType.WEAPON_THREAT
                    s.requires_human_review = True
                    s.evidence.reason = "Weapon mentioned in active threat / pursuit context (Elevated to CRITICAL)."

        # Determine Highest Severity and Safety State
        all_severities = [s.severity for s in signals]
        if previously_fired_signals:
            for prev in previously_fired_signals:
                if isinstance(prev, dict):
                    sev_str = prev.get("severity")
                    if sev_str:
                        try:
                            all_severities.append(SafetySeverity(sev_str))
                        except ValueError:
                            pass
                elif hasattr(prev, "severity"):
                    all_severities.append(prev.severity)

        if any(s == SafetySeverity.CRITICAL for s in all_severities):
            highest_severity = SafetySeverity.CRITICAL
            current_state = SafetyState.CRITICAL
        elif any(s == SafetySeverity.HIGH for s in all_severities):
            highest_severity = SafetySeverity.HIGH
            current_state = SafetyState.HIGH
        elif any(s == SafetySeverity.MODERATE for s in all_severities):
            highest_severity = SafetySeverity.MODERATE
            current_state = SafetyState.ELEVATED
        elif any(s in (SafetySeverity.LOW, SafetySeverity.INFO) for s in all_severities):
            highest_severity = SafetySeverity.LOW
            current_state = SafetyState.WATCH
        else:
            highest_severity = SafetySeverity.NONE
            current_state = SafetyState.NONE

        return SafetyAssessment(
            call_id=call_id,
            session_id=session_id,
            current_state=current_state,
            highest_severity=highest_severity,
            signals=signals,
            requires_human_review=any(s.requires_human_review for s in signals),
            safety_engine_version=self.version,
            evaluated_at=datetime.now(timezone.utc).isoformat(),
            evidence_refs=evidence_refs,
        )


safety_engine = SafetyEngine()
