"""A programmable crossbar tile: signed weights on conductance cells."""

from __future__ import annotations

import numpy as np
from numpy.typing import ArrayLike, NDArray

from .converters import adc
from .crossbar import map_differential, mvm


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
        rng: np.random.Generator | None = None,
    ) -> None:
        if rows <= 0 or cols <= 0:
            raise ValueError("tile rows/cols must be positive")
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
        self.rng = rng

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
            s = mvm(x_norm, self._g_pos, self._g_neg, self.dac_bits, self.vin_max)
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
            rng=self.rng,
        )
