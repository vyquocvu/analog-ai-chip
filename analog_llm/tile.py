"""A programmable crossbar tile: signed weights on conductance cells."""

from __future__ import annotations

import numpy as np
from numpy.typing import ArrayLike, NDArray

from .converters import adc
from .crossbar import (
    apply_conductance_drift,
    apply_programming_variation,
    apply_read_noise,
    apply_stuck_faults,
    map_differential,
    mvm,
)


class CrossbarTile:
    """A ``rows x cols`` differential conductance tile.

    The tile stores a signed weight block ``W`` (real units) and realizes
    ``y = W @ x`` plus the converter and conductance non-idealities.

    Signal model
    ------------
    Inputs/outputs are real vectors. To keep magnitudes inside converter
    ranges, ``W`` is normalized to ``[-1, 1]`` (``A = ||W||_inf``) and inputs
    to ``[-vin_max, vin_max]``. The normalized result is scaled back by ``A``
    and passed through the output ADC (``adc_bits``, ``vout_max``, noise,
    gain/offset).

    Constructor defaults (``gmin=0.05``, ``gmax=1.0``, ...) are the
    functional reference values mirrored by ``device_profiles/ideal.json``;
    they are NOT device evidence. A run intended to represent a proposed
    physical implementation must configure tiles from a validated device
    profile via ``analog_llm.profile_adapter.tile_config_from_profile``.
    """

    def __init__(
        self,
        rows: int,
        cols: int,
        g_bits: int = 6,
        dac_bits: int = 8,
        adc_bits: int = 8,
        gmin: float = 0.05,
        gmax: float = 1.0,
        vin_max: float = 1.0,
        vout_max: float = 1.0,
        adc_noise_std: float = 0.0,
        adc_gain: float = 1.0,
        adc_offset: float = 0.0,
        sigma_prog_rel: float = 0.0,
        sigma_read_rel: float = 0.0,
        p_stuck_hrs: float = 0.0,
        p_stuck_lrs: float = 0.0,
        drift_exponent_nu_min: float = 0.0,
        drift_exponent_nu_max: float = 0.0,
        drift_time_s: float = 0.0,
        iv_non_linearity_beta: float = 0.0,
        v_read_max: float = 0.25,
        r_wire_ohm: float = 0.0,
        rng: np.random.Generator | int | None = None,
    ) -> None:
        if rows <= 0 or cols <= 0:
            raise ValueError("tile rows/cols must be positive")
        if sigma_prog_rel < 0.0 or sigma_read_rel < 0.0:
            raise ValueError("variation parameters must be non-negative")
        if p_stuck_hrs < 0.0 or p_stuck_lrs < 0.0 or (p_stuck_hrs + p_stuck_lrs) > 1.0:
            raise ValueError("fault probabilities must be non-negative with p_hrs + p_lrs <= 1.0")
        if drift_exponent_nu_min < 0.0 or drift_exponent_nu_max < 0.0 or drift_time_s < 0.0:
            raise ValueError("drift parameters must be non-negative")
        if iv_non_linearity_beta < 0.0:
            raise ValueError("iv_non_linearity_beta must be non-negative")
        if v_read_max <= 0.0 or vin_max <= 0.0:
            raise ValueError("voltage ranges must be positive")
        if r_wire_ohm < 0.0:
            raise ValueError("r_wire_ohm must be non-negative")

        self.rows = int(rows)
        self.cols = int(cols)
        self.g_bits = int(g_bits)
        self.dac_bits = int(dac_bits)
        self.adc_bits = int(adc_bits)
        self.gmin = float(gmin)
        self.gmax = float(gmax)
        self.vin_max = float(vin_max)
        self.vout_max = float(vout_max)
        self.adc_noise_std = float(adc_noise_std)
        self.adc_gain = float(adc_gain)
        self.adc_offset = float(adc_offset)
        self.sigma_prog_rel = float(sigma_prog_rel)
        self.sigma_read_rel = float(sigma_read_rel)
        self.p_stuck_hrs = float(p_stuck_hrs)
        self.p_stuck_lrs = float(p_stuck_lrs)
        self.drift_exponent_nu_min = float(drift_exponent_nu_min)
        self.drift_exponent_nu_max = float(drift_exponent_nu_max)
        self.drift_time_s = float(drift_time_s)
        self.iv_non_linearity_beta = float(iv_non_linearity_beta)
        self.v_read_max = float(v_read_max)
        self.r_wire_ohm = float(r_wire_ohm)

        is_stochastic = (
            self.sigma_prog_rel > 0.0
            or self.sigma_read_rel > 0.0
            or self.p_stuck_hrs > 0.0
            or self.p_stuck_lrs > 0.0
            or self.adc_noise_std > 0.0
        )
        if is_stochastic and rng is None:
            raise ValueError(
                "stochastic tile with active variation, faults, or noise requires "
                "an explicit rng seed or Generator for deterministic evidence"
            )

        # Independent decoupled random streams per stochastic mechanism
        if isinstance(rng, (int, np.integer)):
            ss = np.random.SeedSequence(int(rng))
            children = ss.spawn(4)
            self._rng_faults = np.random.default_rng(children[0])
            self._rng_prog = np.random.default_rng(children[1])
            self._rng_read = np.random.default_rng(children[2])
            self._rng_adc = np.random.default_rng(children[3])
        elif isinstance(rng, np.random.Generator):
            seeds = rng.integers(0, 2**31 - 1, size=4)
            self._rng_faults = np.random.default_rng(int(seeds[0]))
            self._rng_prog = np.random.default_rng(int(seeds[1]))
            self._rng_read = np.random.default_rng(int(seeds[2]))
            self._rng_adc = np.random.default_rng(int(seeds[3]))
        elif rng is None:
            self._rng_faults = None
            self._rng_prog = None
            self._rng_read = None
            self._rng_adc = None
        else:
            raise TypeError("rng must be an int, np.random.Generator, or None")

        self._g_pos: NDArray[np.float64] | None = None
        self._g_neg: NDArray[np.float64] | None = None
        self._scale = 0.0

    def program(self, weights: ArrayLike) -> None:
        """Store a ``(rows, cols)`` signed weight block on the tile."""
        w = np.asarray(weights, dtype=np.float64)
        if w.shape != (self.rows, self.cols):
            raise ValueError(f"expected weights shape {(self.rows, self.cols)}, got {w.shape}")
        if np.any(~np.isfinite(w)):
            raise ValueError("weights must be finite")

        scale = float(np.max(np.abs(w))) if w.size else 0.0
        if scale == 0.0:
            w_norm = w.copy()
        else:
            w_norm = w / scale
        g_pos, g_neg, _ = map_differential(
            w_norm, bits=self.g_bits, gmin=self.gmin, gmax=self.gmax
        )

        if self.p_stuck_hrs > 0.0 or self.p_stuck_lrs > 0.0:
            g_pos, _ = apply_stuck_faults(
                g_pos, self.p_stuck_hrs, self.p_stuck_lrs, self.gmin, self.gmax, rng=self._rng_faults
            )
            g_neg, _ = apply_stuck_faults(
                g_neg, self.p_stuck_hrs, self.p_stuck_lrs, self.gmin, self.gmax, rng=self._rng_faults
            )

        if self.sigma_prog_rel > 0.0:
            g_pos = apply_programming_variation(g_pos, self.sigma_prog_rel, rng=self._rng_prog)
            g_neg = apply_programming_variation(g_neg, self.sigma_prog_rel, rng=self._rng_prog)

        if self.drift_time_s > 1.0 and (
            self.drift_exponent_nu_min > 0.0 or self.drift_exponent_nu_max > 0.0
        ):
            g_pos = apply_conductance_drift(
                g_pos,
                self.drift_time_s,
                self.drift_exponent_nu_min,
                self.drift_exponent_nu_max,
                self.gmin,
                self.gmax,
            )
            g_neg = apply_conductance_drift(
                g_neg,
                self.drift_time_s,
                self.drift_exponent_nu_min,
                self.drift_exponent_nu_max,
                self.gmin,
                self.gmax,
            )

        self._g_pos = g_pos
        self._g_neg = g_neg
        self._scale = scale

    @property
    def programmed(self) -> bool:
        return self._g_pos is not None

    def forward(self, x: ArrayLike) -> NDArray[np.float64]:
        """Return ``W @ x`` with converter/conductance error; input length cols."""
        if not self.programmed:
            raise RuntimeError("tile not programmed; call program() first")
        x = np.asarray(x, dtype=np.float64).reshape(-1)
        if x.shape[0] != self.cols:
            raise ValueError(f"expected {self.cols} inputs, got {x.shape[0]}")

        peak = float(np.max(np.abs(x))) if x.size else 0.0
        if peak == 0.0:
            y = np.zeros(self.rows, dtype=np.float64)
        else:
            x_norm = x / peak * self.vin_max
            gp = self._g_pos
            gn = self._g_neg
            if self.sigma_read_rel > 0.0:
                gp = apply_read_noise(gp, self.sigma_read_rel, rng=self._rng_read)
                gn = apply_read_noise(gn, self.sigma_read_rel, rng=self._rng_read)

            s = mvm(
                x_norm,
                gp,
                gn,
                self.dac_bits,
                self.vin_max,
                r_wire_ohm=self.r_wire_ohm,
                iv_non_linearity_beta=self.iv_non_linearity_beta,
                v_read_max=self.v_read_max,
            )
            # divide by the conductance span to recover normalized signed weights
            s = s / (self.gmax - self.gmin)
            y = s * (self._scale * peak / self.vin_max)

        return adc(
            y,
            self.adc_bits,
            vmax=self.vout_max,
            gain=self.adc_gain,
            offset=self.adc_offset,
            noise_std=self.adc_noise_std,
            rng=self._rng_adc,
        )
