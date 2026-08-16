"""Tests for Chapter 0044 PCB / Board Correlation (Gate R9, WP9.2 & WP9.3)."""

from __future__ import annotations

import json
from pathlib import Path

_REPO = Path(__file__).resolve().parent.parent
_EXTRACT = _REPO / "verification" / "circuit" / "results" / "pcb-correlation-0044-extract.json"
_DIAGRAM_DIR = _REPO / "book" / "0044-pcb-board-correlation" / "diagrams"


def test_pcb_correlation_statistical_accuracy() -> None:
    """Verifies that R² exceeds 0.999 and RMSE is below 5 mV."""
    assert _EXTRACT.is_file()
    data = json.loads(_EXTRACT.read_text("utf-8"))
    stats = data["statistical_summary"]
    sm = data["summary"]

    assert stats["r_squared"] > 0.999
    assert stats["rmse_v"] < 0.005  # < 5 mV RMSE
    assert stats["max_delta_v"] < 0.010  # < 10 mV max delta
    assert stats["all_within_tolerance"] is True
    assert sm["all_metrics_within_tolerance"] is True


def test_pcb_correlation_metrics_provenance() -> None:
    """Verifies that all correlation metrics carry 'measured' evidence class."""
    assert _EXTRACT.is_file()
    data = json.loads(_EXTRACT.read_text("utf-8"))
    metrics = data["correlation_metrics"]
    assert len(metrics) >= 5

    for m in metrics:
        assert m["evidence_class"] == "measured"
        assert m["within_tolerance"] is True
        assert len(m["notes"]) > 10


def test_pcb_testbench_vectors() -> None:
    """Verifies all 6 test vectors from Chapter 0005 are evaluated."""
    assert _EXTRACT.is_file()
    data = json.loads(_EXTRACT.read_text("utf-8"))
    cases = data["testbench_cases"]
    assert len(cases) == 6

    for c in cases:
        assert c["within_tolerance"] is True
        assert abs(c["measured_vout_v"] - c["spice_vout_v"]) < 0.005


def test_all_4_diagrams_exist() -> None:
    """Verifies all 4 SVG diagram files exist."""
    assert (_DIAGRAM_DIR / "pcb-correlation-summary-0044.svg").is_file()
    assert (_DIAGRAM_DIR / "pcb-spice-vs-meas-0044.svg").is_file()
    assert (_DIAGRAM_DIR / "pcb-error-residuals-0044.svg").is_file()
    assert (_DIAGRAM_DIR / "pcb-metrics-table-0044.svg").is_file()
