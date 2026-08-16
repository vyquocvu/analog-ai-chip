"""Tests for Chapter 0040 Physical Area and Process Model."""

from __future__ import annotations

import json
from pathlib import Path

_REPO = Path(__file__).resolve().parent.parent
_EXTRACT = _REPO / "verification" / "circuit" / "results" / "area-process-model-0040-extract.json"
_DIAGRAM_DIR = _REPO / "book" / "0040-area-process-model" / "diagrams"


def test_area_coefficients_provenance() -> None:
    """Verifies that all area coefficients carry valid evidence provenance tags."""
    assert _EXTRACT.is_file()
    data = json.loads(_EXTRACT.read_text("utf-8"))
    coeffs = data["area_coefficients"]
    assert len(coeffs) >= 7

    valid_classes = {"measured", "spice", "derived", "assumed"}
    for c in coeffs:
        assert c["evidence_class"] in valid_classes
        assert len(c["provenance"]) > 5
        assert c["value_um2"] > 0.0


def test_tile_area_and_adc_dominance() -> None:
    """Verifies single tile area and that ADC bank is the dominant subsystem."""
    assert _EXTRACT.is_file()
    data = json.loads(_EXTRACT.read_text("utf-8"))
    tile = data["single_tile"]
    sm = data["summary"]

    # Tile area must be physically reasonable for 28nm
    assert 500.0 < tile["total_area_um2"] < 20000.0

    # ADC should dominate tile area
    assert sm["adc_dominates_tile"] is True
    assert sm["adc_fraction_pct"] > 60.0


def test_chip_floorplan_and_efficiency() -> None:
    """Verifies chip total area and compute density metrics."""
    assert _EXTRACT.is_file()
    data = json.loads(_EXTRACT.read_text("utf-8"))
    sm = data["summary"]

    # Total chip area must be physically plausible
    assert 0.5 < sm["total_chip_area_mm2"] < 10.0

    # GOPS/mm² must be positive and non-trivial
    assert sm["area_efficiency_gops_per_mm2"] > 1.0

    # Synapse count must match tile count
    assert sm["total_synapses_packed"] == 16 * 18 * 416


def test_extract_and_all_4_diagrams_exist() -> None:
    """Verifies extract schema and all 4 SVG diagram files exist."""
    assert _EXTRACT.is_file()
    extract = json.loads(_EXTRACT.read_text("utf-8"))
    assert extract["gate"] == "R8 — Physical feasibility report"
    assert extract["chapter"] == "0040-area-process-model"
    assert extract["process_node"] == "28nm CMOS"

    assert (_DIAGRAM_DIR / "area-process-model-0040.svg").is_file()
    assert (_DIAGRAM_DIR / "area-tile-breakdown-0040.svg").is_file()
    assert (_DIAGRAM_DIR / "area-floorplan-0040.svg").is_file()
    assert (_DIAGRAM_DIR / "area-scaling-0040.svg").is_file()
