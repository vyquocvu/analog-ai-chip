"""Tests for Chapter 0036 Sensitivity and Quantization Trade-offs."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parent.parent
_MODULE = _REPO / "book" / "0036-sensitivity-quantization" / "sensitivity_quantization.py"
_EXTRACT = _REPO / "verification" / "circuit" / "results" / "sensitivity-quantization-0036-extract.json"
_DIAGRAM_DIR = _REPO / "book" / "0036-sensitivity-quantization" / "diagrams"


def _load_module():
    spec = importlib.util.spec_from_file_location("sensitivity_quantization_0036", _MODULE)
    if spec is None or spec.loader is None:
        return None
    mod = importlib.util.module_from_spec(spec)
    sys.modules["sensitivity_quantization_0036"] = mod
    spec.loader.exec_module(mod)
    return mod


mod = _load_module()


def test_bit_precision_sweep_structure() -> None:
    """Verifies that bit sweep covers 2..8 bits with monotonic energy scaling."""
    assert _EXTRACT.is_file()
    data = json.loads(_EXTRACT.read_text("utf-8"))
    bit_sweep = data["bit_precision_sweep"]
    assert len(bit_sweep) == 7

    bits = [p["bits"] for p in bit_sweep]
    assert bits == [2, 3, 4, 5, 6, 7, 8]

    energies = [p["tile_energy_nj_per_token"] for p in bit_sweep]
    assert energies == sorted(energies), "Tile energy should monotonically increase with converter resolution"


def test_nonideality_sensitivity_sweeps_coverage() -> None:
    """Verifies coverage across all 4 non-ideality sweep dimensions."""
    assert _EXTRACT.is_file()
    data = json.loads(_EXTRACT.read_text("utf-8"))
    sweeps = data["sensitivity_sweeps"]

    assert "wire_resistance" in sweeps
    assert "programming_variation" in sweeps
    assert "stuck_faults" in sweeps
    assert "retention_drift" in sweeps

    assert len(sweeps["wire_resistance"]) >= 4
    assert len(sweeps["programming_variation"]) >= 4
    assert len(sweeps["stuck_faults"]) >= 4
    assert len(sweeps["retention_drift"]) >= 4


def test_pareto_operating_point() -> None:
    """Verifies that Pareto analysis selects a valid hardware sweet spot."""
    assert _EXTRACT.is_file()
    data = json.loads(_EXTRACT.read_text("utf-8"))
    pop = data["pareto_operating_point"]
    assert pop["recommended_bits"] in [4, 5, 6, 7, 8]
    assert pop["energy_nj_per_token"] > 0.0


def test_extract_and_all_4_diagrams_exist() -> None:
    """Verifies extract and all 4 SVG diagram files exist."""
    assert _EXTRACT.is_file()
    extract = json.loads(_EXTRACT.read_text("utf-8"))
    assert extract["gate"] == "R7 — Transformer and LLM validation"
    assert extract["chapter"] == "0036-sensitivity-quantization"

    assert (_DIAGRAM_DIR / "sensitivity-quantization-0036.svg").is_file()
    assert (_DIAGRAM_DIR / "sensitivity-bit-sweep-0036.svg").is_file()
    assert (_DIAGRAM_DIR / "sensitivity-nonidealities-0036.svg").is_file()
    assert (_DIAGRAM_DIR / "sensitivity-pareto-frontier-0036.svg").is_file()
