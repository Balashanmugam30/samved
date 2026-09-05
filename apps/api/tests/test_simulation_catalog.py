"""Tests for Phase 14 scenario catalog."""

import pytest
from app.simulation.catalog import scenario_catalog


def test_scenario_catalog_coverage():
    scenarios = scenario_catalog.list_scenarios()
    assert len(scenarios) >= 20

    # Ensure all 4 risk bands are represented
    bands = {s.expected_svi_band.upper() for s in scenarios}
    assert "CRITICAL" in bands
    assert "HIGH" in bands
    assert "MODERATE" in bands
    assert "LOW" in bands

    # Ensure key Indian languages are represented
    langs = {s.language for s in scenarios}
    assert "hi-IN" in langs
    assert "ta-IN" in langs
    assert "en-IN" in langs
    assert "te-IN" in langs


def test_scenario_catalog_filtering():
    critical = scenario_catalog.list_scenarios(band="CRITICAL")
    assert len(critical) >= 5
    assert all(s.expected_svi_band == "CRITICAL" for s in critical)

    hindi = scenario_catalog.list_scenarios(language="hi-IN")
    assert len(hindi) >= 4
    assert all(s.language == "hi-IN" for s in hindi)

    smoke = scenario_catalog.get_suite("smoke")
    assert len(smoke) >= 8
    assert all("smoke" in s.tags for s in smoke)


def test_scenario_retrieval_by_id():
    sc = scenario_catalog.get_scenario("SCEN-CRIT-001")
    assert sc is not None
    assert sc.scenario_id == "SCEN-CRIT-001"
    assert sc.expected_svi_band == "CRITICAL"
    assert len(sc.synthetic_dialogue) >= 1

    missing = scenario_catalog.get_scenario("NON-EXISTENT")
    assert missing is None
