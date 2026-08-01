"""Small, explicit crossbar models used by the first lessons."""

from __future__ import annotations

import numpy as np
from numpy.typing import ArrayLike, NDArray


def ideal_mvm(voltages: ArrayLike, conductance: ArrayLike) -> NDArray[np.float64]:
    """Return column currents for a row-voltage crossbar.

    Conductance is shaped ``(outputs, inputs)``. The result is G @ V, equivalent
    to summing each column's cell currents under the orientation used by the book.
    """
    v = np.asarray(voltages, dtype=np.float64)
    g = np.asarray(conductance, dtype=np.float64)
    if v.ndim != 1 or g.ndim != 2 or g.shape[1] != v.shape[0]:
        raise ValueError("expected voltages [inputs] and conductance [outputs, inputs]")
    if np.any(g < 0):
        raise ValueError("physical conductance cannot be negative")
    return g @ v


def map_differential(weights: ArrayLike, g_scale: float = 1.0) -> tuple[NDArray, NDArray]:
    """Map signed weights to non-negative differential conductances."""
    if g_scale <= 0:
        raise ValueError("g_scale must be positive")
    w = np.asarray(weights, dtype=np.float64)
    return np.clip(w, 0, None) * g_scale, np.clip(-w, 0, None) * g_scale


def differential_mvm(
    inputs: ArrayLike, g_pos: ArrayLike, g_neg: ArrayLike, g_scale: float = 1.0
) -> NDArray[np.float64]:
    """Compute W @ x from two physical arrays where W=(G+ - G-)/g_scale."""
    if g_scale <= 0:
        raise ValueError("g_scale must be positive")
    return (ideal_mvm(inputs, g_pos) - ideal_mvm(inputs, g_neg)) / g_scale
