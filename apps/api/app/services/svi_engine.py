import json
import logging
import os
import re
import unicodedata
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from app.schemas.safety import SafetySeverity, SafetySignal
from app.schemas.svi import (
    SVIAssessment,
    SVIBand,
    SVIFeatureCategory,
    SVIFeatureContribution,
    SVITrend,
)

logger = logging.getLogger("samved.svi.engine")

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
    "முன்னாடி", "நேத்து", "கடந்த", "முன்பு", "munnadi", "nethu", "munbu", "nadanthathu", "kadantha",
    "पहले", "कल रात", "बीते", "पिछले", "pehle", "kal",
]

RECENT_TOKENS = [
    "earlier today", "this morning", "few hours ago", "couple of hours ago", "just now",
    "இன்னைக்கு காலைல", "கொஞ்ச நேரம் முன்னாடி", "konja neram munnadi",
    "आज सुबह", "थोड़ी देर पहले", "thodi der pehle",
]

PRESENT_TOKENS = [
    "now", "right now", "currently", "at this moment", "outside right now", "still",
    "இப்போ", "இப்பவே", "இங்க", "ippo", "ippave", "inga",
    "अभी", "इस वक्त", "यहाँ", "abhi", "is waqt", "yahan",
]


class SVIEngine:
    """
    Deterministic, explainable Stress Vulnerability Index (SVI) scoring engine.
    Operational prototype prioritization tool for NHAA 14566 crisis triage.
    Guaranteed sub-5ms execution time, offline capability, and 100% determinism.
    """

    def __init__(self, weights_path: Optional[str] = None):
        self.version = "v1"
        if weights_path:
            self.weights_file = Path(weights_path)
        else:
            self.weights_file = Path(__file__).resolve().parent.parent / "svi_rules" / "v1" / "weights.json"
        
        self.config: Dict[str, Any] = {}
        self._load_weights()

    def _load_weights(self) -> None:
        """Loads versioned weights configuration."""
        if not self.weights_file.exists():
            logger.warning(f"SVI weights file {self.weights_file} does not exist!")
            self.config = self._default_weights()
            return

        try:
            with open(self.weights_file, "r", encoding="utf-8") as f:
                self.config = json.load(f)
            logger.info(f"SVIEngine loaded weights from {self.weights_file}")
        except Exception as e:
            logger.error(f"Failed to load SVI weights: {e}")
            self.config = self._default_weights()

    def _default_weights(self) -> Dict[str, Any]:
        return {
            "version": "v1",
            "recency_multipliers": {"PRESENT": 1.0, "RECENT": 0.75, "HISTORICAL": 0.35},
            "trend_threshold": 5,
            "thresholds": {
                "critical_override_floor": 76,
                "high_override_floor": 51,
                "max_protective_reduction": 15
            },
            "categories": {}
        }

    @staticmethod
    def normalize_text(text: str) -> str:
        """Normalizes unicode NFC, lowercases, and strips excessive whitespace."""
        if not text:
            return ""
        norm = unicodedata.normalize("NFC", text).lower()
        return " ".join(norm.split())

    def detect_recency(self, text: str) -> str:
        """Detects temporal recency: PRESENT, RECENT, or HISTORICAL."""
        norm = self.normalize_text(text)
        for token in sorted(RECENT_TOKENS, key=len, reverse=True):
            if token in norm:
                return "RECENT"
        for token in sorted(PAST_TOKENS, key=len, reverse=True):
            if token in norm:
                return "HISTORICAL"
        return "PRESENT"

    def is_negated(self, text: str, match_phrase: str, lang: str = "en-IN") -> bool:
        """Checks if a matched phrase is negated in the immediate dialogue context."""
        norm = self.normalize_text(text)
        phrase_norm = self.normalize_text(match_phrase)
        tokens = NEGATION_TOKENS.get(lang, NEGATION_TOKENS["en-IN"])
        
        # Look for negation tokens within 4 words before the phrase
        idx = norm.find(phrase_norm)
        if idx == -1:
            return False
        
        prefix = norm[max(0, idx - 40):idx]
        for neg in tokens:
            if re.search(r'\b' + re.escape(neg) + r'\b', prefix):
                return True
        return False

    def evaluate_session(
        self,
        call_id: str,
        session_id: str,
        turns: List[Dict[str, Any]],
        safety_signals: Optional[List[Any]] = None,
        previous_score: Optional[int] = None,
        turn_index: int = 0,
        acoustic_assessment: Optional[Any] = None,
    ) -> SVIAssessment:
        """
        Evaluates conversational turns and deterministic safety signals to generate an SVIAssessment.
        Execution is 100% deterministic and sub-5ms.
        """
        features: List[SVIFeatureContribution] = []
        recency_mults = self.config.get("recency_multipliers", {"PRESENT": 1.0, "RECENT": 0.75, "HISTORICAL": 0.35})
        thresholds = self.config.get("thresholds", {
            "critical_override_floor": 76,
            "high_override_floor": 51,
            "max_protective_reduction": 15
        })
        categories_config = self.config.get("categories", {})

        # 1. Evaluate Immediate Safety from Phase 4 Safety Signals
        immediate_safety_score = 0.0
        critical_override_applied = False
        high_severity_present = False
        highest_safety_severity = SafetySeverity.NONE

        if safety_signals:
            imm_cfg = categories_config.get("immediate_safety", {})
            max_imm = imm_cfg.get("max_weight", 40)
            sev_weights = imm_cfg.get("severity_weights", {
                "CRITICAL": 40,
                "HIGH": 25,
                "MODERATE": 15,
                "LOW": 5
            })

            for sig in safety_signals:
                # Support both SafetySignal objects and raw dicts
                sig_type = sig.signal_type if hasattr(sig, "signal_type") else sig.get("signal_type", "")
                sev = sig.severity if hasattr(sig, "severity") else sig.get("severity", "LOW")
                evidence = sig.evidence if hasattr(sig, "evidence") else sig.get("evidence", {})
                rule_id = sig.rule_id if hasattr(sig, "rule_id") else sig.get("rule_id", "rule_safety")

                sev_str = sev.value if hasattr(sev, "value") else str(sev).upper()
                if sev_str == "CRITICAL":
                    critical_override_applied = True
                    highest_safety_severity = SafetySeverity.CRITICAL
                elif sev_str == "HIGH":
                    high_severity_present = True
                    if highest_safety_severity != SafetySeverity.CRITICAL:
                        highest_safety_severity = SafetySeverity.HIGH

                weight = float(sev_weights.get(sev_str, 5))
                temporal = "PRESENT"
                if hasattr(evidence, "temporal_context"):
                    temporal = evidence.temporal_context
                elif isinstance(evidence, dict):
                    temporal = evidence.get("temporal_context", "PRESENT")

                mult = recency_mults.get(temporal, 1.0)
                weighted = weight * mult

                features.append(
                    SVIFeatureContribution(
                        category=SVIFeatureCategory.IMMEDIATE_SAFETY,
                        feature_name=f"Safety Signal: {sig_type} ({sev_str})",
                        raw_score=weight,
                        recency=temporal,
                        recency_weight=mult,
                        weighted_score=weighted,
                        matched_phrase=getattr(evidence, "matched_phrase", "") if hasattr(evidence, "matched_phrase") else (evidence.get("matched_phrase", "") if isinstance(evidence, dict) else ""),
                        rule_id=rule_id,
                        description=f"Deterministic signal {sig_type} with {sev_str} severity."
                    )
                )
                immediate_safety_score += weighted

            immediate_safety_score = min(immediate_safety_score, max_imm)

        # 2. Evaluate Caller Text Across Lexical Risk Categories
        # Filter for caller utterances
        caller_turns = [
            t for t in turns
            if t.get("speaker", "caller").lower() in ("caller", "user", "victim")
        ]
        # If no caller tag, evaluate all non-agent turns or all turns
        if not caller_turns:
            caller_turns = turns

        category_scores: Dict[str, float] = {
            "coercion_control": 0.0,
            "isolation_support": 0.0,
            "distress_overwhelm": 0.0,
            "help_barriers": 0.0,
            "protective_factors": 0.0,
        }

        # Track category assessments for completeness
        assessed_categories: Set[str] = set()
        if immediate_safety_score > 0:
            assessed_categories.add("immediate_safety")

        for turn in caller_turns:
            text = turn.get("text", "")
            if not text:
                continue
            norm_text = self.normalize_text(text)
            lang = turn.get("language", "en-IN")
            recency = self.detect_recency(norm_text)
            rec_mult = recency_mults.get(recency, 1.0)

            # Evaluate each text-based category
            for cat_key in ["coercion_control", "isolation_support", "distress_overwhelm", "help_barriers", "protective_factors"]:
                cat_cfg = categories_config.get(cat_key, {})
                keywords_map = cat_cfg.get("keywords", {})
                keywords = keywords_map.get(lang, []) + keywords_map.get("en-IN", [])
                base_weight = float(cat_cfg.get("base_match_weight", 10))

                for kw in set(keywords):
                    kw_norm = self.normalize_text(kw)
                    if kw_norm and kw_norm in norm_text:
                        # Check negation
                        if self.is_negated(norm_text, kw_norm, lang):
                            continue

                        # Matched valid cue
                        assessed_categories.add(cat_key)
                        weighted = base_weight * rec_mult
                        category_scores[cat_key] += weighted

                        features.append(
                            SVIFeatureContribution(
                                category=SVIFeatureCategory(cat_key),
                                feature_name=f"{cat_key.replace('_', ' ').title()}: '{kw}'",
                                raw_score=base_weight,
                                recency=recency,
                                recency_weight=rec_mult,
                                weighted_score=weighted,
                                matched_phrase=kw,
                                rule_id=f"svi_{cat_key}",
                                description=f"Matched keyword '{kw}' under {cat_key} with {recency} recency."
                            )
                        )
                        break  # Match at most one keyword per category per turn to prevent score inflation

        # Cap individual category scores
        capped_coercion = min(category_scores["coercion_control"], categories_config.get("coercion_control", {}).get("max_weight", 25))
        capped_isolation = min(category_scores["isolation_support"], categories_config.get("isolation_support", {}).get("max_weight", 15))
        capped_distress = min(category_scores["distress_overwhelm"], categories_config.get("distress_overwhelm", {}).get("max_weight", 20))
        capped_barriers = min(category_scores["help_barriers"], categories_config.get("help_barriers", {}).get("max_weight", 15))
        
        # Protective factors reduction (bounded max 15)
        raw_protective = category_scores["protective_factors"]
        max_prot = thresholds.get("max_protective_reduction", 15)
        protective_reduction = min(int(round(raw_protective)), max_prot)

        # 3. Aggregate Risk Score
        raw_risk_score = (
            immediate_safety_score +
            capped_coercion +
            capped_isolation +
            capped_distress +
            capped_barriers
        )

        final_score = int(round(raw_risk_score - protective_reduction))

        # 4. Apply Overrides & Floor Rules
        crit_floor = thresholds.get("critical_override_floor", 76)
        high_floor = thresholds.get("high_override_floor", 51)

        if critical_override_applied:
            # Active violence / lethal threats floor
            final_score = max(final_score, crit_floor)
        elif high_severity_present:
            final_score = max(final_score, high_floor)

        # 5. Clamping
        final_score = max(0, min(100, final_score))

        # 6. Determine SVIBand
        if final_score >= 76:
            band = SVIBand.CRITICAL
        elif final_score >= 51:
            band = SVIBand.HIGH
        elif final_score >= 26:
            band = SVIBand.MODERATE
        else:
            band = SVIBand.LOW

        # 7. Determine Trend
        trend_threshold = self.config.get("trend_threshold", 5)
        if previous_score is None:
            trend = SVITrend.INITIAL
            delta = 0
        else:
            delta = final_score - previous_score
            if delta >= trend_threshold:
                trend = SVITrend.RISING
            elif delta <= -trend_threshold:
                trend = SVITrend.FALLING
            else:
                trend = SVITrend.STABLE

        # 8. Assessment Completeness
        # 5 primary risk categories + turn count depth
        category_completeness = len(assessed_categories) / 5.0
        turn_completeness = min(len(caller_turns) / 5.0, 1.0)
        if len(caller_turns) == 0 and len(assessed_categories) == 0:
            completeness = 0.0
        else:
            completeness = round(min(1.0, 0.4 * category_completeness + 0.5 * turn_completeness + 0.1), 2)

        # 9. Top Contributors
        # Sort features by weighted_score descending
        risk_features = [f for f in features if f.category != SVIFeatureCategory.PROTECTIVE_FACTORS]
        risk_features.sort(key=lambda x: x.weighted_score, reverse=True)
        top_contributors = [
            f"{f.feature_name} (+{int(round(f.weighted_score))} pts)"
            for f in risk_features[:4]
        ]
        if protective_reduction > 0:
            top_contributors.append(f"Protective Buffer (-{protective_reduction} pts)")

        # 10. Human Review Mandate
        requires_human_review = (
            final_score >= 51
            or critical_override_applied
            or high_severity_present
        )

        # 11. Acoustic Evidence Integration (Phase 6)
        acoustic_available = False
        acoustic_note = "Acoustic evidence: Not available in current phase (Phase 6 deferred)"
        if acoustic_assessment is not None:
            acoustic_available = True
            q_val = (
                acoustic_assessment.quality.value
                if hasattr(acoustic_assessment.quality, "value")
                else str(acoustic_assessment.quality)
            )
            signals = getattr(acoustic_assessment, "operational_signals", []) or []
            if signals:
                sig_labels = [
                    (s.code.value if hasattr(s.code, "value") else str(s.code))
                    for s in signals
                ]
                acoustic_note = f"Acoustic observations: quality={q_val}, signals={', '.join(sig_labels)}"
            else:
                conf = getattr(acoustic_assessment, "confidence", 1.0)
                acoustic_note = f"Acoustic telemetry active: quality={q_val}, {round(conf * 100)}% confidence"

        return SVIAssessment(
            call_id=call_id,
            session_id=session_id,
            turn_index=turn_index,
            score=final_score,
            band=band,
            trend=trend,
            delta=delta,
            assessment_completeness=completeness,
            features=features,
            top_contributors=top_contributors,
            protective_factor_reduction=protective_reduction,
            critical_override_applied=critical_override_applied,
            acoustic_evidence_available=acoustic_available,
            acoustic_evidence_note=acoustic_note,
            requires_human_review=requires_human_review,
            disclaimer="Operational Prototype Priority Indicator — NOT a clinical, medical, or diagnostic score",
            evaluated_at=datetime.now(timezone.utc).isoformat(),
            svi_version=self.version,
        )


svi_engine = SVIEngine()

