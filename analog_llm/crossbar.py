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

    The ``gmin``/``gmax`` defaults here (``0.05``/``1.0``) are functional
    reference values mirrored by ``device_profiles/ideal.json``, not device
    evidence. Physical simulations must take the conductance window from a
    validated device profile via ``analog_llm.profile_adapter``.
    """

from __future__ import annotations

from functools import lru_cache
from typing import Any

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


def apply_stuck_faults(
    g: ArrayLike,
    p_hrs: float = 0.0,
    p_lrs: float = 0.0,
    gmin: float = 10.0e-6,
    gmax: float = 100.0e-6,
    rng: np.random.Generator | None = None,
) -> tuple[NDArray[np.float64], dict[str, int]]:
    """Inject spatial stuck-at-HRS and stuck-at-LRS defects into a conductance matrix."""
    if p_hrs < 0.0 or p_lrs < 0.0 or (p_hrs + p_lrs) > 1.0:
        raise ValueError("fault probabilities must be non-negative with p_hrs + p_lrs <= 1.0")
    if gmax <= gmin or gmin <= 0.0:
        raise ValueError("requires 0 < gmin < gmax")

    g_arr = np.asarray(g, dtype=np.float64).copy()
    if p_hrs == 0.0 and p_lrs == 0.0:
        return g_arr, {"total_cells": int(g_arr.size), "stuck_hrs_count": 0, "stuck_lrs_count": 0}

    if rng is None:
        rng = np.random.default_rng()

    rand_draws = rng.random(size=g_arr.shape)
    mask_lrs = rand_draws < p_lrs
    mask_hrs = (rand_draws >= p_lrs) & (rand_draws < (p_lrs + p_hrs))

    g_arr[mask_lrs] = gmax
    g_arr[mask_hrs] = gmin

    counts = {
        "total_cells": int(g_arr.size),
        "stuck_lrs_count": int(np.sum(mask_lrs)),
        "stuck_hrs_count": int(np.sum(mask_hrs)),
    }
    return g_arr, counts


def apply_programming_variation(
    g: ArrayLike,
    sigma_prog: float = 0.0,
    rng: np.random.Generator | None = None,
) -> NDArray[np.float64]:
    """Apply relative Gaussian programming (write) variation to conductances."""
    if sigma_prog < 0.0:
        raise ValueError("sigma_prog must be non-negative")
    g_arr = np.asarray(g, dtype=np.float64).copy()
    if sigma_prog == 0.0:
        return g_arr

    if rng is None:
        rng = np.random.default_rng()

    delta = rng.normal(0.0, sigma_prog, size=g_arr.shape)
    return np.clip(g_arr * (1.0 + delta), 0.0, None)


def apply_conductance_drift(
    g: ArrayLike,
    drift_time_s: float = 0.0,
    nu_min: float = 0.02,
    nu_max: float = 0.06,
    gmin: float = 10.0e-6,
    gmax: float = 100.0e-6,
    t0_s: float = 1.0,
) -> NDArray[np.float64]:
    """Apply structural relaxation temporal drift G(t) = G0 * (t/t0)^(-nu(G0))."""
    if drift_time_s < 0.0 or nu_min < 0.0 or nu_max < 0.0 or t0_s <= 0.0:
        raise ValueError("drift parameters must be non-negative with t0_s > 0")
    if gmax <= gmin or gmin <= 0.0:
        raise ValueError("requires 0 < gmin < gmax")

    g_arr = np.asarray(g, dtype=np.float64).copy()
    if drift_time_s <= t0_s or (nu_min == 0.0 and nu_max == 0.0):
        return g_arr

    span = gmax - gmin
    frac = np.clip((g_arr - gmin) / span, 0.0, 1.0)
    nu = nu_min + frac * (nu_max - nu_min)
    return g_arr * ((drift_time_s / t0_s) ** (-nu))


def apply_read_noise(
    g: ArrayLike,
    sigma_read: float = 0.0,
    rng: np.random.Generator | None = None,
) -> NDArray[np.float64]:
    """Apply temporal read noise fluctuations to conductances."""
    if sigma_read < 0.0:
        raise ValueError("sigma_read must be non-negative")
    g_arr = np.asarray(g, dtype=np.float64).copy()
    if sigma_read == 0.0:
        return g_arr

    if rng is None:
        rng = np.random.default_rng()

    delta = rng.normal(0.0, sigma_read, size=g_arr.shape)
    return np.clip(g_arr * (1.0 + delta), 0.0, None)


def apply_iv_nonlinearity(
    voltages: ArrayLike,
    beta: float = 0.0,
    v_read_max: float = 0.25,
    vin_max: float = 1.0,
) -> NDArray[np.float64]:
    """Apply cubic sub-Ohmic I-V non-linearity v_eff = v * (1 + beta * (v * v_read_max / vin_max)^2)."""
    if beta < 0.0 or v_read_max <= 0.0 or vin_max <= 0.0:
        raise ValueError("beta must be non-negative and voltage ranges must be positive")
    v = np.asarray(voltages, dtype=np.float64)
    if beta == 0.0:
        return v.copy()
    v_phys = v * (v_read_max / vin_max)
    return v * (1.0 + beta * (v_phys**2))


@lru_cache(maxsize=64)
def _get_g_wire_template(N: int, M: int, r_wire: float) -> np.ndarray:
    """Precompute static wire conductance connectivity matrix for an (N, M) crossbar."""
    dim = 2 * N * M
    G_wire = np.zeros((dim, dim), dtype=np.float64)
    g_wire = 1.0 / r_wire

    for i in range(N):
        for j in range(M):
            kr = i * M + j
            kc = N * M + kr
            # Row wire to left / driver
            G_wire[kr, kr] += g_wire
            if j > 0:
                G_wire[kr, kr - 1] -= g_wire
            # Row wire to right
            if j < M - 1:
                G_wire[kr, kr] += g_wire
                G_wire[kr, kr + 1] -= g_wire

            # Column wire from top
            if i > 0:
                G_wire[kc, kc] += g_wire
                G_wire[kc, kc - M] -= g_wire
            # Column wire to bottom / virtual ground
            G_wire[kc, kc] += g_wire
            if i < N - 1:
                G_wire[kc, kc + M] -= g_wire

    return G_wire


def solve_crossbar_nodal(
    v_in: ArrayLike,
    g_matrix: ArrayLike,
    r_wire: float = 0.0,
    vref: float = 0.0,
) -> dict[str, Any]:
    """Solve steady-state crossbar node voltages and column output currents via 2D nodal analysis.

    Parameters
    ----------
    v_in : ndarray of shape (N,) or (N, B)
        Row input driving voltages.
    g_matrix : ndarray of shape (N, M)
        Crosspoint conductances (N inputs x M outputs).
    r_wire : float
        Interconnect wire resistance per segment (Ohm). If r_wire <= 1e-12, returns ideal.
    vref : float
        Virtual ground reference potential (V) at the column outputs.

    Returns
    -------
    dict containing:
        - 'i_out': output column currents exiting at bottom nodes (A), shape (M,) or (M, B)
        - 'i_ideal': ideal column currents without IR drop (A), shape (M,) or (M, B)
        - 'v_row': row node voltages (N, M) (only populated for 1D input)
        - 'v_col': column node voltages (N, M) (only populated for 1D input)
    """
    g_mat = np.asarray(g_matrix, dtype=np.float64)
    if g_mat.ndim != 2:
        raise ValueError("g_matrix must be a 2D array (N, M)")
    N, M = g_mat.shape
    v_arr = np.asarray(v_in, dtype=np.float64)
    is_1d = v_arr.ndim == 1
    if is_1d:
        v_2d = v_arr.reshape(N, 1)
    elif v_arr.ndim == 2:
        if v_arr.shape[0] != N:
            raise ValueError(f"expected {N} input rows, got {v_arr.shape[0]}")
        v_2d = v_arr
    else:
        raise ValueError(f"v_in must be 1D or 2D, got shape {v_arr.shape}")

    u_in = v_2d - vref
    i_ideal = g_mat.T @ u_in

    if r_wire <= 1e-12:
        if is_1d:
            v_row = np.repeat(v_arr[:, None], M, axis=1)
            v_col = np.full((N, M), vref, dtype=np.float64)
            return {
                "i_out": i_ideal.ravel(),
                "i_ideal": i_ideal.ravel(),
                "v_row": v_row,
                "v_col": v_col,
            }
        return {
            "i_out": i_ideal,
            "i_ideal": i_ideal,
            "v_row": None,
            "v_col": None,
        }

    dim = 2 * N * M
    g_wire = 1.0 / r_wire
    G_wire = _get_g_wire_template(N, M, r_wire)
    G_sys = G_wire.copy()

    kr = np.arange(N * M)
    kc = N * M + kr
    g_flat = g_mat.ravel()

    # Vectorized cell conductance stamping
    G_sys[kr, kr] += g_flat
    G_sys[kc, kc] += g_flat
    G_sys[kr, kc] -= g_flat
    G_sys[kc, kr] -= g_flat

    B = v_2d.shape[1]
    if is_1d:
        I_rhs = np.zeros(dim, dtype=np.float64)
        I_rhs[: N * M : M] = v_arr * g_wire
        if vref != 0.0:
            I_rhs[N * M + (N - 1) * M :] = vref * g_wire

        v_nodes = np.linalg.solve(G_sys, I_rhs)
        v_row = v_nodes[: N * M].reshape((N, M))
        v_col = v_nodes[N * M :].reshape((N, M))
        i_out = (v_col[N - 1, :] - vref) * g_wire

        return {
            "i_out": i_out,
            "i_ideal": i_ideal.ravel(),
            "v_row": v_row,
            "v_col": v_col,
        }

    # Batched RHS evaluation
    I_rhs = np.zeros((dim, B), dtype=np.float64)
    I_rhs[: N * M : M, :] = v_2d * g_wire
    if vref != 0.0:
        I_rhs[N * M + (N - 1) * M :, :] = vref * g_wire

    v_nodes = np.linalg.solve(G_sys, I_rhs)
    v_col_bottom = v_nodes[N * M + (N - 1) * M :, :]
    i_out = (v_col_bottom - vref) * g_wire

    return {
        "i_out": i_out,
        "i_ideal": i_ideal,
        "v_row": None,
        "v_col": None,
    }


def mvm(
    voltages: ArrayLike,
    g_pos: ArrayLike,
    g_neg: ArrayLike,
    dac_bits: int,
    vin_max: float = 1.0,
    r_wire_ohm: float = 0.0,
    iv_non_linearity_beta: float = 0.0,
    v_read_max: float = 0.25,
) -> NDArray[np.float64]:
    """Column currents (as effective weighted sums) for a differential crossbar.

    Inputs are quantized by a DAC, optionally distorted by I-V non-linearity
    and distributed wire resistance (IR drop), multiplied by ``(G+ - G-)``,
    and summed per column.
    """
    v = dac(voltages, dac_bits, vmax=vin_max)
    gp = np.asarray(g_pos, dtype=np.float64)
    gn = np.asarray(g_neg, dtype=np.float64)
    if v.ndim != 1 or gp.ndim != 2 or gp.shape != gn.shape or gp.shape[1] != v.shape[0]:
        raise ValueError("expected voltages [inputs] and (G+,G-) [outputs, inputs]")
    if np.any(gp < 0) or np.any(gn < 0):
        raise ValueError("physical conductance cannot be negative")

    if iv_non_linearity_beta > 0.0:
        v_eff = apply_iv_nonlinearity(
            v, iv_non_linearity_beta, v_read_max=v_read_max, vin_max=vin_max
        )
    else:
        v_eff = v

    if r_wire_ohm > 0.0:
        # gp has shape (rows, cols) -> gp.T has shape (cols, rows) = (inputs, outputs)
        ip = solve_crossbar_nodal(v_eff, gp.T, r_wire=r_wire_ohm, vref=0.0)["i_out"]
        in_ = solve_crossbar_nodal(v_eff, gn.T, r_wire=r_wire_ohm, vref=0.0)["i_out"]
        return ip - in_

    return (gp @ v_eff) - (gn @ v_eff)
