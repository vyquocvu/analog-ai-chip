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


def test_rejects_non_2x2_weight_shape() -> None:
    mod = _load_module()
    with pytest.raises(ValueError, match="2x2"):
        mod.ideal_mvm([3.0, 2.1], [[0.5, 0.25, 0.0], [0.1, 0.2, 0.3]])


def test_rejects_non_two_input_vector() -> None:
    mod = _load_module()
    with pytest.raises(ValueError, match="2 inputs"):
        mod.ideal_mvm([3.0], [[0.5, 0.25], [-0.5, 0.25]])


def test_spice_2x2_matches_ideal_when_engine_available() -> None:
    mod = _load_module()
    try:
        got = mod.run_array([3.0, 2.1], [[0.50, 0.25], [-0.50, 0.25]])
    except (ImportError, OSError):
        pytest.skip("PySpice/ngspice not available")

    expected = mod.ideal_mvm([3.0, 2.1], [[0.50, 0.25], [-0.50, 0.25]])
    np.testing.assert_allclose(got, expected, atol=2e-2, rtol=0.0)
