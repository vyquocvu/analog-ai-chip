"""Tests for Chapter 0041 Thermal / Power Density Sanity Checks."""

from __future__ import annotations

import json
from pathlib import Path

_REPO = Path(__file__).resolve().parent.parent
_EXTRACT = _REPO / "verification" / "circuit" / "results" / "thermal-power-density-0041-extract.json"
_DIAGRAM_DIR = _REPO / "book" / "0041-thermal-power-density" / "diagrams"


def test_all_thermal_sanity_checks_pass() -> None:
    """Verifies all 5 thermal sanity checks pass."""
    assert _EXTRACT.is_file()
    data = json.loads(_EXTRACT.read_text("utf-8"))
    sm = data["summary"]
    assert sm["all_sanity_checks_passed"] is True
    assert sm["num_checks_passed"] == sm["num_checks_total"]
    assert sm["num_checks_total"] == 5

    checks = data["sanity_checks"]
    for c in checks:
        assert c["passed"] is True


def test_junction_temperature_within_envelope() -> None:
    """Verifies nominal junction temperature is safely below T_j,max."""
    assert _EXTRACT.is_file()
    data = json.loads(_EXTRACT.read_text("utf-8"))
    sm = data["summary"]

    # T_j must be above ambient (25°C) but well below 125°C max
    assert 25.0 < sm["nominal_junction_temp_c"] < 125.0
    # Must have at least 20°C safety margin
    assert (125.0 - sm["nominal_junction_temp_c"]) > 20.0


def test_power_density_within_passive_cooling_limit() -> None:
    """Verifies power density is within passive (natural convection) cooling limits."""
    assert _EXTRACT.is_file()
    data = json.loads(_EXTRACT.read_text("utf-8"))
    sm = data["summary"]

    # Must be below 100 mW/mm² for passive cooling
    assert sm["power_density_mw_per_mm2"] < 100.0
    # And physically reasonable (positive)
    assert sm["power_density_mw_per_mm2"] > 0.0


def test_thermal_parameters_provenance() -> None:
    """Verifies all thermal parameters carry valid evidence class tags."""
    assert _EXTRACT.is_file()
    data = json.loads(_EXTRACT.read_text("utf-8"))
    valid_classes = {"measured", "spice", "derived", "assumed"}
    for p in data["thermal_parameters"]:
        assert p["evidence_class"] in valid_classes
        assert len(p["provenance"]) > 5


def test_all_4_diagrams_exist() -> None:
    """Verifies all 4 SVG diagram files exist."""
    assert (_DIAGRAM_DIR / "thermal-power-density-0041.svg").is_file()
    assert (_DIAGRAM_DIR / "thermal-sanity-checks-0041.svg").is_file()
    assert (_DIAGRAM_DIR / "thermal-scenarios-0041.svg").is_file()
    assert (_DIAGRAM_DIR / "thermal-memristor-reliability-0041.svg").is_file()
