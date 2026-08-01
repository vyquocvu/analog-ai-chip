import numpy as np

from analog_ai.quantization import quantize_symmetric


def test_symmetric_quantization_is_bounded_and_deterministic() -> None:
    values = np.array([-1.0, -0.3, 0.0, 0.2, 1.0])
    quantized, scale = quantize_symmetric(values, bits=4)
    assert scale == 1.0 / 7.0
    assert np.max(np.abs(quantized - values)) <= scale / 2 + 1e-12
