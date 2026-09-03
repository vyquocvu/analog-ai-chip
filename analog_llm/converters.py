"""Converter models (DAC / ADC) for a hybrid analog-digital LLM accelerator.

Signal convention
-----------------
Everything entering or leaving a crossbar is a real number in a normalized
voltage domain ``[-vmax, vmax]``. A ``DAC`` turns an ideal digital value into
a quantized analog voltage; an ``ADC`` turns a real analog voltage back into a
quantized digital value. Both are symmetric about zero.

Non-idealities modelled here
----------------------------
- finite resolution (``bits``),
- clipping / saturation at ``+/- vmax`` (the input must stay in range),
- additive Gaussian noise at the ADC input (``noise_std``),
- a static gain error and offset error on the analog path.

What is deliberately NOT modelled
---------------------------------
INL/DNL, thermal drift over time, converter energy, and recovery after
saturation. This keeps the model small and deterministic while still exposing
the dominant numerical error sources of a converter.
"""

from __future__ import annotations

import numpy as np
from numpy.typing import ArrayLike, NDArray


def _check_bits(bits: int) -> None:
    if int(bits) != bits or bits < 2:
        raise ValueError("bits must be an integer >= 2")


def _qmax(bits: int) -> int:
    return 2 ** (bits - 1) - 1


def symmetric_converter(
    values: ArrayLike,
    bits: int,
    vmax: float = 1.0,
    gain: float = 1.0,
    offset: float = 0.0,
    noise_std: float = 0.0,
    rng: np.random.Generator | None = None,
) -> NDArray[np.float64]:
    """Quantize ``values`` to a symmetric ``bits``-bit converter output.

    Applies the same symmetric quantization a DAC and an ADC share, plus
    optional analog-path gain/offset and input noise. Output is clipped to
    ``[-vmax, vmax]`` and returned in the voltage domain (dequantized codes).
    """
    _check_bits(bits)
    if vmax <= 0:
        raise ValueError("vmax must be positive")
    if noise_std < 0:
        raise ValueError("noise_std must be non-negative")

    x = np.asarray(values, dtype=np.float64)
    if gain != 1.0 or offset != 0.0:
        x = x * gain + offset
    if noise_std > 0:
        if rng is None:
            raise ValueError("rng is required when noise_std > 0")
        x = x + rng.normal(0.0, noise_std, size=x.shape)

    x = np.clip(x, -vmax, vmax)
    qmax = _qmax(bits)
    scale = vmax / qmax
    codes = np.clip(np.rint(x / scale), -qmax, qmax)
    return codes * scale


def dac(
    values: ArrayLike, bits: int, vmax: float = 1.0
) -> NDArray[np.float64]:
    """Digital value -> quantized analog voltage (finite resolution + clip)."""
    return symmetric_converter(values, bits, vmax=vmax)


def adc(
    voltages: ArrayLike,
    bits: int,
    vmax: float = 1.0,
    gain: float = 1.0,
    offset: float = 0.0,
    noise_std: float = 0.0,
    rng: np.random.Generator | None = None,
) -> NDArray[np.float64]:
    """Analog voltage -> dequantized digital value with realistic errors."""
    return symmetric_converter(
        voltages, bits, vmax=vmax, gain=gain, offset=offset,
        noise_std=noise_std, rng=rng,
    )
