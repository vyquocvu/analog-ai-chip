import numpy as np

from analog_ai.crossbar import ideal_mvm

voltages = np.array([0.2, 0.5])
conductance = np.array([[2.0, 1.0], [0.5, 3.0]])
expected = np.array([0.9, 1.6])
actual = ideal_mvm(voltages, conductance)
np.testing.assert_allclose(actual, expected)
print("crossbar currents:", actual)
