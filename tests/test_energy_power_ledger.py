"""Tests for Chapter 0039 Physical Energy and Power Ledger."""

from __future__ import annotations

import json
from pathlib import Path

_REPO = Path(__file__).resolve().parent.parent
_EXTRACT = _REPO / "verification" / "circuit" / "results" / "energy-power-ledger-0039-extract.json"
_DIAGRAM_DIR = _REPO / "book" / "0039-energy-power-ledger" / "diagrams"


def test_energy_coefficients_provenance() -> None:
    """Verifies that all energy coefficients carry rigorous evidence provenance tags."""
    assert _EXTRACT.is_file()
    data = json.loads(_EXTRACT.read_text("utf-8"))
    coeffs = data["energy_coefficients"]
    assert len(coeffs) >= 6

    valid_classes = {"measured", "spice", "derived", "assumed"}
    for c in coeffs:
        assert c["evidence_class"] in valid_classes
        assert len(c["provenance"]) > 5
        assert c["value"] > 0.0


def test_token_energy_breakdown_and_power() -> None:
    """Verifies token energy calculation, active power dissipation, and efficiency ratio."""
    assert _EXTRACT.is_file()
    data = json.loads(_EXTRACT.read_text("utf-8"))
    sm = data["summary"]

    assert 15.0 < sm["total_token_energy_nj"] < 50.0
    assert 10.0 < sm["active_power_mw"] < 100.0
    assert sm["energy_efficiency_advantage_x"] > 5.0

    subsystems = data["subsystem_energy_breakdown"]
    total_energy_sub = sum(s["energy_nj"] for s in subsystems)
    assert abs(total_energy_sub - sm["total_token_energy_nj"]) < 0.1


def test_power_metrics_structure() -> None:
    """Verifies active, leakage, and total chip power metrics."""
    assert _EXTRACT.is_file()
    data = json.loads(_EXTRACT.read_text("utf-8"))
    power = data["power_metrics"]
    assert len(power) == 3

    names = [p["name"] for p in power]
    assert "Active Dynamic Power" in names
    assert "Static Standby Leakage" in names
    assert "Total Peak Chip Power" in names


def test_extract_and_all_4_diagrams_exist() -> None:
    """Verifies extract schema and all 4 SVG diagram files exist."""
    assert _EXTRACT.is_file()
    extract = json.loads(_EXTRACT.read_text("utf-8"))
    assert extract["gate"] == "R8 — Physical feasibility report"
    assert extract["chapter"] == "0039-energy-power-ledger"

    assert (_DIAGRAM_DIR / "energy-ledger-0039.svg").is_file()
    assert (_DIAGRAM_DIR / "energy-breakdown-0039.svg").is_file()
    assert (_DIAGRAM_DIR / "energy-power-density-0039.svg").is_file()
    assert (_DIAGRAM_DIR / "energy-comparison-0039.svg").is_file()
