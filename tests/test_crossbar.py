import numpy as np
import pytest

from analog_ai.crossbar import differential_mvm, ideal_mvm, map_differential


def test_ideal_crossbar_matches_hand_calculation() -> None:
    voltages = np.array([0.2, 0.5])
    conductance = np.array([[2.0, 1.0], [0.5, 3.0]])
    np.testing.assert_allclose(ideal_mvm(voltages, conductance), [0.9, 1.6])


def test_differential_pair_recovers_signed_matrix() -> None:
    weights = np.array([[1.0, -2.0], [-0.5, 3.0]])
    inputs = np.array([2.0, 1.0])
    g_pos, g_neg = map_differential(weights, g_scale=4.0)
    np.testing.assert_allclose(differential_mvm(inputs, g_pos, g_neg, 4.0), weights @ inputs)


def test_negative_physical_conductance_is_rejected() -> None:
    with pytest.raises(ValueError, match="cannot be negative"):
        ideal_mvm([1.0], [[-1.0]])
