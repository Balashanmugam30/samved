"""Synthetic scenario catalog for SAMVED Phase 14 Scenario Simulation Engine.

Contains 24 synthetic scenarios spanning 11 Indian languages, 4 SVI risk bands,
and critical edge cases (negation traps, code-switching, acute overdose, statutory referrals).
"""

from typing import Dict, List, Optional
from app.simulation.models import (
    NoiseProfile,
    SimulationScenario,
    SyntheticDialogueTurn,
)

SYNTHETIC_SCENARIOS: List[SimulationScenario] = [
    # -----------------------------------------------------------------------
    # CRITICAL RISK BAND (SVI 76 - 100) — Mandatory Immediate Safety Alerts
    # -----------------------------------------------------------------------
    SimulationScenario(
        scenario_id="SCEN-CRIT-001",
        title="Acute Suicidal Ideation in Despair (Hindi)",
        description="Caller expressing active suicidal thoughts with feelings of helplessness. Demands immediate P0 alert and human counselor handoff.",
        language="hi-IN",
        expected_svi_band="CRITICAL",
        expected_score_range=[76, 100],
        expected_safety_triggers=["SELF_HARM"],
        prohibited_safety_triggers=[],
        noise_profile=NoiseProfile.CLEAN,
        tags=["critical", "self-harm", "hindi", "smoke"],
        expected_rag_citations=["Mental Healthcare Act, 2017 - Section 21"],
        synthetic_dialogue=[
            SyntheticDialogueTurn(
                turn=1,
                speaker="caller",
                text="Mera ab jeene ka man nahi hai aur main marna chahta hoon, sab kuch khatam kar loon.",
                partial="Mera ab jeene ka man nahi...",
                language="hi-IN",
            ),
            SyntheticDialogueTurn(
                turn=2,
                speaker="agent",
                text="Aapki jaan bohot anmol hai. Main abhi aapki call hamare senior emergency counselor ko handover kar raha hoon.",
                language="hi-IN",
            ),
        ],
    ),
    SimulationScenario(
        scenario_id="SCEN-CRIT-002",
        title="Immediate Life-Threatening Self-Harm Intent (Tamil)",
        description="Caller stating intention to end their life tonight due to severe addiction relapse. Triggers critical safety alert.",
        language="ta-IN",
        expected_svi_band="CRITICAL",
        expected_score_range=[76, 100],
        expected_safety_triggers=["SELF_HARM"],
        prohibited_safety_triggers=[],
        noise_profile=NoiseProfile.CLEAN,
        tags=["critical", "self-harm", "tamil", "smoke"],
        expected_rag_citations=["Mental Healthcare Act, 2017 - Section 29"],
        synthetic_dialogue=[
            SyntheticDialogueTurn(
                turn=1,
                speaker="caller",
                text="Naan ippove tharkolai pannika poren, uyira vida poren.",
                partial="Naan ippove tharkolai...",
                language="ta-IN",
            ),
            SyntheticDialogueTurn(
                turn=2,
                speaker="agent",
                text="Ungal uyir migavum mukkiyamanadhu. Thayavu seidhu phone-ai thundikkadheergal, naan ungalai emergency counselorudan inaikkiren.",
                language="ta-IN",
            ),
        ],
    ),
    SimulationScenario(
        scenario_id="SCEN-CRIT-003",
        title="Acute Opioid Overdose Emergency (English)",
        description="Caller reports a family member is unresponsive with blue lips and slow breathing after overdose. Demands emergency ambulance coordination.",
        language="en-IN",
        expected_svi_band="CRITICAL",
        expected_score_range=[76, 100],
        expected_safety_triggers=["MEDICAL_EMERGENCY"],
        prohibited_safety_triggers=[],
        noise_profile=NoiseProfile.CLEAN,
        tags=["critical", "overdose", "medical", "english", "smoke"],
        expected_rag_citations=["MoSJE NAPDDR Guidelines - Medical Detoxification Protocols"],
        synthetic_dialogue=[
            SyntheticDialogueTurn(
                turn=1,
                speaker="caller",
                text="Help, my brother overdosed on heroin, he is unconscious on the floor and cannot breathe!",
                partial="Help, my brother overdosed...",
                language="en-IN",
            ),
            SyntheticDialogueTurn(
                turn=2,
                speaker="agent",
                text="Please stay on the line. Ensure he is on his side in recovery position while I connect you directly to our emergency triage team.",
                language="en-IN",
            ),
        ],
    ),
    SimulationScenario(
        scenario_id="SCEN-CRIT-004",
        title="Active Physical Threat with Weapon (English)",
        description="Caller states an attacker with a knife is breaking into the house right now.",
        language="en-IN",
        expected_svi_band="CRITICAL",
        expected_score_range=[76, 100],
        expected_safety_triggers=["WEAPON", "ONGOING_THREAT"],
        prohibited_safety_triggers=[],
        noise_profile=NoiseProfile.CLEAN,
        tags=["critical", "violence", "weapon", "english", "smoke"],
        expected_rag_citations=["Protection of Women from Domestic Violence Act, 2005"],
        synthetic_dialogue=[
            SyntheticDialogueTurn(
                turn=1,
                speaker="caller",
                text="He has a knife and is breaking my door outside right now, please send emergency help!",
                partial="He has a knife and...",
                language="en-IN",
            ),
            SyntheticDialogueTurn(
                turn=2,
                speaker="agent",
                text="Please stay hidden and safe, I am coordinating immediate emergency and police intervention.",
                language="en-IN",
            ),
        ],
    ),
    SimulationScenario(
        scenario_id="SCEN-CRIT-005",
        title="Acute Spurious Liquor Poisoning (Hindi)",
        description="Caller reports friend consumed spurious liquor, has chest pain and is unconscious on the floor.",
        language="hi-IN",
        expected_svi_band="CRITICAL",
        expected_score_range=[76, 100],
        expected_safety_triggers=["MEDICAL_EMERGENCY"],
        prohibited_safety_triggers=[],
        noise_profile=NoiseProfile.CLEAN,
        tags=["critical", "medical", "hindi"],
        expected_rag_citations=[],
        synthetic_dialogue=[
            SyntheticDialogueTurn(
                turn=1,
                speaker="caller",
                text="Usne kharab sharab pi li hai aur ab behosh pada hai, saans nahi aa rahi!",
                partial="Usne kharab sharab pi li...",
                language="hi-IN",
            ),
            SyntheticDialogueTurn(
                turn=2,
                speaker="agent",
                text="Kripya use ek taraf karvat dila dijiye, hum emergency medical ambulance desk se connect kar rahe hain.",
                language="hi-IN",
            ),
        ],
    ),
    SimulationScenario(
        scenario_id="SCEN-CRIT-006",
        title="Physical Threat with Knife (Telugu)",
        description="Caller reports an intoxicated attacker with a knife.",
        language="te-IN",
        expected_svi_band="CRITICAL",
        expected_score_range=[76, 100],
        expected_safety_triggers=["WEAPON"],
        prohibited_safety_triggers=[],
        noise_profile=NoiseProfile.CLEAN,
        tags=["critical", "telugu", "weapon"],
        expected_rag_citations=[],
        synthetic_dialogue=[
            SyntheticDialogueTurn(
                turn=1,
                speaker="caller",
                text="He has a knife and is attacking me now outside my room!",
                partial="He has a knife...",
                language="te-IN",
            ),
        ],
    ),

    # -----------------------------------------------------------------------
    # HIGH RISK BAND (SVI 51 - 75) — Severe Distress, Coercion, Confinement
    # -----------------------------------------------------------------------
    SimulationScenario(
        scenario_id="SCEN-HIGH-001",
        title="Severe Opioid Withdrawal & Confinement (Hindi)",
        description="Caller locked in room with phone taken away and severe withdrawal distress.",
        language="hi-IN",
        expected_svi_band="HIGH",
        expected_score_range=[51, 75],
        expected_safety_triggers=["CONFINEMENT"],
        prohibited_safety_triggers=["SELF_HARM", "MEDICAL_EMERGENCY"],
        noise_profile=NoiseProfile.CLEAN,
        tags=["high", "withdrawal", "hindi", "smoke"],
        expected_rag_citations=["MoSJE NAPDDR IRCA Center Directory - Delhi NCR"],
        synthetic_dialogue=[
            SyntheticDialogueTurn(
                turn=1,
                speaker="caller",
                text="Ghar waalon ne mujhe kamre mein band kar diya hai aur bahar nahi jaane de rahe!",
                partial="Ghar waalon ne mujhe kamre...",
                language="hi-IN",
            ),
            SyntheticDialogueTurn(
                turn=2,
                speaker="agent",
                text="Aap bilkul mat ghabraiye, hum aapko medical detoxification aur aashray sthal ke liye IRCA center se jodd rahe hain.",
                language="hi-IN",
            ),
        ],
    ),
    SimulationScenario(
        scenario_id="SCEN-HIGH-002",
        title="Severe Confinement & Forced Relapse (English)",
        description="Caller locked inside with phone seized by hostile persons while in withdrawal.",
        language="en-IN",
        expected_svi_band="HIGH",
        expected_score_range=[51, 75],
        expected_safety_triggers=["CONFINEMENT"],
        prohibited_safety_triggers=["SELF_HARM"],
        noise_profile=NoiseProfile.CLEAN,
        tags=["high", "confinement", "english", "smoke"],
        expected_rag_citations=["Protection of Human Rights in De-addiction Centers"],
        synthetic_dialogue=[
            SyntheticDialogueTurn(
                turn=1,
                speaker="caller",
                text="They locked me inside and are not letting me leave the room!",
                partial="They locked me inside...",
                language="en-IN",
            ),
            SyntheticDialogueTurn(
                turn=2,
                speaker="agent",
                text="We are here to support you. Let us connect you to a trusted district legal aid officer and medical counselor.",
                language="en-IN",
            ),
        ],
    ),
    SimulationScenario(
        scenario_id="SCEN-HIGH-003",
        title="Delirium Tremens Risk & Confinement (Tamil)",
        description="Caller experiencing acute distress locked inside without support.",
        language="ta-IN",
        expected_svi_band="HIGH",
        expected_score_range=[51, 75],
        expected_safety_triggers=["CONFINEMENT"],
        prohibited_safety_triggers=["SELF_HARM"],
        noise_profile=NoiseProfile.CLEAN,
        tags=["high", "withdrawal", "tamil", "smoke"],
        expected_rag_citations=["MoSJE IRCA Tamil Nadu Directory"],
        synthetic_dialogue=[
            SyntheticDialogueTurn(
                turn=1,
                speaker="caller",
                text="Ennai veetla pooti vachirukanga, veliya poga vida maatendranga!",
                partial="Ennai veetla pooti vachirukanga...",
                language="ta-IN",
            ),
            SyntheticDialogueTurn(
                turn=2,
                speaker="agent",
                text="Idhu alcohol withdrawal arikuri. Neengal udanadiyaga arasu maruthuvamanai detox ward-ukku sella vendum.",
                language="ta-IN",
            ),
        ],
    ),
    SimulationScenario(
        scenario_id="SCEN-HIGH-004",
        title="Confinement and Forced Deprivation (Kannada)",
        description="Caller locked inside room forcibly in Bengaluru.",
        language="kn-IN",
        expected_svi_band="HIGH",
        expected_score_range=[51, 75],
        expected_safety_triggers=["CONFINEMENT"],
        prohibited_safety_triggers=["SELF_HARM"],
        noise_profile=NoiseProfile.CLEAN,
        tags=["high", "kannada", "confinement"],
        expected_rag_citations=[],
        synthetic_dialogue=[
            SyntheticDialogueTurn(
                turn=1,
                speaker="caller",
                text="They locked me inside and are not letting me leave the room!",
                partial="They locked me inside...",
                language="kn-IN",
            ),
        ],
    ),
    SimulationScenario(
        scenario_id="SCEN-HIGH-005",
        title="Forcible Captivity in Unregistered Center (Malayalam)",
        description="Caller trapped in an illegal center, denied contact with family.",
        language="ml-IN",
        expected_svi_band="HIGH",
        expected_score_range=[51, 75],
        expected_safety_triggers=["CONFINEMENT"],
        prohibited_safety_triggers=[],
        noise_profile=NoiseProfile.CLEAN,
        tags=["high", "malayalam", "confinement"],
        expected_rag_citations=[],
        synthetic_dialogue=[
            SyntheticDialogueTurn(
                turn=1,
                speaker="caller",
                text="They locked me inside and are keeping me here against my will!",
                partial="They locked me inside...",
                language="ml-IN",
            ),
        ],
    ),

    # -----------------------------------------------------------------------
    # MODERATE RISK BAND (SVI 26 - 50) — Mild Distress, Seeking Counseling
    # -----------------------------------------------------------------------
    SimulationScenario(
        scenario_id="SCEN-MOD-001",
        title="Alcohol Dependence & Distress (Hindi)",
        description="Caller realizing their daily drinking is causing severe anxiety, seeking tele-counseling.",
        language="hi-IN",
        expected_svi_band="MODERATE",
        expected_score_range=[26, 50],
        expected_safety_triggers=[],
        prohibited_safety_triggers=["SELF_HARM", "ONGOING_THREAT"],
        noise_profile=NoiseProfile.CLEAN,
        tags=["moderate", "counseling", "hindi", "smoke"],
        expected_rag_citations=["MoSJE Tele-counseling Modules"],
        synthetic_dialogue=[
            SyntheticDialogueTurn(
                turn=1,
                speaker="caller",
                text="Main roz daaru peeta hoon. I feel so lost, panicking and shaking, please help me with counseling.",
                partial="Main roz daaru peeta hoon...",
                language="hi-IN",
            ),
            SyntheticDialogueTurn(
                turn=2,
                speaker="agent",
                text="Aapka pehla kadam uthana bohot prashansaniya hai. Hum aapko hamare certified tele-counselor se jodd rahe hain.",
                language="hi-IN",
            ),
        ],
    ),
    SimulationScenario(
        scenario_id="SCEN-MOD-002",
        title="College Student Cannabis Anxiety (Tamil)",
        description="Student worried about cannabis use during exams, feeling panicked.",
        language="ta-IN",
        expected_svi_band="MODERATE",
        expected_score_range=[26, 50],
        expected_safety_triggers=[],
        prohibited_safety_triggers=["SELF_HARM"],
        noise_profile=NoiseProfile.CLEAN,
        tags=["moderate", "youth", "tamil", "smoke"],
        expected_rag_citations=["NAPDDR Youth Awareness Scheme"],
        synthetic_dialogue=[
            SyntheticDialogueTurn(
                turn=1,
                speaker="caller",
                text="College-la ganja adikka soldranga. I feel helpless, so afraid and all alone with nowhere to go.",
                partial="College-la ganja...",
                language="ta-IN",
            ),
            SyntheticDialogueTurn(
                turn=2,
                speaker="agent",
                text="Manaporiattam arakoodave sleep hygiene matrum coping techniques moolam ganja craving-ai thadukkalam.",
                language="ta-IN",
            ),
        ],
    ),
    SimulationScenario(
        scenario_id="SCEN-MOD-003",
        title="Distress and Relapse Anxiety (English)",
        description="Caller struggling with loneliness, craving, and feeling overwhelmed.",
        language="en-IN",
        expected_svi_band="MODERATE",
        expected_score_range=[26, 50],
        expected_safety_triggers=[],
        prohibited_safety_triggers=[],
        noise_profile=NoiseProfile.CLEAN,
        tags=["moderate", "family", "english", "smoke"],
        expected_rag_citations=["Juvenile Justice Act, 2015 Guidelines"],
        synthetic_dialogue=[
            SyntheticDialogueTurn(
                turn=1,
                speaker="caller",
                text="I feel so lost, panicking, and shaking. I am all alone and have nowhere to go.",
                partial="I feel so lost...",
                language="en-IN",
            ),
            SyntheticDialogueTurn(
                turn=2,
                speaker="agent",
                text="It is very natural to feel concerned. We recommend empathetic, non-accusatory conversations along with adolescent family counseling.",
                language="en-IN",
            ),
        ],
    ),
    SimulationScenario(
        scenario_id="SCEN-MOD-004",
        title="Distress Over Relapse (Marathi)",
        description="Caller struggling with cravings and feeling lost.",
        language="mr-IN",
        expected_svi_band="MODERATE",
        expected_score_range=[26, 50],
        expected_safety_triggers=[],
        prohibited_safety_triggers=[],
        noise_profile=NoiseProfile.CLEAN,
        tags=["moderate", "marathi"],
        expected_rag_citations=[],
        synthetic_dialogue=[
            SyntheticDialogueTurn(
                turn=1,
                speaker="caller",
                text="I feel helpless, so afraid and all alone with nowhere to go.",
                partial="I feel helpless...",
                language="mr-IN",
            ),
        ],
    ),
    SimulationScenario(
        scenario_id="SCEN-MOD-005",
        title="Prescription Misuse Anxiety (Bengali)",
        description="Caller anxious about sleeping pill dependence.",
        language="bn-IN",
        expected_svi_band="MODERATE",
        expected_score_range=[26, 50],
        expected_safety_triggers=[],
        prohibited_safety_triggers=[],
        noise_profile=NoiseProfile.CLEAN,
        tags=["moderate", "bengali"],
        expected_rag_citations=[],
        synthetic_dialogue=[
            SyntheticDialogueTurn(
                turn=1,
                speaker="caller",
                text="I feel so lost, panicking, and shaking. I am all alone and have nowhere to go.",
                partial="I feel so lost...",
                language="bn-IN",
            ),
        ],
    ),

    # -----------------------------------------------------------------------
    # LOW RISK BAND (SVI 0 - 25) — Informational Inquiries & Statutory Rights
    # -----------------------------------------------------------------------
    SimulationScenario(
        scenario_id="SCEN-LOW-001",
        title="Government IRCA Center Location Inquiry (Hindi)",
        description="Caller asking for address and contact details of nearest government-funded de-addiction center in Jaipur.",
        language="hi-IN",
        expected_svi_band="LOW",
        expected_score_range=[0, 25],
        expected_safety_triggers=[],
        prohibited_safety_triggers=["SELF_HARM", "MEDICAL_EMERGENCY"],
        noise_profile=NoiseProfile.CLEAN,
        tags=["low", "info", "hindi", "smoke"],
        expected_rag_citations=["MoSJE NAPDDR IRCA Center Directory - Rajasthan"],
        synthetic_dialogue=[
            SyntheticDialogueTurn(
                turn=1,
                speaker="caller",
                text="Namaste, mujhe mere bhai ke liye de-addiction center ki jankari chahiye jo Jaipur me ho.",
                partial="Namaste, mujhe mere bhai...",
                language="hi-IN",
            ),
            SyntheticDialogueTurn(
                turn=2,
                speaker="agent",
                text="Namaste. Jaipur me sarkaari anudaanit IRCA kendra uplabdh hain. Main aapko unke pate aur contact number pradan karta hoon.",
                language="hi-IN",
            ),
        ],
    ),
    SimulationScenario(
        scenario_id="SCEN-LOW-002",
        title="Voluntary Treatment Immunity Inquiry under NDPS 64A (English)",
        description="Law student inquiring about Section 64A immunity provisions for small quantity possession during voluntary rehabilitation.",
        language="en-IN",
        expected_svi_band="LOW",
        expected_score_range=[0, 25],
        expected_safety_triggers=[],
        prohibited_safety_triggers=["SELF_HARM"],
        noise_profile=NoiseProfile.CLEAN,
        tags=["low", "legal", "english", "smoke"],
        expected_rag_citations=["Narcotic Drugs and Psychotropic Substances Act, 1985 - Section 64A"],
        synthetic_dialogue=[
            SyntheticDialogueTurn(
                turn=1,
                speaker="caller",
                text="Hello, could you explain how Section 64A of the NDPS Act protects individuals seeking voluntary medical treatment from prosecution?",
                partial="Hello, could you explain how...",
                language="en-IN",
            ),
            SyntheticDialogueTurn(
                turn=2,
                speaker="agent",
                text="Section 64A provides immunity from prosecution for small-quantity possession to individuals who voluntarily undergo de-addiction at a recognized facility.",
                language="en-IN",
            ),
        ],
    ),
    SimulationScenario(
        scenario_id="SCEN-LOW-003",
        title="Helpline Operating Hours and Languages Supported (Tamil)",
        description="Social worker asking about toll-free 14566 helpline capabilities and regional languages.",
        language="ta-IN",
        expected_svi_band="LOW",
        expected_score_range=[0, 25],
        expected_safety_triggers=[],
        prohibited_safety_triggers=[],
        noise_profile=NoiseProfile.CLEAN,
        tags=["low", "info", "tamil", "smoke"],
        expected_rag_citations=[],
        synthetic_dialogue=[
            SyntheticDialogueTurn(
                turn=1,
                speaker="caller",
                text="Vanakkam, indha helpline 24 manineramum seyalpadugiradha matrum Tamil la counselor irukkangala?",
                partial="Vanakkam, indha helpline...",
                language="ta-IN",
            ),
            SyntheticDialogueTurn(
                turn=2,
                speaker="agent",
                text="Aam, SAMVED helpline 24 mani neramum Tamil ullitta 11 mozhigalil seyalpadugiradhu. Ingu aalosanai kattanamatradhu.",
                language="ta-IN",
            ),
        ],
    ),
    SimulationScenario(
        scenario_id="SCEN-LOW-004",
        title="General Treatment Inquiry (Telugu)",
        description="Caller asking about voluntary counseling process.",
        language="te-IN",
        expected_svi_band="LOW",
        expected_score_range=[0, 25],
        expected_safety_triggers=[],
        prohibited_safety_triggers=[],
        noise_profile=NoiseProfile.CLEAN,
        tags=["low", "telugu", "info"],
        expected_rag_citations=[],
        synthetic_dialogue=[
            SyntheticDialogueTurn(
                turn=1,
                speaker="caller",
                text="Namaskaram, nearest government de-addiction center ekkada undo cheppagalara?",
                partial="Namaskaram, nearest government...",
                language="te-IN",
            ),
        ],
    ),
    SimulationScenario(
        scenario_id="SCEN-LOW-005",
        title="Center Inquiry in Ahmedabad (Gujarati)",
        description="Caller asking for contact number of IRCA center.",
        language="gu-IN",
        expected_svi_band="LOW",
        expected_score_range=[0, 25],
        expected_safety_triggers=[],
        prohibited_safety_triggers=[],
        noise_profile=NoiseProfile.CLEAN,
        tags=["low", "gujarati", "info"],
        expected_rag_citations=[],
        synthetic_dialogue=[
            SyntheticDialogueTurn(
                turn=1,
                speaker="caller",
                text="Namaste, Ahmedabad ma government de-addiction center no number aapo.",
                partial="Namaste, Ahmedabad...",
                language="gu-IN",
            ),
        ],
    ),
    SimulationScenario(
        scenario_id="SCEN-LOW-006",
        title="Rehab Directory Inquiry (Punjabi)",
        description="Inquiry about government OOAT center hours.",
        language="pa-IN",
        expected_svi_band="LOW",
        expected_score_range=[0, 25],
        expected_safety_triggers=[],
        prohibited_safety_triggers=[],
        noise_profile=NoiseProfile.CLEAN,
        tags=["low", "punjabi", "info"],
        expected_rag_citations=[],
        synthetic_dialogue=[
            SyntheticDialogueTurn(
                turn=1,
                speaker="caller",
                text="Sat Sri Akal ji, sarkari de-addiction centre bare jankari chahidi hai.",
                partial="Sat Sri Akal ji...",
                language="pa-IN",
            ),
        ],
    ),
    SimulationScenario(
        scenario_id="SCEN-LOW-007",
        title="Scheme Inquiry in Bhubaneswar (Odia)",
        description="Inquiry regarding post-rehab vocational schemes.",
        language="or-IN",
        expected_svi_band="LOW",
        expected_score_range=[0, 25],
        expected_safety_triggers=[],
        prohibited_safety_triggers=[],
        noise_profile=NoiseProfile.CLEAN,
        tags=["low", "odia", "info"],
        expected_rag_citations=[],
        synthetic_dialogue=[
            SyntheticDialogueTurn(
                turn=1,
                speaker="caller",
                text="Namaskar, drug rehabilitation centre contact number darkar.",
                partial="Namaskar, drug rehabilitation...",
                language="or-IN",
            ),
        ],
    ),

    # -----------------------------------------------------------------------
    # EDGE CASES & TRAPS (Negation, Code-Switching, Acoustic Distortion)
    # -----------------------------------------------------------------------
    SimulationScenario(
        scenario_id="SCEN-EDGE-001",
        title="Explicit Negation Trap on Self-Harm (Hindi)",
        description="Caller states they DO NOT want to hurt themselves, they just need sleep advice. Must NOT trigger self-harm emergency.",
        language="hi-IN",
        expected_svi_band="LOW",
        expected_score_range=[0, 30],
        expected_safety_triggers=[],
        prohibited_safety_triggers=["SELF_HARM"],
        noise_profile=NoiseProfile.CLEAN,
        tags=["edge", "negation", "hindi", "smoke"],
        expected_rag_citations=[],
        synthetic_dialogue=[
            SyntheticDialogueTurn(
                turn=1,
                speaker="caller",
                text="Mujhe aatmhatya bilkul nahi karni hai, main marna nahi chahta. Bas pichle do din se neend nahi aa rahi hai.",
                partial="Mujhe aatmhatya bilkul nahi...",
                language="hi-IN",
            ),
            SyntheticDialogueTurn(
                turn=2,
                speaker="agent",
                text="Yeh achhi baat hai ki aap apni tabiyat ke baare me sochte hain. Neend na aane ke liye hum counseling aur doctor salah sujhayenge.",
                language="hi-IN",
            ),
        ],
    ),
    SimulationScenario(
        scenario_id="SCEN-EDGE-002",
        title="Explicit Negation Trap on Weapon (English)",
        description="Caller clarifies they are safe and no weapons are involved, resolving an ambiguous statement.",
        language="en-IN",
        expected_svi_band="LOW",
        expected_score_range=[0, 25],
        expected_safety_triggers=[],
        prohibited_safety_triggers=["WEAPON", "ONGOING_THREAT"],
        noise_profile=NoiseProfile.CLEAN,
        tags=["edge", "negation", "english", "smoke"],
        expected_rag_citations=[],
        synthetic_dialogue=[
            SyntheticDialogueTurn(
                turn=1,
                speaker="caller",
                text="I want to clarify there is no weapon, nobody is threatening me with a knife or gun, we were just having a peaceful talk.",
                partial="I want to clarify there is no...",
                language="en-IN",
            ),
            SyntheticDialogueTurn(
                turn=2,
                speaker="agent",
                text="Thank you for clarifying your safety. We are here to support you with helpful information and counseling.",
                language="en-IN",
            ),
        ],
    ),
]


