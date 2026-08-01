import numpy as np

from analog_ai.quantization import quantize_symmetric

values = np.array([-1.0, -0.3, 0.0, 0.2, 1.0])
quantized, scale = quantize_symmetric(values, bits=4)
error = np.abs(quantized - values)
assert np.max(error) <= scale / 2 + 1e-12

rng = np.random.default_rng(7)
ideal = np.array([0.9, 1.6])
noisy = ideal + rng.normal(0.0, 0.01, size=ideal.shape)
print("quantized:", quantized)
print("max quantization error:", np.max(error))
print("deterministic noisy sample:", noisy)
