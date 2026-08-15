"""Tests for Chapter 0019 — Conductance Drift, Stuck-at Faults & I-V Non-Linearity."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import numpy as np
import pytest

_REPO = Path(__file__).resolve().parent.parent
_MODULE = _REPO / "book" / "0019-drift-faults" / "drift_faults.py"
_EXTRACT = _REPO / "verification" / "circuit" / "results" / "drift-faults-0019-extract.json"


def _load_module():
    spec = importlib.util.spec_from_file_location("drift_faults_0019", _MODULE)
    if spec is None or spec.loader is None:
        return None
    mod = importlib.util.module_from_spec(spec)
    sys.modules["drift_faults_0019"] = mod
    spec.loader.exec_module(mod)
    return mod


mod = _load_module()


def test_module_loaded() -> None:
    assert mod is not None, "Failed to load book/0019-drift-faults/drift_faults.py"


def test_temporal_conductance_drift() -> None:
    """Test power-law drift invariants."""
    assert mod is not None
    cfg = mod.DriftConfig(nu_min=0.02, nu_max=0.06, t0_s=1.0)

    g_lrs = 100.0e-6
    g_hrs = 10.0e-6

    # 1. At t = t0, G(t) == G0 exactly
    assert cfg.evaluate_drift(g_lrs, 1.0) == pytest.approx(g_lrs)
    assert cfg.evaluate_drift(g_hrs, 1.0) == pytest.approx(g_hrs)

    # 2. Monotonic decay over time
    g_10s = cfg.evaluate_drift(g_lrs, 10.0)
    g_100s = cfg.evaluate_drift(g_lrs, 100.0)
    g_1yr = cfg.evaluate_drift(g_lrs, 3.15e7)

    assert g_lrs > g_10s > g_100s > g_1yr

    # 3. State-dependent exponent
    assert cfg.nu_for_conductance(g_lrs) == pytest.approx(0.06)
    assert cfg.nu_for_conductance(g_hrs) == pytest.approx(0.02)


def test_stuck_at_fault_injection() -> None:
    """Test spatial defect injection on crossbar matrix."""
    assert mod is not None
    cfg = mod.FaultConfig(p_hrs=0.04, p_lrs=0.01, seed=42)
    g_mat = np.full((32, 32), 50.0e-6)

    g_faulty, counts = cfg.inject_faults(g_mat)
    assert g_faulty.shape == (32, 32)
    assert counts["total_cells"] == 1024
    assert counts["stuck_hrs_count"] > 0
    assert counts["stuck_lrs_count"] > 0

    # Values in matrix are either intact (50 uS) or stuck at G_MIN (10 uS) or G_MAX (100 uS)
    unique_vals = np.unique(np.round(g_faulty * 1e6, 2))
    for v in unique_vals:
        assert v in [10.0, 50.0, 100.0]


def test_monotonic_mvm_error_with_fault_rate() -> None:
    """MVM relative error increases with higher defect probability."""
    assert mod is not None
    rng = np.random.default_rng(42)
    N = 16
    v_in = rng.uniform(0.0, 0.25, size=N)
    g_mat = rng.uniform(10e-6, 100e-6, size=(N, N))
    y_ideal = g_mat.T @ v_in

    cfg_low = mod.FaultConfig(p_hrs=0.01, p_lrs=0.002, seed=42)
    cfg_high = mod.FaultConfig(p_hrs=0.10, p_lrs=0.02, seed=42)

    g_low, _ = cfg_low.inject_faults(g_mat, rng)
    g_high, _ = cfg_high.inject_faults(g_mat, rng)

    err_low = np.linalg.norm(g_low.T @ v_in - y_ideal)
    err_high = np.linalg.norm(g_high.T @ v_in - y_ideal)

    assert err_high > err_low


def test_non_linear_iv_conduction() -> None:
    """Test cubic sub-Ohmic I-V non-linearity."""
    assert mod is not None
    cfg = mod.NonLinearConfig(beta=1.0)
    g0 = 100.0e-6

    # 1. Zero voltage draws zero current
    assert cfg.current(g0, 0.0) == pytest.approx(0.0)

    # 2. Odd symmetry: I(-V) == -I(V)
    assert cfg.current(g0, -0.20) == pytest.approx(-cfg.current(g0, 0.20))

    # 3. Super-linear current at non-zero voltage
    i_lin = g0 * 0.25
    i_act = cfg.current(g0, 0.25)
    expected_act = g0 * 0.25 * (1.0 + 1.0 * (0.25**2))
    assert i_act == pytest.approx(expected_act)
    assert i_act > i_lin
    assert (i_act - i_lin) / i_lin == pytest.approx(0.0625)


def test_committed_extract_integrity() -> None:
    """Validate structure and metrics of committed extract JSON."""
    assert _EXTRACT.exists(), f"Missing extract artifact at {_EXTRACT}"
    with open(_EXTRACT) as f:
        data = json.load(f)

    assert data["schema_version"] == "0.1.0"
    assert data["chapter"] == "0019-drift-faults"
    assert data["summary"]["max_drift_loss_1year_pct"] > 50.0
    assert data["summary"]["max_iv_distortion_pct"] == pytest.approx(6.25)


def test_diagram_svgs_exist() -> None:
    """Verify presence of Chapter 0019 SVG diagrams."""
    diag_dir = _REPO / "book" / "0019-drift-faults" / "diagrams"
    assert (diag_dir / "drift_faults_schematic.svg").is_file(), "Missing drift_faults_schematic.svg"
    assert (diag_dir / "drift_and_fault_effects.svg").is_file(), "Missing drift_and_fault_effects.svg"
