"""Chapter 0011 — calibration candidates for the R-2R converter.

Mismatch is static per chip: gain error, offset and INL are fixed once the
chip is built. That makes them correctable. This module defines the candidate
calibration schemes and measures how much error each removes from the
SPICE-measured mismatched transfers of ``variation``.

Candidates
----------
1. **Two-point (gain + offset) calibration** -- measure the two endpoints
   (code 0 and full scale) and correct every code with the fitted line:

       V_corr = (V - offset) * (LSB / slope)

   Removes offset and gain error entirely; the residual is exactly the
   non-linearity ``INL * LSB/slope``.

2. **Full transfer lookup table (INL calibration)** -- measure the whole
   transfer once and store the per-code deviation from the *ideal* transfer;
   subtract it at run time:

       V_corr = V - (V - V_ideal) = V_ideal

   For static mismatch this drives the error to zero on the calibrated chip.
   (A LUT of the endpoint-relative INL alone only removes non-linearity and
   must be stacked on a two-point gain/offset correction.)

3. **Reference trim (VREF gain correction)** -- the 0010 supply-sensitivity
   study showed ``gain_error = dVREF/VREF`` is a pure gain; trimming ``VREF``
   (or its supply) is an alternative to the digital two-point gain factor.

Candidates 1 and 2 are exercised on the deterministic SPICE mismatch draws and
the residual error is compared to the separated INL component (chapter's
decomposition module). Candidate 3 is a design note backed by the 0010 study,
not re-measured here.
"""

from __future__ import annotations

import numpy as np


def two_point_calibrate(transfers: np.ndarray, bits: int = 4,
                        vref: float = 2.5) -> np.ndarray:
    """Correct offset + gain per sample from the two endpoint codes.

    Returns ``(n_samples, 2^bits)`` calibrated transfers. Raises ``ValueError``
    when a sample has zero slope (degenerate all-zero transfer).
    """
    t = np.asarray(transfers, dtype=float)
    if t.ndim != 2 or t.shape[1] != 2**bits:
        raise ValueError(f"expected shape (n_samples, {2**bits}), got {t.shape}")
    if t.shape[0] == 0:
        raise ValueError("transfers must contain at least one sample")

    lsb = vref / (2**bits)
    offset = t[:, 0]
    slope = (t[:, -1] - t[:, 0]) / (2**bits - 1)
    if np.any(slope <= 0.0):
        raise ValueError("calibration requires positive end-to-end slope")
    codes = np.arange(2**bits)
    line = offset[:, None] + slope[:, None] * codes
    return ((t - line) * (lsb / slope[:, None])) + codes[None, :] * lsb


def lookup_table_calibrate(transfers: np.ndarray, bits: int = 4,
                           vref: float = 2.5) -> np.ndarray:
    """Correct every code from a per-code LUT of the deviation from ideal.

    ``lut(code) = V(code) - V_ideal(code)``; corrected ``V = V - lut``.
    For a static (unchanging) mismatch this reproduces the ideal ladder
    exactly, removing offset, gain and non-linearity in one correction.
    """
    t = np.asarray(transfers, dtype=float)
    if t.ndim != 2 or t.shape[1] != 2**bits:
        raise ValueError(f"expected shape (n_samples, {2**bits}), got {t.shape}")
    if t.shape[0] == 0:
        raise ValueError("transfers must contain at least one sample")

    ideal = np.arange(2**bits) * (vref / (2**bits))
    lut = t - ideal[None, :]
    return t - lut


def residual_error(calibrated: np.ndarray, bits: int = 4,
                   vref: float = 2.5) -> float:
    """Worst |calibrated - ideal| over all samples and codes."""
    t = np.asarray(calibrated, dtype=float)
    ideal = np.arange(2**bits) * (vref / (2**bits))
    return float(np.max(np.abs(t - ideal[None, :])))


def main() -> None:
    from decomposition import decompose_dac_transfer
    from variation import draw_deltas, transfers_spice

    t = transfers_spice(draw_deltas())
    total_err = residual_error(t)
    two_pt = two_point_calibrate(t)
    lut = lookup_table_calibrate(t)
    dec = decompose_dac_transfer(t)

    print("Calibration candidates on 64-sample SPICE mismatch study:")
    print(f"  raw          residual {total_err:.2e} V")
    print(f"  two-point    residual {residual_error(two_pt):.2e} V  "
          f"(= max|INL| {dec['max_inl_v']:.2e} V, scaled)")
    print(f"  lookup table residual {residual_error(lut):.2e} V")
    assert residual_error(two_pt) <= 1.01 * dec["max_inl_v"] / (1 - dec["gain_error_mean"])
    assert residual_error(lut) <= 1e-12, "LUT calibration must zero static mismatch"
    print("OK")


if __name__ == "__main__":
    main()
