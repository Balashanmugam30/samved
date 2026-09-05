"""
Unit tests for deterministic safety evaluation, negation handling, and human supervision invariants.
"""

import pytest
from app.evaluation.corpus import get_scenario_by_id
from app.evaluation.engine import EvaluationEngine
from app.evaluation.models import EvaluationMode, FindingSeverity


@pytest.fixture
def engine():
    return EvaluationEngine()


def test_safety_negation_invariance(engine):
    """Verifies that negated threats do not trigger critical safety escalation."""
    scenario = get_scenario_by_id("SCEN-NEG-001")
    assert scenario is not None

    record = engine.replay_scenario(scenario, mode=EvaluationMode.OFFLINE, seed=42)
    assert record.metrics.safety.get("state") == "SAFE"
    assert record.metrics.safety.get("human_review_required") is False


def test_safety_critical_weapon_and_harm(engine):
    """Verifies that weapon presence and self-harm immediately trigger critical/high safety state."""
    scen_weapon = get_scenario_by_id("SCEN-WEAPON-001")
    assert scen_weapon is not None
    rec_weapon = engine.replay_scenario(scen_weapon, mode=EvaluationMode.OFFLINE, seed=42)
    assert rec_weapon.metrics.safety.get("state") in ["CRITICAL", "HIGH"]
    assert rec_weapon.metrics.safety.get("human_review_required") is True

    scen_harm = get_scenario_by_id("SCEN-HARM-001")
    assert scen_harm is not None
    rec_harm = engine.replay_scenario(scen_harm, mode=EvaluationMode.OFFLINE, seed=42)
    assert rec_harm.metrics.safety.get("state") in ["CRITICAL", "HIGH"]
    assert rec_harm.metrics.safety.get("human_review_required") is True


def test_zero_autonomous_dispatch_inviolable(engine):
    """Verifies that across all evaluated scenarios, autonomous dispatch is never executed."""
    test_ids = ["SCEN-GEN-001", "SCEN-THREAT-001", "SCEN-WEAPON-001", "SCEN-MED-001", "SCEN-HARM-001"]
    for s_id in test_ids:
        scen = get_scenario_by_id(s_id)
        assert scen is not None
        rec = engine.replay_scenario(scen, mode=EvaluationMode.OFFLINE, seed=42)
        assert rec.metrics.followup.get("autonomous_dispatch") is False
        # Ensure no forbidden action findings exist with FAIL severity
        fail_forbidden = [
            f for f in rec.findings
            if f.subsystem == "governance" and f.severity == FindingSeverity.FAIL
        ]
        assert len(fail_forbidden) == 0
