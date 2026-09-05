"""Operator Training Sandbox for SAMVED Phase 14.

Provides interactive tele-counselor simulation drills with real-time SOP scoring,
de-escalation feedback, empathy analysis, and protocol compliance tracking.
"""

from datetime import datetime, timezone
import logging
import re
from typing import Dict, List, Optional
import uuid

from app.simulation.models import (
    DrillDifficulty,
    SyntheticDialogueTurn,
    TrainingDrill,
    TrainingSession,
    TrainingTurnEvaluation,
)

logger = logging.getLogger("samved.simulation.sandbox")

# ---------------------------------------------------------------------------
# Curated Training Drills
# ---------------------------------------------------------------------------

CURATED_DRILLS: List[TrainingDrill] = [
    TrainingDrill(
        drill_key="DRILL-OVERDOSE-001",
        title="Critical Opioid Overdose Rapid Intake",
        category="CRITICAL_TRIAGE",
        difficulty=DrillDifficulty.EXPERT,
        language="en-IN",
        description="Caller reports an unresponsive roommate after heroin use. Trainee must instruct recovery position and execute immediate emergency ambulance handover.",
        scenario_context="Emergency call at 02:15 AM. Caller is panicked. Patient is unconscious with shallow breathing.",
        expected_competencies=[
            "Emergency Escalation Protocol",
            "Recovery Position Instruction",
            "Calming Pacing under Panic",
            "No Stigmatizing Language",
        ],
        turns=[
            SyntheticDialogueTurn(
                turn=1,
                speaker="caller",
                text="Help! My roommate took something white an hour ago and now he won't wake up! His lips look bluish and he's breathing very slowly!",
                language="en-IN",
            ),
            SyntheticDialogueTurn(
                turn=2,
                speaker="caller",
                text="Okay I turned him on his side like you said! But he is still not answering me. Should I give him water? When is the ambulance coming?!",
                language="en-IN",
            ),
        ],
    ),
    TrainingDrill(
        drill_key="DRILL-WITHDRAWAL-002",
        title="Acute Opioid Withdrawal & Housing Dislocation",
        category="WITHDRAWAL_COUNSELING",
        difficulty=DrillDifficulty.INTERMEDIATE,
        language="hi-IN",
        description="Caller undergoing severe chills, vomiting, and tremors after being evicted by family. Trainee must offer immediate medical detox referral.",
        scenario_context="Inbound call from street corner in Delhi. Caller is physically suffering and feels abandoned.",
        expected_competencies=[
            "Medical Detox Referral",
            "Empathy and Validation",
            "Shelter/IRCA Navigation",
            "De-escalation of Helplessness",
        ],
        turns=[
            SyntheticDialogueTurn(
                turn=1,
                speaker="caller",
                text="Mera shareer kaanp raha hai, ulti aa rahi hai aur ghar waalon ne ghar se nikaal diya. Mujhe lagta hai main ab mar jaunga.",
                language="hi-IN",
            ),
            SyntheticDialogueTurn(
                turn=2,
                speaker="caller",
                text="Kya sarkaari hospital me bina police ke ilaaj mil jayega? Mujhe dar lag raha hai ki mujhe arrest kar lenge.",
                language="hi-IN",
            ),
        ],
    ),
    TrainingDrill(
        drill_key="DRILL-CODESWITCH-003",
        title="Tanglish Peer Pressure & Relapse Anxiety",
        category="RELAPSE_PREVENTION",
        difficulty=DrillDifficulty.INTERMEDIATE,
        language="ta-IN",
        description="College student code-switching in Tamil and English worried about exam relapse and intense cravings.",
        scenario_context="Student calling from hostel room feeling anxious and isolated.",
        expected_competencies=[
            "Multilingual Attunement",
            "Craving Delay Techniques",
            "Non-judgmental Tone",
            "Confidentiality Assurance",
        ],
        turns=[
            SyntheticDialogueTurn(
                turn=1,
                speaker="caller",
                text="Vanakkam sir, I am feeling very anxious. Friends are forcing me to use ganja again and tomorrow is my semester exam.",
                language="ta-IN",
            ),
            SyntheticDialogueTurn(
                turn=2,
                speaker="caller",
                text="If I say no, they will mock me and isolate me from the project group. Enakku enna panradhu nu theriyala.",
                language="ta-IN",
            ),
        ],
    ),
    TrainingDrill(
        drill_key="DRILL-NEGATION-004",
        title="Ambiguous Statement & Negation Clarification",
        category="RISK_CALIBRATION",
        difficulty=DrillDifficulty.ADVANCED,
        language="en-IN",
        description="Caller uses ambiguous phrases ('I can't take this anymore') but explicitly clarifies they are NOT suicidal. Trainee must avoid over-escalation.",
        scenario_context="Exhausted caregiver calling regarding chronic insomnia and burnout.",
        expected_competencies=[
            "Precise Risk Differentiation",
            "Avoiding Panic/False Escalation",
            "Active Listening",
            "Caregiver Burnout Support",
        ],
        turns=[
            SyntheticDialogueTurn(
                turn=1,
                speaker="caller",
                text="I just want to clarify: I am NOT going to hurt myself, I don't want to die. I am just totally exhausted from caring for my addicted husband.",
                language="en-IN",
            ),
            SyntheticDialogueTurn(
                turn=2,
                speaker="caller",
                text="Thank you for listening. Where can I find support groups for families going through this?",
                language="en-IN",
            ),
        ],
    ),
]


