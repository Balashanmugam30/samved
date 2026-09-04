"""Response Policy layer defining constraints, tone, and boundaries per action."""

from typing import Dict, List
from pydantic import BaseModel, Field

from app.adaptive.models import AdaptiveAction
from app.adaptive.templates import get_template


class ActionResponsePolicy(BaseModel):
    action: AdaptiveAction
    purpose: str
    max_questions: int = 1
    tone: str
    allowed_structure: str
    forbidden_content: List[str] = Field(
        default_factory=lambda: [
            "police dispatched",
            "police on the way",
            "emergency ambulance dispatched",
            "you have clinical addiction",
            "you are diagnosed with",
            "according to lie detection",
            "you are lying",
            "guilty of an offense",
        ]
    )

    def get_fallback(self, language: str = "en-IN") -> str:
        return get_template(self.action, language)


POLICY_CATALOG: Dict[AdaptiveAction, ActionResponsePolicy] = {
    AdaptiveAction.SAFETY_CHECK: ActionResponsePolicy(
        action=AdaptiveAction.SAFETY_CHECK,
        purpose="Verify caller immediate physical safety in calm, direct manner.",
        max_questions=1,
        tone="calm, grounding, direct",
        allowed_structure="1 reassuring sentence followed by 1 immediate safety question.",
    ),
    AdaptiveAction.ASK_IMMEDIATE_DANGER: ActionResponsePolicy(
        action=AdaptiveAction.ASK_IMMEDIATE_DANGER,
        purpose="Clarify if immediate physical threat or violence is active.",
        max_questions=1,
        tone="direct, alert, composed",
        allowed_structure="1 concise immediate danger verification question.",
    ),
    AdaptiveAction.ASK_SAFE_TO_CONTINUE: ActionResponsePolicy(
        action=AdaptiveAction.ASK_SAFE_TO_CONTINUE,
        purpose="Ensure caller can speak privately without putting themselves at risk.",
        max_questions=1,
        tone="protective, cautious, gentle",
        allowed_structure="1 question asking if it is safe to continue on the phone.",
    ),
    AdaptiveAction.ASK_LOCATION: ActionResponsePolicy(
        action=AdaptiveAction.ASK_LOCATION,
        purpose="Ascertain city or district for operator referral purposes.",
        max_questions=1,
        tone="respectful, operational",
        allowed_structure="1 question inquiring about general city or district.",
    ),
    AdaptiveAction.ASK_SUPPORT: ActionResponsePolicy(
        action=AdaptiveAction.ASK_SUPPORT,
        purpose="Inquire about presence of trusted family or friend nearby to reduce overwhelm.",
        max_questions=1,
        tone="empathetic, gentle",
        allowed_structure="1 supportive inquiry about nearby trusted individuals.",
    ),
    AdaptiveAction.ASK_RECENCY: ActionResponsePolicy(
        action=AdaptiveAction.ASK_RECENCY,
        purpose="Distinguish acute today crisis from chronic ongoing situation.",
        max_questions=1,
        tone="attentive, clarifying",
        allowed_structure="1 timeline clarifying question.",
    ),
    AdaptiveAction.ASK_PREFERENCE: ActionResponsePolicy(
        action=AdaptiveAction.ASK_PREFERENCE,
        purpose="Ask caller their preferred mode of assistance.",
        max_questions=1,
        tone="empowering, respectful",
        allowed_structure="1 concise preference choice question.",
    ),
    AdaptiveAction.ASK_NEXT_STEP: ActionResponsePolicy(
        action=AdaptiveAction.ASK_NEXT_STEP,
        purpose="Inquire what immediate next step caller feels would be most helpful.",
        max_questions=1,
        tone="supportive, collaborative",
        allowed_structure="1 open, forward-looking question.",
    ),
    AdaptiveAction.OFFER_OPTIONS: ActionResponsePolicy(
        action=AdaptiveAction.OFFER_OPTIONS,
        purpose="Present clear helpline support tracks (de-addiction, counseling, legal).",
        max_questions=1,
        tone="informative, structured",
        allowed_structure="Brief options followed by preference question.",
    ),
    AdaptiveAction.PROVIDE_BRIEF_GUIDANCE: ActionResponsePolicy(
        action=AdaptiveAction.PROVIDE_BRIEF_GUIDANCE,
        purpose="Provide concise statutory helpline informational guidance.",
        max_questions=0,
        tone="authoritative, helpful, calm",
        allowed_structure="1 to 2 informative non-judgmental sentences.",
    ),
    AdaptiveAction.ALLOW_SILENCE: ActionResponsePolicy(
        action=AdaptiveAction.ALLOW_SILENCE,
        purpose="Give caller unpressured space to compose themselves or breathe.",
        max_questions=0,
        tone="patient, unhurried, reassuring",
        allowed_structure="1 reassuring sentence indicating listener presence.",
    ),
    AdaptiveAction.CLARIFY_AUDIO: ActionResponsePolicy(
        action=AdaptiveAction.CLARIFY_AUDIO,
        purpose="Request repetition gracefully due to telephony packet loss or acoustic noise.",
        max_questions=1,
        tone="polite, humble",
        allowed_structure="1 apology for audio quality and request to repeat.",
    ),
    AdaptiveAction.HUMAN_HANDOFF: ActionResponsePolicy(
        action=AdaptiveAction.HUMAN_HANDOFF,
        purpose="Initiate warm transition to human tele-counselor.",
        max_questions=0,
        tone="warm, reassuring, definitive",
        allowed_structure="1 sentence informing caller of human counselor connection.",
    ),
    AdaptiveAction.PAUSE_ADAPTIVE_QUESTIONS: ActionResponsePolicy(
        action=AdaptiveAction.PAUSE_ADAPTIVE_QUESTIONS,
        purpose="Pause questioning upon caller refusal or operator directive.",
        max_questions=0,
        tone="respectful, compliant, grounding",
        allowed_structure="1 sentence acknowledging the pause without pressure.",
    ),
    AdaptiveAction.END_GRACEFULLY: ActionResponsePolicy(
        action=AdaptiveAction.END_GRACEFULLY,
        purpose="Conclude the call gracefully when caller is satisfied and safety is intact.",
        max_questions=0,
        tone="courteous, warm, final",
        allowed_structure="1 closing thanks and invitation to call back anytime.",
    ),
    AdaptiveAction.ACKNOWLEDGE: ActionResponsePolicy(
        action=AdaptiveAction.ACKNOWLEDGE,
        purpose="Empathetic validation of caller emotional statement.",
        max_questions=0,
        tone="empathic, reflective",
        allowed_structure="1 empathetic acknowledging sentence.",
    ),
    AdaptiveAction.CLARIFY: ActionResponsePolicy(
        action=AdaptiveAction.CLARIFY,
        purpose="General conversational clarification turn.",
        max_questions=1,
        tone="engaged, gentle",
        allowed_structure="1 brief clarifying sentence or question.",
    ),
}


def get_response_policy(action: AdaptiveAction) -> ActionResponsePolicy:
    """Retrieves the strict response policy for an adaptive action."""
    return POLICY_CATALOG.get(action, POLICY_CATALOG[AdaptiveAction.CLARIFY])