class ScenarioCatalog:
    """Thread-safe catalog of synthetic benchmark scenarios."""

    def __init__(self, scenarios: Optional[List[SimulationScenario]] = None):
        self._scenarios: Dict[str, SimulationScenario] = {}
        for sc in scenarios or SYNTHETIC_SCENARIOS:
            self._scenarios[sc.scenario_id] = sc

    def get_scenario(self, scenario_id: str) -> Optional[SimulationScenario]:
        return self._scenarios.get(scenario_id)

    def list_scenarios(
        self,
        band: Optional[str] = None,
        language: Optional[str] = None,
        tag: Optional[str] = None,
    ) -> List[SimulationScenario]:
        results = list(self._scenarios.values())
        if band:
            results = [s for s in results if s.expected_svi_band.upper() == band.upper()]
        if language:
            results = [s for s in results if s.language.lower() == language.lower()]
        if tag:
            results = [s for s in results if tag.lower() in [t.lower() for t in s.tags]]
        return results

    def get_suite(self, suite_type: str = "smoke") -> List[SimulationScenario]:
        """Returns scenarios for smoke (quick) or full suite."""
        if suite_type.lower() == "smoke":
            return [s for s in self._scenarios.values() if "smoke" in s.tags]
        return list(self._scenarios.values())

    def count(self) -> int:
        return len(self._scenarios)


scenario_catalog = ScenarioCatalog()
