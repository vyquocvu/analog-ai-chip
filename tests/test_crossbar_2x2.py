"""TDD contract for R3 / chapter 0012: a 2x2 differential crossbar array."""

import importlib.util
from pathlib import Path

import numpy as np
import pytest

MODULE = (
    Path(__file__).resolve().parent.parent
    / "book"
    / "0012-crossbar-2x2"
    / "crossbar_2x2.py"
)


def _load_module():
    assert MODULE.exists(), "0012 implementation must exist before this contract can pass"
    spec = importlib.util.spec_from_file_location("crossbar_2x2", MODULE)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_shared_rows_produce_two_independent_columns() -> None:
    mod = _load_module()
    xs = [3.0, 2.1]
    weights = [[0.50, 0.25], [-0.50, 0.25]]

    got = mod.ideal_mvm(xs, weights)

    expected = np.array([
        mod.RF * mod.GSCALE * (0.50 * 0.50 + (-0.40) * 0.25),
        mod.RF * mod.GSCALE * (0.50 * -0.50 + (-0.40) * 0.25),
    ])
    np.testing.assert_allclose(got, expected, atol=1e-12, rtol=0.0)


def test_differential_conductance_matrix_realizes_signed_weights() -> None:
    mod = _load_module()
    weights = np.array([[0.50, 0.25], [-0.50, 0.0]])

    gp, gm = mod.conductance_matrices(weights)

    np.testing.assert_allclose(gp - gm, weights * mod.GSCALE, atol=1e-15, rtol=0.0)
    assert np.all(gp >= mod.G0)
    assert np.all(gm >= mod.G0)


def test_zero_balanced_cells_produce_zero_output() -> None:
    mod = _load_module()
    xs = [3.0, 2.0]
    weights = [[0.0, 0.0], [0.0, 0.0]]

    gp, gm = mod.conductance_matrices(weights)
    np.testing.assert_allclose(gp, gm, atol=0.0, rtol=0.0)
    np.testing.assert_allclose(mod.ideal_mvm(xs, weights), [0.0, 0.0], atol=1e-15, rtol=0.0)


def test_headroom_report_distinguishes_safe_and_overdrive_cases() -> None:
    mod = _load_module()
    safe = mod.headroom_report([3.0, 2.1], [[0.50, 0.25], [-0.50, 0.25]])
    assert safe["within_rails"] is True
    assert safe["low_margin_v"] >= 0.0
    assert safe["high_margin_v"] >= 0.0

    # Full-rail inputs with maximum same-sign weights exceed this ideal TIA's
    # 0–5 V branch envelope. Detect the limitation instead of silently clipping.
    overdrive = mod.headroom_report([5.0, 5.0], [[1.0, 1.0], [-1.0, -1.0]])
    assert overdrive["within_rails"] is False
    assert min(overdrive["low_margin_v"], overdrive["high_margin_v"]) < 0.0


def test_shared_row_loading_is_explicit() -> None:
    mod = _load_module()
    report = mod.row_loading_report([3.0, 2.1], [[0.50, 0.25], [-0.50, 0.25]])

    assert report["driver_model"] == "ideal_voltage_source"
    assert len(report["row_conductance_s"]) == 2
    assert len(report["row_current_a"]) == 2
    assert report["max_abs_row_current_a"] > 0.0
    # Every differential cell includes the balanced G0 baseline, so sharing a
    # row across two output columns creates a non-zero load even for zero weight.
    assert all(g >= 4.0 * mod.G0 for g in report["row_conductance_s"])


def test_rejects_non_2x2_weight_shape() -> None:
    mod = _load_module()
    with pytest.raises(ValueError, match="2x2"):
        mod.ideal_mvm([3.0, 2.1], [[0.5, 0.25, 0.0], [0.1, 0.2, 0.3]])


def test_rejects_non_two_input_vector() -> None:
    mod = _load_module()
    with pytest.raises(ValueError, match="2 inputs"):
        mod.ideal_mvm([3.0], [[0.5, 0.25], [-0.5, 0.25]])


def test_rejects_weight_outside_normalized_range() -> None:
    mod = _load_module()
    with pytest.raises(ValueError, match=r"\[-1, 1\]"):
        mod.ideal_mvm([3.0, 2.1], [[1.01, 0.0], [0.0, 0.0]])


def test_spice_2x2_matches_ideal_when_engine_available() -> None:
    mod = _load_module()
    try:
        evidence = mod.spice_evidence([3.0, 2.1], [[0.50, 0.25], [-0.50, 0.25]])
    except OSError:
        pytest.skip("ngspice not available")

    assert evidence["evidence_class"] == "spice"
    assert evidence["simulator"] == "ngspice-cli"
    assert evidence["within_rails"] is True
    assert evidence["loading"]["driver_model"] == "ideal_voltage_source"
    np.testing.assert_allclose(
        evidence["spice_output_v"], evidence["expected_output_v"], atol=2e-2, rtol=0.0
    )
    assert evidence["max_abs_error_v"] <= 2e-2
