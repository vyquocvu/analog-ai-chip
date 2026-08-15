"""Tests for Chapter 0018 — Parasitic Capacitance, RC Dynamics & Transient Settling."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parent.parent
_MODULE = _REPO / "book" / "0018-parasitics" / "parasitics.py"
_EXTRACT = _REPO / "verification" / "circuit" / "results" / "parasitics-0018-extract.json"


def _load_module():
    spec = importlib.util.spec_from_file_location("parasitics_0018", _MODULE)
    if spec is None or spec.loader is None:
        return None
    mod = importlib.util.module_from_spec(spec)
    sys.modules["parasitics_0018"] = mod
    spec.loader.exec_module(mod)
    return mod


mod = _load_module()


def test_module_loaded() -> None:
    assert mod is not None, "Failed to load book/0018-parasitics/parasitics.py"


def test_parasitic_constants() -> None:
    """Validate default RC segment parasitic constants."""
    assert mod is not None
    assert mod.R_WIRE_OHM == pytest.approx(1.0)
    assert mod.C_WIRE_FF == pytest.approx(0.5)
    assert mod.C_CELL_FF == pytest.approx(1.0)
    assert mod.C_SEG_FF == pytest.approx(1.5)
    assert mod.VREF == pytest.approx(2.5)
    assert mod.V_STEP == pytest.approx(0.25)


def test_spice_deck_builder() -> None:
    """Verify generated SPICE deck structure."""
    assert mod is not None
    deck = mod.build_rc_crossbar_deck(N=4, M=1)
    assert "PULSE" in deck
    assert "Rrw_0_0" in deck
    assert "Ccr_0_0" in deck
    assert "Rcell_0_0" in deck
    assert ".tran" in deck


def test_transient_settling_metrics() -> None:
    """Test transient step response for 16-row crossbar."""
    assert mod is not None
    res = mod.simulate_transient_settling(N=16, M=1)

    assert res["N"] == 16
    assert 10.0 <= res["t_rise_ps"] <= 30.0
    assert 10.0 <= res["t_settle_1pct_ps"] <= 40.0
    assert res["f_max_ghz"] >= 25.0
    assert 20.0 <= res["i_ss_uA"] <= 26.0


def test_monotonic_settling_growth_with_array_size() -> None:
    """Settling time increases with array size N."""
    assert mod is not None
    res_4 = mod.simulate_transient_settling(N=4, M=1)
    res_64 = mod.simulate_transient_settling(N=64, M=1)

    assert res_64["t_settle_1pct_ps"] >= res_4["t_settle_1pct_ps"]
    assert res_64["i_ss_uA"] < res_4["i_ss_uA"]  # IR drop reduces steady-state current


def test_committed_extract_integrity() -> None:
    """Validate structure and metrics of committed extract JSON."""
    assert _EXTRACT.exists(), f"Missing extract artifact at {_EXTRACT}"
    with open(_EXTRACT) as f:
        data = json.load(f)

    assert data["schema_version"] == "0.1.0"
    assert data["chapter"] == "0018-parasitics"
    assert len(data["sweep_results"]) == 5  # [4, 8, 16, 32, 64]
    assert data["summary"]["f_max_16x16_ghz"] >= 30.0


def test_diagram_svgs_exist() -> None:
    """Verify presence of Chapter 0018 SVG diagrams."""
    diag_dir = _REPO / "book" / "0018-parasitics" / "diagrams"
    assert (diag_dir / "rc_parasitics_schematic.svg").is_file(), "Missing rc_parasitics_schematic.svg"
    assert (diag_dir / "transient_settling.svg").is_file(), "Missing transient_settling.svg"
