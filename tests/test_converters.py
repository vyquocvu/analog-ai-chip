import numpy as np
import pytest

from analog_llm.converters import adc, dac, symmetric_converter


def test_dac_quantizes_with_bounded_error_and_clip() -> None:
    x = np.array([-1.0, 0.0, 0.3, 1.0])
    y = dac(x, bits=4, vmax=1.0)
    assert np.max(np.abs(y - x)) <= (1.0 / 7.0) / 2 + 1e-12
    assert np.all(y >= -1.0) and np.all(y <= 1.0)


def test_dac_clips_out_of_range() -> None:
    y = dac([3.0, -3.0], bits=8, vmax=1.0)
    assert np.all(y == 1.0) or np.allclose(y, [1.0, -1.0])


def test_adc_applies_gain_offset_and_noise() -> None:
    rng = np.random.default_rng(3)
    x = np.array([0.4, -0.2])
    y = adc(x, bits=14, vmax=1.0, gain=1.5, offset=0.1, noise_std=0.001, rng=rng)
    assert np.allclose(y, (x * 1.5 + 0.1), atol=0.005)


def test_adc_noise_requires_rng() -> None:
    with pytest.raises(ValueError, match="rng is required"):
        adc([0.1], bits=8, noise_std=0.01)


def test_invalid_bits_rejected() -> None:
    for bad in (0, 1):
        with pytest.raises(ValueError, match="bits"):
            symmetric_converter([0.1], bits=bad)


def test_invalid_parameters_rejected() -> None:
    with pytest.raises(ValueError, match="vmax"):
        symmetric_converter([0.1], bits=8, vmax=0.0)
    with pytest.raises(ValueError, match="noise_std"):
        symmetric_converter([0.1], bits=8, noise_std=-1.0)
