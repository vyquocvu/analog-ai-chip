import numpy as np

from analog_ai.crossbar import differential_mvm, map_differential

weights = np.array([[1.0, -2.0], [-0.5, 3.0]])
inputs = np.array([2.0, 1.0])
g_pos, g_neg = map_differential(weights, g_scale=4.0)
actual = differential_mvm(inputs, g_pos, g_neg, g_scale=4.0)
expected = np.array([0.0, 2.0])
np.testing.assert_allclose(actual, expected)
assert np.all(g_pos >= 0) and np.all(g_neg >= 0)
print("signed output:", actual)
