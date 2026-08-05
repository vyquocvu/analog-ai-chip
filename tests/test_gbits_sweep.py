import numpy as np

from analog_llm.crossbar import map_differential

GMIN, GMAX = 0.05, 1.0


def _err(weights, bits):
    _, _, w_eff = map_differential(weights, bits, gmin=GMIN, gmax=GMAX)
    return float(np.max(np.abs(weights - w_eff / (GMAX - GMIN))))


def test_weight_error_falls_with_more_bits() -> None:
    w = np.linspace(-1.0, 1.0, 201)
    errs = [_err(w, b) for b in (2, 3, 4, 6, 8)]
    assert all(errs[i + 1] < errs[i] for i in range(len(errs) - 1))


def test_weight_error_matches_analytic_bound() -> None:
    w = np.linspace(-1.0, 1.0, 1001)
    for b in (3, 5, 7, 10):
        bound = 1.0 / (2 * (2 ** b - 1))
        np.testing.assert_allclose(_err(w, b), bound, atol=1e-6)


def test_high_resolution_is_precise() -> None:
    w = np.linspace(-1.0, 1.0, 101)
    assert _err(w, 14) < 1e-3
