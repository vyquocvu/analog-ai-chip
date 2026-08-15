"""Tests for Chapter 0014 — Crossbar Array Timing, Loading, and Scaling Limits."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parent.parent
_MODULE = _REPO / "book" / "0014-array-timing" / "array_timing.py"
_EXTRACT = _REPO / "verification" / "circuit" / "results" / "array-timing-0014-extract.json"


def _load_module():
    try:
        spec = importlib.util.spec_from_file_location("array_timing_0014", _MODULE)
        if spec is None or spec.loader is None:
            return None
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod
    except Exception:  # noqa: BLE001
        return None


mod = _load_module()


def test_module_loaded() -> None:
    assert mod is not None, "Failed to load book/0014-array-timing/array_timing.py"


def test_noise_gain_closed_form() -> None:
    """Noise gain scales as 1 + N * RF * G0."""
    assert mod is not None
    assert mod.noise_gain_hand(2, mod.G0, mod.RF) == pytest.approx(3.0)
    assert mod.noise_gain_hand(4, mod.G0, mod.RF) == pytest.approx(5.0)
    assert mod.noise_gain_hand(8, mod.G0, mod.RF) == pytest.approx(9.0)
    assert mod.noise_gain_hand(16, mod.G0, mod.RF) == pytest.approx(17.0)
    assert mod.noise_gain_hand(32, mod.G0, mod.RF) == pytest.approx(33.0)
    assert mod.noise_gain_hand(64, mod.G0, mod.RF) == pytest.approx(65.0)


def test_dc_gain_error_hand_formula() -> None:
    """Theoretical fractional gain error = NG / (A_OL + NG)."""
    assert mod is not None
    err_2 = mod.dc_gain_error_hand(2, mod.A_OL, mod.G0, mod.RF)
    assert err_2 == pytest.approx(3.0 / (10000.0 + 3.0))

    err_64 = mod.dc_gain_error_hand(64, mod.A_OL, mod.G0, mod.RF)
    assert err_64 == pytest.approx(65.0 / (10000.0 + 65.0))
    assert err_64 > err_2


def test_committed_extract_integrity() -> None:
    """Validate schema, constants, and monotonic scaling in the committed extract JSON."""
    assert _EXTRACT.exists(), f"Missing extract artifact at {_EXTRACT}"
    with open(_EXTRACT) as f:
        data = json.load(f)

    assert data["schema_version"] == "0.1.0"
    assert data["chapter"] == "0014-array-timing"
    assert data["constants"]["vref_v"] == pytest.approx(2.5)
    assert data["constants"]["rf_ohm"] == pytest.approx(10000.0)

    rows = data["row_scaling_sweep"]
    assert len(rows) == 6  # N in [2, 4, 8, 16, 32, 64]

    # Check noise gain increases monotonically with row count
    for i in range(len(rows) - 1):
        assert rows[i + 1]["n_rows"] > rows[i]["n_rows"]
        assert rows[i + 1]["noise_gain"] > rows[i]["noise_gain"]
        assert rows[i + 1]["expected_gain_error"] > rows[i]["expected_gain_error"]


def test_spice_row_scaling_sweep() -> None:
    """Run SPICE scaling sweep for N in [2, 4, 8, 16] and verify accuracy within 2 mV."""
    if mod is None or not getattr(mod, "_PYSPICE_OK", False):
        pytest.skip("PySpice/ngspice engine not available")
    sweep = mod.sweep_row_scaling([2, 4, 8, 16])
    assert len(sweep) == 4
    for entry in sweep:
        assert entry["mvm_abs_error"] < 2.0e-3  # under 2 mV error envelope
        assert abs(entry["vn_plus_err"]) < 1.0e-3


def test_diagram_svgs_exist() -> None:
    """Verify that theory and scaling plot SVGs exist."""
    diag_dir = _REPO / "book" / "0014-array-timing" / "diagrams"
    assert (diag_dir / "theory.svg").is_file(), "Missing theory.svg"
    assert (diag_dir / "scaling_plots.svg").is_file(), "Missing scaling_plots.svg"

