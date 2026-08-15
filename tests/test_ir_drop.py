"""Tests for Chapter 0017 — IR Drop & Interconnect Line Resistance."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import numpy as np
import pytest

_REPO = Path(__file__).resolve().parent.parent
_MODULE = _REPO / "book" / "0017-ir-drop" / "ir_drop.py"
_EXTRACT = _REPO / "verification" / "circuit" / "results" / "ir-drop-0017-extract.json"


def _load_module():
    spec = importlib.util.spec_from_file_location("ir_drop_0017", _MODULE)
    if spec is None or spec.loader is None:
        return None
    mod = importlib.util.module_from_spec(spec)
    sys.modules["ir_drop_0017"] = mod
    spec.loader.exec_module(mod)
    return mod


mod = _load_module()


def test_module_loaded() -> None:
    assert mod is not None, "Failed to load book/0017-ir-drop/ir_drop.py"


def test_ideal_zero_wire_resistance_limit() -> None:
    """With R_wire = 0, nodal solver reproduces ideal matrix multiplication exactly."""
    assert mod is not None
    N, M = 4, 4
    v_in = np.array([2.6, 2.7, 2.55, 2.65])
    g_mat = np.full((N, M), 50.0e-6)
    vref = 2.5

    sol = mod.solve_crossbar_nodal(v_in, g_mat, r_wire=0.0, vref=vref)
    assert sol["rel_error_pct"] == pytest.approx(0.0)

    u_in = v_in - vref
    i_expected = g_mat.T @ u_in
    np.testing.assert_allclose(sol["i_out"], i_expected, rtol=1e-12)


def test_monotonic_error_scaling_with_rwire() -> None:
    """MVM relative error strictly increases with wire resistance."""
    assert mod is not None
    N, M = 8, 8
    v_in = np.full(N, 2.75)
    g_mat = np.full((N, M), 100.0e-6)

    sol_05 = mod.solve_crossbar_nodal(v_in, g_mat, r_wire=0.5)
    sol_10 = mod.solve_crossbar_nodal(v_in, g_mat, r_wire=1.0)
    sol_20 = mod.solve_crossbar_nodal(v_in, g_mat, r_wire=2.0)

    assert sol_05["rel_error_pct"] < sol_10["rel_error_pct"]
    assert sol_10["rel_error_pct"] < sol_20["rel_error_pct"]


def test_monotonic_error_scaling_with_array_dimension() -> None:
    """MVM relative error strictly increases with array size N."""
    assert mod is not None
    r_wire = 1.0

    errors = []
    for n in [4, 8, 16, 32]:
        v_in = np.full(n, 2.75)
        g_mat = np.full((n, n), 100.0e-6)
        sol = mod.solve_crossbar_nodal(v_in, g_mat, r_wire=r_wire)
        errors.append(sol["rel_error_pct"])

    for i in range(len(errors) - 1):
        assert errors[i + 1] > errors[i]


def test_far_corner_voltage_deficit() -> None:
    """Cell (0, M-1) furthest from row driver (left) and col TIA (bottom) has lowest voltage."""
    assert mod is not None
    N, M = 8, 8
    v_in = np.full(N, 2.75)
    g_mat = np.full((N, M), 100.0e-6)
    sol = mod.solve_crossbar_nodal(v_in, g_mat, r_wire=1.0)

    v_cell = sol["v_cell"]
    # Cell (N-1, 0) is closest to both left driver and bottom TIA
    # Cell (0, M-1) is furthest from both
    assert v_cell[N - 1, 0] > v_cell[0, M - 1]
    assert np.min(v_cell) == pytest.approx(v_cell[0, M - 1])


def test_pyspice_cross_validation_4x4() -> None:
    """Validate NumPy nodal solver against PySpice operating point on 4x4 mesh."""
    if mod is None or not getattr(mod, "_PYSPICE_OK", False):
        pytest.skip("PySpice engine not available")

    N, M = 4, 4
    v_in = np.array([2.70, 2.60, 2.65, 2.75])
    g_mat = np.array([
        [100e-6, 50e-6, 20e-6, 10e-6],
        [10e-6, 100e-6, 50e-6, 20e-6],
        [20e-6, 10e-6, 100e-6, 50e-6],
        [50e-6, 20e-6, 10e-6, 100e-6],
    ])
    r_wire = 1.0

    # 1. Nodal solve
    sol_nodal = mod.solve_crossbar_nodal(v_in, g_mat, r_wire=r_wire)

    # 2. PySpice solve
    c = mod._build_pyspice_crossbar(v_in, g_mat, r_wire=r_wire)
    sim = c.simulator()
    res = sim.operating_point()

    spice_i_out = []
    vref_spice = float(np.ravel(np.asarray(res["vref"]))[0])
    for j in range(M):
        v_c_last = float(np.ravel(np.asarray(res[f"c_{N-1}_{j}"]))[0])
        # Current exiting bottom column node through r_wire into vref
        i_s = (v_c_last - vref_spice) / r_wire
        spice_i_out.append(i_s)

    np.testing.assert_allclose(sol_nodal["i_out"], spice_i_out, rtol=1e-5, atol=1e-10)


def test_committed_extract_integrity() -> None:
    """Validate structure and metrics of committed extract JSON."""
    assert _EXTRACT.exists(), f"Missing extract artifact at {_EXTRACT}"
    with open(_EXTRACT) as f:
        data = json.load(f)

    assert data["schema_version"] == "0.1.0"
    assert data["chapter"] == "0017-ir-drop"
    assert len(data["scaling_results"]) == 6  # [2, 4, 8, 16, 32, 64]
    assert data["summary"]["recommended_max_tile_dim"] == 32


def test_diagram_svgs_exist() -> None:
    """Verify presence of Chapter 0017 SVG diagrams."""
    diag_dir = _REPO / "book" / "0017-ir-drop" / "diagrams"
    assert (diag_dir / "ir_drop_schematic.svg").is_file(), "Missing ir_drop_schematic.svg"
    assert (diag_dir / "ir_drop_scaling.svg").is_file(), "Missing ir_drop_scaling.svg"
