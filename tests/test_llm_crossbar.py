import numpy as np
import pytest

from analog_llm.crossbar import map_differential, mvm, scale_weights


def test_scale_weights_normalizes_to_unit_peak() -> None:
    w = np.array([[2.0, -4.0], [1.0, 0.5]])
    assert np.max(np.abs(scale_weights(w))) == pytest.approx(1.0)


def test_zero_weight_maps_to_balanced_cells() -> None:
    gp, gn, we = map_differential(np.array([[0.0, 0.0]]), bits=4, gmin=0.05, gmax=1.0)
    assert np.all(gp == 0.05) and np.all(gn == 0.05)
    assert np.allclose(we, 0.0)


def test_positive_and_negative_extremes() -> None:
    gp, gn, we = map_differential(np.array([[1.0, -1.0]]), bits=8, gmin=0.05, gmax=1.0)
    assert np.allclose(gp[0, 0], 1.0) and np.allclose(gn[0, 0], 0.05)
    assert np.allclose(gp[0, 1], 0.05) and np.allclose(gn[0, 1], 1.0)
    assert np.allclose(we, [1.0 - 0.05, -(1.0 - 0.05)])


def test_map_differential_effective_weight_stays_in_range() -> None:
    w = np.array([[0.0, 0.4, -0.7, 1.0, -1.0]])
    _, _, we = map_differential(w, bits=5, gmin=0.05, gmax=1.0)
    rng_span = 1.0 - 0.05
    assert np.all(we <= rng_span + 1e-12)
    assert np.all(we >= -rng_span - 1e-12)


def test_mvm_matches_hand_calculation_at_high_bits() -> None:
    v = np.array([0.2, 0.5])
    gp = np.array([[1.0, 0.05], [0.05, 1.0]])
    gn = np.zeros((2, 2))
    gn[:, :] = 0.05
    y = mvm(v, gp, gn, dac_bits=24, vin_max=1.0)
    expected = np.array([(1.0 - 0.05) * 0.2 + 0.0 * 0.5, 0.0 * 0.2 + (1.0 - 0.05) * 0.5])
    np.testing.assert_allclose(y, expected, atol=1e-3)


def test_invalid_bits_rejected() -> None:
    with pytest.raises(ValueError, match="bits"):
        map_differential(np.zeros((1, 2)), bits=0)


def test_invalid_g_range_rejected() -> None:
    with pytest.raises(ValueError, match="gmin < gmax"):
        map_differential(np.zeros((1, 2)), bits=4, gmin=1.0, gmax=0.5)


def test_out_of_range_and_nonfinite_weights_rejected() -> None:
    with pytest.raises(ValueError, match=r"in \[-1, 1\]"):
        map_differential(np.array([[1.5]]), bits=4)
    with pytest.raises(ValueError, match="finite"):
        map_differential(np.array([[np.nan]]), bits=4)
