"""Tests for Chapter 0038 Physical Latency Ledger."""

from __future__ import annotations

import json
from pathlib import Path

_REPO = Path(__file__).resolve().parent.parent
_EXTRACT = _REPO / "verification" / "circuit" / "results" / "latency-ledger-0038-extract.json"
_DIAGRAM_DIR = _REPO / "book" / "0038-latency-ledger" / "diagrams"


def test_timing_coefficients_provenance() -> None:
    """Verifies that all timing coefficients carry rigorous evidence provenance tags."""
    assert _EXTRACT.is_file()
    data = json.loads(_EXTRACT.read_text("utf-8"))
    coeffs = data["timing_coefficients"]
    assert len(coeffs) >= 6

    valid_classes = {"measured", "spice", "derived", "assumed"}
    for c in coeffs:
        assert c["evidence_class"] in valid_classes
        assert len(c["provenance"]) > 5
        assert c["value_ns"] > 0.0


def test_token_decode_schedule_and_throughput() -> None:
    """Verifies token decode schedule sanity and throughput calculations."""
    assert _EXTRACT.is_file()
    data = json.loads(_EXTRACT.read_text("utf-8"))
    sm = data["summary"]

    assert 500.0 < sm["single_token_decode_latency_ns"] < 2000.0
    assert sm["peak_token_throughput_tok_s"] > 500000
    assert sm["analog_imc_time_pct"] > 80.0
    assert sm["digital_overhead_pct"] < 20.0


def test_context_scaling_monotonicity() -> None:
    """Verifies that step latency monotonically increases with context length."""
    assert _EXTRACT.is_file()
    data = json.loads(_EXTRACT.read_text("utf-8"))
    scaling = data["context_length_scaling"]
    assert len(scaling) >= 5

    latencies = [s["latency_ns"] for s in scaling]
    assert latencies == sorted(latencies)


def test_extract_and_all_4_diagrams_exist() -> None:
    """Verifies extract schema and all 4 SVG diagram files exist."""
    assert _EXTRACT.is_file()
    extract = json.loads(_EXTRACT.read_text("utf-8"))
    assert extract["gate"] == "R8 — Physical feasibility report"
    assert extract["chapter"] == "0038-latency-ledger"

    assert (_DIAGRAM_DIR / "latency-ledger-0038.svg").is_file()
    assert (_DIAGRAM_DIR / "latency-waterfall-0038.svg").is_file()
    assert (_DIAGRAM_DIR / "latency-subsystem-breakdown-0038.svg").is_file()
    assert (_DIAGRAM_DIR / "latency-scaling-0038.svg").is_file()
