"""Crossbar models with programmable conductance and differential signed weights.

A crossbar stores a non-negative conductance per cell ``G >= 0``. A signed
weight ``w`` is encoded differentially in two arrays ``(G+, G-)`` of
programmable conductances that resolve to ``w_eff = G+ - G-``.

Physical units
--------------
Conductance ``G`` is expressed in the range ``[gmin, gmax]`` (both positive),
where ``gmin`` is the balanced zero-weight cell and ``gmax`` the strongest
cell. ``bits`` selects how many programmable conductance levels exist between
them, so the effective weight resolution is finite. This is the dominant
weight-side non-ideality: conductance quantization.
"""

from __future__ import annotations

import numpy as np
from numpy.typing import ArrayLike, NDArray

from .converters import dac


def scale_weights(weights: ArrayLike) -> NDArray[np.float64]:
    """Normalize signed weights to ``[-1, 1]`` (or zero vector)."""
    w = np.asarray(weights, dtype=np.float64)
    peak = float(np.max(np.abs(w))) if w.size else 0.0
    if peak == 0.0:
        return w.copy()
    return w / peak


def map_differential(
    weights: ArrayLike,
    bits: int,
    gmin: float = 0.05,
    gmax: float = 1.0,
) -> tuple[NDArray[np.float64], NDArray[np.float64], NDArray[np.float64]]:
    """Map signed ``weights`` (already in ``[-1, 1]``) to programmable cells.

    Returns ``(G_pos, G_neg, w_eff)`` where ``w_eff = G_pos - G_neg`` is the
    effective signed weight realized by the quantized conductances.

    ``bits`` is the number of programmable levels of each conductance cell.
    A weight of 0 maps to ``(gmin, gmin)`` and resolves to ``0`` exactly.
    """
    if int(bits) != bits or bits < 1:
        raise ValueError("bits must be an integer >= 1")
    if gmax <= gmin or gmin <= 0:
        raise ValueError("requires 0 < gmin < gmax")

    w = np.asarray(weights, dtype=np.float64)
    if np.any(~np.isfinite(w)):
        raise ValueError("weights must be finite")
    if w.size and (np.max(np.abs(w)) > 1.0 + 1e-9):
        raise ValueError("weights must be in [-1, 1]; call scale_weights first")

    w_pos = np.clip(w, 0.0, 1.0)
    w_neg = np.clip(-w, 0.0, 1.0)

    levels = np.linspace(gmin, gmax, 2**bits)

    def quantize(v: NDArray[np.float64]) -> NDArray[np.float64]:
        idx = np.rint((v - gmin) / (gmax - gmin) * (2**bits - 1))
        idx = np.clip(idx, 0.0, 2**bits - 1).astype(int)
        return levels[idx]

    g_pos = np.zeros_like(w)
    g_neg = np.zeros_like(w)
    g_pos[w_pos > 0] = quantize(gmin + w_pos[w_pos > 0] * (gmax - gmin))
    g_neg[w_neg > 0] = quantize(gmin + w_neg[w_neg > 0] * (gmax - gmin))
    g_pos[w_pos == 0] = gmin
    g_neg[w_neg == 0] = gmin

    return g_pos, g_neg, g_pos - g_neg


def mvm(
    voltages: ArrayLike,
    g_pos: ArrayLike,
    g_neg: ArrayLike,
    dac_bits: int,
    vin_max: float = 1.0,
) -> NDArray[np.float64]:
    """Column currents (as effective weighted sums) for a differential crossbar.

    Inputs are quantized by a DAC, multiplied by ``(G+ - G-)``, and summed per
    column (the current-to-voltage conversion is folded into a unit gain here).
    """
    v = dac(voltages, dac_bits, vmax=vin_max)
    gp = np.asarray(g_pos, dtype=np.float64)
    gn = np.asarray(g_neg, dtype=np.float64)
    if v.ndim != 1 or gp.ndim != 2 or gp.shape != gn.shape or gp.shape[1] != v.shape[0]:
        raise ValueError("expected voltages [inputs] and (G+,G-) [outputs, inputs]")
    if np.any(gp < 0) or np.any(gn < 0):
        raise ValueError("physical conductance cannot be negative")
    return (gp @ v) - (gn @ v)
