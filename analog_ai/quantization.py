"""Converter-oriented quantization helpers."""

from __future__ import annotations

import numpy as np
from numpy.typing import ArrayLike, NDArray


def quantize_symmetric(values: ArrayLike, bits: int) -> tuple[NDArray[np.float64], float]:
    """Quantize and dequantize around zero, returning values and scale.

    The function models the numerical effect of an ideal symmetric converter. It
    intentionally does not model circuit timing, energy, saturation recovery, or INL/DNL.
    """
    if bits < 2:
        raise ValueError("bits must be at least 2")
    x = np.asarray(values, dtype=np.float64)
    peak = float(np.max(np.abs(x))) if x.size else 0.0
    if peak == 0.0:
        return x.copy(), 1.0
    qmax = 2 ** (bits - 1) - 1
    scale = peak / qmax
    codes = np.clip(np.rint(x / scale), -qmax, qmax)
    return codes * scale, scale
