"""Unit and integration tests for Operator Training Sandbox."""

import pytest
from app.simulation.sandbox import training_sandbox


def test_sandbox_list_drills():
    drills = training_sandbox.list_drills()
    assert len(drills) >= 4
    categories = {d.category for d in drills}
    assert "CRITICAL_TRIAGE" in categories


def test_sandbox_session_lifecycle_and_turn_scoring():
    session = training_sandbox.start_session(
        drill_key="DRILL-OVERDOSE-001",
        trainee_id="T-2026",
        trainee_name="Counselor Trainee Priya",
    )
    assert session.session_id.startswith("TRN-")
    assert session.status == "ACTIVE"
    assert session.current_turn == 1
    assert session.total_turns == 2

    # Turn 1: Trainee gives strong response instructing recovery position and emergency ambulance
    eval_turn_1 = training_sandbox.evaluate_trainee_turn(
        session_id=session.session_id,
        trainee_input="Stay calm, please turn him on his side in the recovery position immediately while I connect to the emergency ambulance and doctor.",
    )
    assert eval_turn_1.turn_number == 1
    assert eval_turn_1.safety_protocol_score >= 28.0
    assert eval_turn_1.empathy_score >= 18.0
    assert eval_turn_1.de_escalation_score >= 14.0
    assert eval_turn_1.score >= 80.0
    assert eval_turn_1.caller_next_turn is not None
    assert session.current_turn == 2

    # Turn 2: Trainee continues reassurance and confirms emergency dispatch
    eval_turn_2 = training_sandbox.evaluate_trainee_turn(
        session_id=session.session_id,
        trainee_input="Do not give water. Keep him on his side, keep the airway clear. The ambulance is on the way and our medical team is on the line with us right now.",
    )
    assert eval_turn_2.turn_number == 2
    assert eval_turn_2.score >= 75.0

    # Session should now be finalized
    completed_session = training_sandbox.get_session(session.session_id)
    assert completed_session.status == "COMPLETED"
    assert completed_session.completed_at is not None
    assert completed_session.overall_score >= 75.0
    assert completed_session.performance_rating in ("EXEMPLARY", "PROFICIENT")
    assert "safety_protocol" in completed_session.competency_breakdown
    assert len(completed_session.recommendations) >= 1
