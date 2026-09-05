"""SAMVED Phase 16: SIH 2026 Presentation Demo Catalog.

Houses the canonical flagship demonstration scenario (Tamil/English code-switching)
designed specifically for Smart India Hackathon evaluators to witness the entire
end-to-end multi-stage pipeline under high-stress conditions.
"""

from typing import Dict, List
from app.demo.models import (
    DemoDialogueTurn,
    DemoScenario,
    DemoSpeakerRole,
)

FLAGSHIP_SCENARIO_ID = "DEMO-SCENARIO-TAMIL-ENG-001"

FLAGSHIP_TAMIL_ENG_SCENARIO = DemoScenario(
    scenario_id=FLAGSHIP_SCENARIO_ID,
    title="Flagship SIH 2026: Tamil/English Code-Switching Acute Domestic Crisis & Rapid Warm Transfer",
    description=(
        "A realistic, high-urgency multi-turn crisis scenario featuring an English-Tamil bilingual caller "
        "experiencing imminent domestic violence with weapon involvement and child co-presence. "
        "Demonstrates real-time acoustic distress detection, statutory RAG grounding, SVI 88 (Critical) scoring, "
        "P0 Emergency Protocol activation, operator warm-transfer briefing, and cryptographically sealed audit logging."
    ),
    problem_statement="SIH 2026 PS-26093: AI-Driven Multilingual Emergency Triage and Victim Support",
    language_pair="ta-IN / en-IN (Code-Switching)",
    caller_profile={
        "synthetic_caller_id": "CALLER-SYNTH-9842",
        "pseudonym": "Kavitha (Synthetic Persona)",
        "phone_masked": "+91-98765-XXXXX",
        "location": "Madurai Urban, Tamil Nadu",
        "environment": "Locked inner room, loud banging sounds in background",
        "risk_profile": "Immediate Threat / Edged Weapon / Co-present Dependent",
    },
    dialogue=[
        DemoDialogueTurn(
            turn_index=1,
            speaker=DemoSpeakerRole.CALLER,
            text="Help me please... avar romba violent-ah behave panraaru, door break panna try panraaru... enna panradhu nu therila!",
            transcription_raw="Help me please avar romba violent ah behave panraaru door break panna try panraaru enna panradhu nu therila",
            translation_en="Help me please... he is behaving very violently, trying to break the door... I don't know what to do!",
            detected_language="ta-en",
            acoustic_stress_score=0.82,
            delay_ms=450,
        ),
        DemoDialogueTurn(
            turn_index=2,
            speaker=DemoSpeakerRole.CALLER,
            text="He has a knife in hand... kaiyila kaththi vechirukaaru, threaten panraaru! Please send help, baby is crying inside room.",
            transcription_raw="He has a knife in hand kaiyila kaththi vechirukaaru threaten panraaru Please send help baby is crying inside room",
            translation_en="He has a knife in hand... he is holding a knife, threatening me! Please send help, baby is crying inside room.",
            detected_language="ta-en",
            acoustic_stress_score=0.94,
            delay_ms=520,
        ),
        DemoDialogueTurn(
            turn_index=3,
            speaker=DemoSpeakerRole.CALLER,
            text="Ennala mudiyala... if he gets in, everything is over. Nan romba bayandhu poi iruken.",
            transcription_raw="Ennala mudiyala if he gets in everything is over Nan romba bayandhu poi iruken",
            translation_en="I cannot take this... if he gets in, everything is over. I am terrified.",
            detected_language="ta-en",
            acoustic_stress_score=0.89,
            delay_ms=380,
        ),
    ],
    expected_safety_triggers=[
        "IMMINENT_VIOLENCE",
        "WEAPON_INVOLVED",
        "DOMESTIC_DISTRESS",
        "CHILD_PRESENT",
    ],
    expected_svi={
        "score": 88,
        "band": "CRITICAL",
        "normalized_score": 0.88,
        "confidence": 0.94,
        "primary_drivers": [
            {"factor": "Weapon Involvement (Knife)", "weight": 0.35, "contribution": 30.8},
            {"factor": "Physical Threat / Active Forced Entry", "weight": 0.30, "contribution": 26.4},
            {"factor": "Co-present Vulnerable Infant", "weight": 0.20, "contribution": 17.6},
            {"factor": "Extreme Acoustic Tremor & Panic", "weight": 0.15, "contribution": 13.2},
        ],
    },
    expected_protocol="P0_EMERGENCY_DISPATCH_ASSIST",
    expected_warm_transfer={
        "urgency_level": "CRITICAL_P0",
        "transfer_target": "Senior Crisis Supervisor & 112 Liaison Desk",
        "briefing_bullet_1": "Barricaded caller (Kavitha, Madurai) with 10-month-old infant in locked bedroom; active forced door entry.",
        "briefing_bullet_2": "Perpetrator armed with edged weapon (knife); acute panic, acoustic distress score 0.94.",
        "briefing_bullet_3": "Automated 112 dispatch advisory generated; human confirmation required before emergency vehicle dispatch.",
    },
    expected_rag_citations=[
        {
            "statute": "Protection of Women from Domestic Violence Act (PWDVA), 2005",
            "section": "Section 12 & 18",
            "relevance": "Immediate ex-parte protection orders and residence preservation against perpetrator eviction.",
        },
        {
            "statute": "Emergency Response Support System (ERSS) Guidelines (MHA)",
            "section": "SOP-112-DV-CRITICAL",
            "relevance": "Direct priority geo-dispatch to Madurai City Control Room with silent siren protocol.",
        },
        {
            "statute": "Tamil Nadu Social Welfare & Women Empowerment Dept",
            "section": "Madurai District IRCA & One Stop Centre (Sakhi)",
            "relevance": "Integrated emergency shelter, medical aid, and legal aid coordinator contact.",
        },
        {
            "statute": "Tele-MANAS National Mental Health Program",
            "section": "MoHFW Protocol 14416",
            "relevance": "Grounding trauma counselor warm handoff support.",
        },
    ],
    expected_case_linkage={
        "case_id": "CASE-2026-SIH-001",
        "entities": [
            {"entity_type": "VICTIM", "identifier": "Kavitha", "status": "BARRICADED"},
            {"entity_type": "DEPENDENT", "identifier": "Infant (Child)", "status": "AT_RISK"},
            {"entity_type": "PERPETRATOR", "identifier": "Spouse/Partner", "status": "ARMED_ATTEMPTING_ENTRY"},
            {"entity_type": "LOCATION", "identifier": "Madurai Urban, TN", "status": "ACTIVE_INCIDENT"},
        ],
        "relationships": [
            {"source": "Kavitha", "relation": "PROTECTS", "target": "Infant (Child)"},
            {"source": "Spouse/Partner", "relation": "THREATENS_WITH_WEAPON", "target": "Kavitha"},
        ],
    },
    expected_followup={
        "recommended_window": "T+2 hours post-intervention",
        "channel": "DISCRETE_SMS_OR_SILENT_CALLBACK",
        "safety_guard": "Requires tele-counselor positive confirmation of perpetrator removal before outreach.",
    },
    tags=["SIH_2026", "FLAGSHIP", "TAMIL_ENGLISH", "CODE_SWITCHING", "P0_EMERGENCY", "SVI_CRITICAL"],
)

DEMO_CATALOG: Dict[str, DemoScenario] = {
    FLAGSHIP_SCENARIO_ID: FLAGSHIP_TAMIL_ENG_SCENARIO,
}


def get_demo_scenario(scenario_id: str = FLAGSHIP_SCENARIO_ID) -> DemoScenario:
    """Retrieve demo scenario by ID, defaulting to the flagship Tamil/English scenario."""
    if scenario_id in DEMO_CATALOG:
        return DEMO_CATALOG[scenario_id]
    return FLAGSHIP_TAMIL_ENG_SCENARIO


def list_demo_scenarios() -> List[DemoScenario]:
    """List all available demo scenarios."""
    return list(DEMO_CATALOG.values())
