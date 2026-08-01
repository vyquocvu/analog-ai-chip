import numpy as np

from analog_ai.tiling import tiled_mvm


def test_tiled_mvm_matches_dense_reference() -> None:
    matrix = np.arange(1, 21, dtype=float).reshape(4, 5)
    vector = np.array([1.0, -1.0, 0.5, 2.0, -0.25])
    np.testing.assert_allclose(tiled_mvm(matrix, vector, 2, 3), matrix @ vector)
