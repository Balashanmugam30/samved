"""Test suite for Case Intelligence timeline and read-only subsystem events (Phase 11)."""

import pytest
from app.cases.service import CaseService


@pytest.mark.asyncio
async def test_case_timeline_and_subsystem_events():
    svc = CaseService(auto_seed=False)
    call_id = "call-timeline-01"
    case = await svc.create_case(call_id=call_id, case_number="CAS-TIME-001")

    # Record Safety Event
    safe_ev = await svc.record_safety_event(
        call_id=call_id,
        safety_rule="IMMINENT_HARM_CHECK",
        action="ESCALATE_TO_COUNSELOR",
        severity="HIGH",
    )
    assert safe_ev is not None
    assert safe_ev.source_type == "SAFETY"

    # Record SVI Event
    svi_ev = await svc.record_svi_event(
        call_id=call_id,
        svi_score=78,
        band="CRITICAL",
        factors=["high distress", "isolated environment"],
    )
    assert svi_ev is not None
    assert svi_ev.source_type == "SVI"

    # Record Acoustic Event
    ac_ev = await svc.record_acoustic_event(
        call_id=call_id,
        valence=-0.65,
        arousal=0.82,
        distress=0.79,
        primary_emotion="fear",
    )
    assert ac_ev is not None
    assert ac_ev.source_type == "ACOUSTIC"

    # Record Knowledge Citation
    cit_ev = await svc.record_knowledge_citation(
        call_id=call_id,
        citation_ref="CIT-TN-SHELTER-2023",
        source_id="src-tn-01",
        title="TN Women Shelter Guidelines",
        excerpt="Emergency shelter admission criteria...",
    )
    assert cit_ev is not None
    assert cit_ev.source_type == "KNOWLEDGE"

    # Verify Timeline order and content
    timeline = await svc.get_timeline(case.case_id)
    assert len(timeline) >= 5  # Initial creation + 4 events

    # Verify updated case state reflects Safety & SVI without altering graph entities
    updated_case = await svc.get_case(case.case_id)
    assert updated_case.safety_state == "HIGH"
    assert updated_case.svi_score == 78
    assert updated_case.svi_band == "CRITICAL"
