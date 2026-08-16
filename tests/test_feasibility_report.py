"""Tests for Chapter 0042 Integrated Physical Feasibility Report."""

from __future__ import annotations

import json
from pathlib import Path

_REPO = Path(__file__).resolve().parent.parent
_EXTRACT = _REPO / "verification" / "circuit" / "results" / "integrated-feasibility-0042-extract.json"
_DIAGRAM_DIR = _REPO / "book" / "0042-integrated-feasibility-report" / "diagrams"


def test_gate_r8_passed() -> None:
    """Verifies Gate R8 has all 7/7 milestones satisfied."""
    assert _EXTRACT.is_file()
    data = json.loads(_EXTRACT.read_text("utf-8"))
    gate = data["gate_r8_status"]
    assert gate["gate_r8_passed"] is True
    assert gate["num_passed"] == gate["num_total"]
    assert gate["num_total"] == 7


def test_physical_ledger_10_claims() -> None:
    """Verifies all 10 physical claims are present across all 4 domains."""
    assert _EXTRACT.is_file()
    data = json.loads(_EXTRACT.read_text("utf-8"))
    claims = data["physical_ledger"]
    assert len(claims) == 10

    domains = {c["domain"] for c in claims}
    assert domains == {"latency", "energy", "area", "thermal"}

    valid_ev = {"measured", "spice", "derived", "assumed"}
    for c in claims:
        assert c["evidence_class"] in valid_ev
        assert len(c["sensitivity"]) > 5


def test_all_efficiency_claims_allowed() -> None:
    """Verifies all 4 efficiency claims are allowed with documented caveats."""
    assert _EXTRACT.is_file()
    data = json.loads(_EXTRACT.read_text("utf-8"))
    sm = data["summary"]
    assert sm["all_efficiency_claims_allowed"] is True

    ev = data["efficiency_claims_audit"]
    assert len(ev) == 4
    for e in ev:
        assert e["allowed"] is True
        assert len(e["caveat"]) > 10


def test_sensitivity_ranges_documented() -> None:
    """Verifies 5 assumed parameter sensitivity ranges are documented."""
    assert _EXTRACT.is_file()
    data = json.loads(_EXTRACT.read_text("utf-8"))
    sens = data["sensitivity_ranges"]
    assert len(sens) == 5
    for s in sens:
        assert len(s["pessimistic_impact"]) > 5
        assert len(s["optimistic_impact"]) > 5


def test_all_4_diagrams_exist() -> None:
    """Verifies all 4 SVG diagram files exist."""
    assert (_DIAGRAM_DIR / "feasibility-summary-0042.svg").is_file()
    assert (_DIAGRAM_DIR / "feasibility-ledger-0042.svg").is_file()
    assert (_DIAGRAM_DIR / "feasibility-sensitivity-0042.svg").is_file()
    assert (_DIAGRAM_DIR / "feasibility-gate-r8-0042.svg").is_file()


def test_extract_references_all_source_chapters() -> None:
    """Verifies the extract provenance references all Gate R8 source chapters."""
    assert _EXTRACT.is_file()
    data = json.loads(_EXTRACT.read_text("utf-8"))
    claims = data["physical_ledger"]
    provenances = " ".join(c["provenance"] for c in claims)
    for ch in ["Ch.0038", "Ch.0039", "Ch.0040", "Ch.0041"]:
        assert ch in provenances
