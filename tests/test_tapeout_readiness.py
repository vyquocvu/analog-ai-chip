"""Tests for Chapter 0045 IC / Tape-Out Readiness Review (Gate R9 Final Sign-Off)."""

from __future__ import annotations

import json
from pathlib import Path

_REPO = Path(__file__).resolve().parent.parent
_EXTRACT = _REPO / "verification" / "circuit" / "results" / "tapeout-readiness-0045-extract.json"
_DIAGRAM_DIR = _REPO / "book" / "0045-ic-tapeout-readiness" / "diagrams"


def test_gate_r9_tapeout_verdict() -> None:
    """Verifies that Gate R9 is PASSED and zero critical blockers exist."""
    assert _EXTRACT.is_file()
    data = json.loads(_EXTRACT.read_text("utf-8"))
    sm = data["summary"]

    assert sm["gate_r9_verdict"] == "PASSED"
    assert sm["num_blockers"] == 0
    assert sm["num_gates_passed"] >= 5
    assert "READY FOR FOUNDRY SHUTTLE" in sm["overall_tapeout_readiness"]


def test_pdk_requirements_completeness() -> None:
    """Verifies that FEOL, BEOL, physical layout, and analog PDK rules are defined."""
    assert _EXTRACT.is_file()
    data = json.loads(_EXTRACT.read_text("utf-8"))
    reqs = data["pdk_requirements"]
    assert len(reqs) >= 5

    categories = {r["category"] for r in reqs}
    assert "Front-End (FEOL)" in categories
    assert "Back-End (BEOL)" in categories
    assert "Physical Layout" in categories
    assert "Analog Peripherals" in categories


def test_risk_matrix_mitigations() -> None:
    """Verifies that all high/medium severity risks have documented mitigation strategies."""
    assert _EXTRACT.is_file()
    data = json.loads(_EXTRACT.read_text("utf-8"))
    risks = data["open_risk_matrix"]
    assert len(risks) >= 5

    for rk in risks:
        assert len(rk["mitigation_strategy"]) > 15
        assert len(rk["residual_impact"]) > 10
        assert rk["severity"] in {"HIGH", "MEDIUM", "LOW"}


def test_all_4_diagrams_exist() -> None:
    """Verifies all 4 SVG diagram files exist."""
    assert (_DIAGRAM_DIR / "tapeout-summary-0045.svg").is_file()
    assert (_DIAGRAM_DIR / "tapeout-pdk-stack-0045.svg").is_file()
    assert (_DIAGRAM_DIR / "tapeout-risk-matrix-0045.svg").is_file()
    assert (_DIAGRAM_DIR / "tapeout-gate-checklist-0045.svg").is_file()
