import numpy as np

from analog_ai.tiling import tiled_mvm

matrix = np.arange(1, 21, dtype=float).reshape(4, 5)
vector = np.array([1.0, -1.0, 0.5, 2.0, -0.25])
reference = matrix @ vector
actual = tiled_mvm(matrix, vector, tile_rows=2, tile_cols=3)
np.testing.assert_allclose(actual, reference)
print("dense reference:", reference)
print("tiled result:   ", actual)
