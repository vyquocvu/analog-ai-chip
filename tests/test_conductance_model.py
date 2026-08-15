"""Tests for Chapter 0015 — Programmable Conductance Compact Model."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parent.parent
_MODULE = _REPO / "book" / "0015-conductance-model" / "conductance_model.py"
_EXTRACT = _REPO / "verification" / "circuit" / "results" / "conductance-model-0015-extract.json"


def _load_module():
    spec = importlib.util.spec_from_file_location("conductance_model_0015", _MODULE)
    if spec is None or spec.loader is None:
        return None
    import sys
    mod = importlib.util.module_from_spec(spec)
    sys.modules["conductance_model_0015"] = mod
    spec.loader.exec_module(mod)
    return mod


mod = _load_module()


def test_module_loaded() -> None:
    assert mod is not None, "Failed to load book/0015-conductance-model/conductance_model.py"


def test_compact_model_parameters() -> None:
    """Validate default model constants and property calculations."""
    assert mod is not None
    cell = mod.ConductanceCellModel()
    assert cell.g_min == pytest.approx(10.0e-6)
    assert cell.g_max == pytest.approx(100.0e-6)
    assert cell.span == pytest.approx(90.0e-6)
    assert cell.num_states == 16
    assert cell.v_read_max == pytest.approx(0.25)


def test_conductance_state_discretization() -> None:
    """Check 4-bit and 6-bit state spacing and endpoints."""
    assert mod is not None
    c4 = mod.ConductanceCellModel(bits=4)
    levels4 = c4.conductance_levels
    assert len(levels4) == 16
    assert levels4[0] == pytest.approx(10.0e-6)
    assert levels4[-1] == pytest.approx(100.0e-6)
    step4 = 90.0e-6 / 15
    assert (levels4[1] - levels4[0]) == pytest.approx(step4)

    c6 = mod.ConductanceCellModel(bits=6)
    levels6 = c6.conductance_levels
    assert len(levels6) == 64
    assert levels6[0] == pytest.approx(10.0e-6)
    assert levels6[-1] == pytest.approx(100.0e-6)


def test_differential_weight_mapping() -> None:
    """Signed weights map to (G+, G-) and resolve w_eff accurately."""
    assert mod is not None
    cell = mod.ConductanceCellModel(bits=4)

    # 1. Zero weight
    gp, gm, weff, ip, im = cell.map_signed_weight(0.0)
    assert gp == pytest.approx(10.0e-6)
    assert gm == pytest.approx(10.0e-6)
    assert weff == pytest.approx(0.0)
    assert ip == 0 and im == 0

    # 2. Positive full-scale weight
    gp, gm, weff, ip, im = cell.map_signed_weight(1.0)
    assert gp == pytest.approx(100.0e-6)
    assert gm == pytest.approx(10.0e-6)
    assert weff == pytest.approx(1.0)
    assert ip == 15 and im == 0

    # 3. Negative full-scale weight
    gp, gm, weff, ip, im = cell.map_signed_weight(-1.0)
    assert gp == pytest.approx(10.0e-6)
    assert gm == pytest.approx(100.0e-6)
    assert weff == pytest.approx(-1.0)
    assert ip == 0 and im == 15

    # 4. Quantization bound for any w
    max_step = 1.0 / (cell.num_states - 1)
    for w in [-0.85, -0.33, 0.12, 0.47, 0.76]:
        _, _, w_eff, _, _ = cell.map_signed_weight(w)
        assert abs(w_eff - w) <= max_step / 2.0 + 1e-9


def test_invalid_parameters_raise() -> None:
    """Fail-closed on invalid compact model parameters."""
    assert mod is not None
    with pytest.raises(ValueError, match="0 < g_min < g_max"):
        mod.ConductanceCellModel(g_min=100e-6, g_max=10e-6)
    with pytest.raises(ValueError, match="0 < g_min < g_max"):
        mod.ConductanceCellModel(g_min=-10e-6, g_max=100e-6)
    with pytest.raises(ValueError, match="v_read_max"):
        mod.ConductanceCellModel(v_read_max=-0.5)


def test_committed_extract_integrity() -> None:
    """Validate structure and metrics of the committed extract JSON."""
    assert _EXTRACT.exists(), f"Missing extract artifact at {_EXTRACT}"
    with open(_EXTRACT) as f:
        data = json.load(f)

    assert data["schema_version"] == "0.1.0"
    assert data["chapter"] == "0015-conductance-model"
    assert data["model_parameters"]["g_min_uS"] == pytest.approx(10.0)
    assert data["model_parameters"]["g_max_uS"] == pytest.approx(100.0)
    assert data["model_parameters"]["span_uS"] == pytest.approx(90.0)
    assert data["model_parameters"]["dynamic_range_ratio"] == pytest.approx(10.0)
    assert len(data["states_4bit"]) == 16


def test_diagram_svgs_exist() -> None:
    """Verify presence of Chapter 0015 SVG diagrams."""
    diag_dir = _REPO / "book" / "0015-conductance-model" / "diagrams"
    assert (diag_dir / "cell_model.svg").is_file(), "Missing cell_model.svg"
    assert (diag_dir / "state_levels.svg").is_file(), "Missing state_levels.svg"