class TrainingSandbox:
    """Manages training drills and evaluates trainee responses in real-time."""

    def __init__(self, drills: Optional[List[TrainingDrill]] = None):
        self._drills: Dict[str, TrainingDrill] = {}
        for d in drills or CURATED_DRILLS:
            self._drills[d.drill_key] = d
        self._sessions: Dict[str, TrainingSession] = {}

    def list_drills(self, difficulty: Optional[str] = None) -> List[TrainingDrill]:
        drills = list(self._drills.values())
        if difficulty:
            drills = [d for d in drills if d.difficulty.value.upper() == difficulty.upper()]
        return drills

    def get_drill(self, drill_key: str) -> Optional[TrainingDrill]:
        return self._drills.get(drill_key)

    def start_session(self, drill_key: str, trainee_id: str = "T-1001", trainee_name: str = "Counselor Trainee") -> TrainingSession:
        drill = self.get_drill(drill_key)
        if not drill:
            raise ValueError(f"Drill {drill_key} not found")

        session_id = f"TRN-{uuid.uuid4().hex[:8].upper()}"
        session = TrainingSession(
            session_id=session_id,
            drill_id=drill.id,
            trainee_id=trainee_id,
            trainee_name=trainee_name,
            status="ACTIVE",
            current_turn=1,
            total_turns=len(drill.turns),
            evaluated_turns=[],
        )
        self._sessions[session_id] = session
        return session

    def evaluate_trainee_turn(
        self, session_id: str, trainee_input: str
    ) -> TrainingTurnEvaluation:
        """Evaluates a single trainee turn against SOP rubrics with explainable feedback."""
        session = self._sessions.get(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")

        drill = next((d for d in self._drills.values() if d.id == session.drill_id), None)
        if not drill:
            raise ValueError("Associated drill not found")

        turn_idx = session.current_turn - 1
        current_caller_turn = drill.turns[turn_idx] if turn_idx < len(drill.turns) else drill.turns[-1]
        next_caller_turn = drill.turns[turn_idx + 1].text if turn_idx + 1 < len(drill.turns) else None

        input_lower = trainee_input.lower()
        hints: List[str] = []

        # 1. Safety Protocol Adherence (Max 35 points)
        safety_score = 15.0  # baseline
        emergency_cues = ["emergency", "ambulance", "hospital", "doctor", "police", "handover", "connect", "surakshit", "madad"]
        recovery_cues = ["recovery position", "side", "turn", "head", "breathing", "padkhe", "saah"]
        
        has_emergency = any(c in input_lower for c in emergency_cues)
        has_recovery = any(c in input_lower for c in recovery_cues)

        if "CRITICAL" in drill.category or "OVERDOSE" in drill.drill_key:
            if has_emergency and has_recovery:
                safety_score = 35.0
                hints.append("Excellent rapid triage: instructed recovery position and triggered emergency handover.")
            elif has_emergency:
                safety_score = 28.0
                hints.append("Good emergency handover, but remember to instruct recovery position for unresponsive caller.")
            else:
                safety_score = 10.0
                hints.append("Critical safety missed: Always prioritize immediate ambulance/emergency handover for overdose signs.")
        else:
            safety_score = 30.0 if has_emergency else 25.0

        # 2. Empathy & Active Listening (Max 25 points)
        empathy_score = 15.0
        empathy_cues = ["understand", "help", "safe", "stay with you", "not alone", "gopaniya", "ghabraiye mat", "aapki jaan", "saath hain", "kavalai"]
        has_empathy = any(c in input_lower for c in empathy_cues)
        
        # Penalize blaming/stigmatizing words
        stigmatizing_cues = ["your fault", "addict", "nashedi", "criminal", "why did you take", "arrest"]
        has_stigma = any(c in input_lower for c in stigmatizing_cues)

        if has_stigma:
            empathy_score = 5.0
            hints.append("Avoid stigmatizing language or assigning blame. Use person-first, supportive phrasing.")
        elif has_empathy:
            empathy_score = 25.0
            hints.append("Strong empathetic reassurance and non-judgmental presence.")
        else:
            empathy_score = 18.0
            hints.append("Consider opening with explicit validation (e.g. 'We are here with you, you are safe now').")

        # 3. De-escalation & Pacing (Max 20 points)
        de_escalation_score = 12.0
        calming_cues = ["calm", "breathe", "slow", "line", "stay on", "dhyan", "aaram", "saans", "wait"]
        if any(c in input_lower for c in calming_cues):
            de_escalation_score = 20.0
            hints.append("Calming vocal cues and structured pacing helped stabilize the caller.")
        else:
            de_escalation_score = 14.0

        # 4. Statutory & Referral Accuracy (Max 20 points)
        referral_score = 10.0
        referral_cues = ["irca", "rehab", "detox", "counselor", "center", "section 64a", "voluntary", "hospital", "helpline", "kendra"]
        if any(c in input_lower for c in referral_cues):
            referral_score = 20.0
            hints.append("Accurate service and treatment referral guidance provided.")
        else:
            referral_score = 12.0
            hints.append("Guide the caller toward structured care (e.g. government-funded IRCA center or tele-counselor).")

        total_score = min(100.0, round(safety_score + empathy_score + de_escalation_score + referral_score, 1))

        turn_eval = TrainingTurnEvaluation(
            turn_number=session.current_turn,
            trainee_input=trainee_input,
            score=total_score,
            safety_protocol_score=safety_score,
            empathy_score=empathy_score,
            de_escalation_score=de_escalation_score,
            statutory_referral_score=referral_score,
            feedback_hints=hints,
            caller_next_turn=next_caller_turn,
        )

        session.evaluated_turns.append(turn_eval)

        # Advance turn or complete
        if session.current_turn >= session.total_turns:
            self._finalize_session(session)
        else:
            session.current_turn += 1

        return turn_eval

    def _finalize_session(self, session: TrainingSession) -> None:
        """Computes aggregate scores, ratings, and recommendations upon drill completion."""
        session.status = "COMPLETED"
        session.completed_at = datetime.now(timezone.utc)

        if not session.evaluated_turns:
            session.overall_score = 0.0
            session.performance_rating = "NEEDS_IMPROVEMENT"
            return

        scores = [t.score for t in session.evaluated_turns]
        avg_score = round(sum(scores) / len(scores), 1)
        session.overall_score = avg_score

        # Rating bands
        if avg_score >= 90.0:
            rating = "EXEMPLARY"
        elif avg_score >= 75.0:
            rating = "PROFICIENT"
        elif avg_score >= 60.0:
            rating = "DEVELOPING"
        else:
            rating = "NEEDS_IMPROVEMENT"
        session.performance_rating = rating

        # Competency breakdown
        mean_safety = round(sum(t.safety_protocol_score for t in session.evaluated_turns) / len(scores), 1)
        mean_empathy = round(sum(t.empathy_score for t in session.evaluated_turns) / len(scores), 1)
        mean_deesc = round(sum(t.de_escalation_score for t in session.evaluated_turns) / len(scores), 1)
        mean_referral = round(sum(t.statutory_referral_score for t in session.evaluated_turns) / len(scores), 1)

        session.competency_breakdown = {
            "safety_protocol": mean_safety,
            "empathy_and_listening": mean_empathy,
            "de_escalation_pacing": mean_deesc,
            "referral_accuracy": mean_referral,
        }

        recs = []
        if mean_safety < 28.0:
            recs.append("Review Phase 4 Deterministic Safety guidelines for rapid overdose and self-harm identification.")
        if mean_empathy < 20.0:
            recs.append("Practice person-first, trauma-informed active listening vocabulary.")
        if mean_referral < 15.0:
            recs.append("Familiarize with MoSJE NAPDDR IRCA directories and Section 64A voluntary treatment protections.")
        if not recs:
            recs.append("Demonstrated high competency across all core helpline triage domains. Ready for supervised live calls.")

        session.recommendations = recs

    def get_session(self, session_id: str) -> Optional[TrainingSession]:
        return self._sessions.get(session_id)


training_sandbox = TrainingSandbox()
