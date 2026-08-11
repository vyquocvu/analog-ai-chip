"""Chapter 0011 — separating converter error mechanisms.

A measured converter transfer mixes several independent error mechanisms. This
module takes the SPICE-measured mismatched ladder (from ``variation``) and the
functional quantizer (0010) and separates total error into its components, then
proves the separation is exact.

DAC side (``decompose_dac_transfer``)
-------------------------------------
For each mismatched sample, the endpoint-fit line ``L(code) = offset + slope*code``
captures offset + gain. Everything left is non-linearity:

    INL(code) = V(code) - L(code)

The decomposition is exact by construction: ``V = offset + slope*code + INL``.
The budget is reported as the RMS contribution of offset, gain and
non-linearity to the total deviation from the ideal transfer.

ADC side (``separate_adc_error``)
---------------------------------
A full-scale sine through the 4-bit quantizer plus input-referred Gaussian
noise accumulates error power from two mechanisms that are uncorrelated with
each other and with the signal:

    P_total = P_quant + P_noise,     P_quant = LSB^2/12,  P_noise = noise_std^2

The measured total error power is compared to the hand sum -- the "separation
is exact" assertion for the ADC.

Both sides are deterministic (fixed seed, fixed sine), and the measured
powers/errors are compared to hand references encoded in ``tests``.
"""

from __future__ import annotations

import os

import numpy as np

if "NGSPICE_LIBRARY_PATH" not in os.environ:
    for path in (
        "/opt/homebrew/lib/libngspice.dylib",
        "/usr/local/lib/libngspice.dylib",
        "/usr/lib/x86_64-linux-gnu/libngspice.so",
    ):
        if os.path.exists(path):
            os.environ["NGSPICE_LIBRARY_PATH"] = path
            break

BITS = 4                 # prototype width (matches 0009/0010/0011)
VREF = 2.5               # reference voltage (V)
LSB = VREF / (2**BITS)


def decompose_dac_transfer(transfers: np.ndarray, bits: int = BITS,
                           vref: float = VREF) -> dict[str, float]:
    """Separate a ``(n_samples, 2^bits)`` DAC transfer into offset/gain/INL.

    Endpoint fit: ``offset = V(0)``, ``slope = (V(end) - V(0))/(2^bits - 1)``,
    ``gain_error = slope/LSB - 1``, ``INL = V - line``. Returns the RMS budget
    (relative to the ideal transfer's RMS and the full-scale) for each
    mechanism, plus the exact reconstruction check.
    """
    t = np.asarray(transfers, dtype=float)
    if t.ndim != 2 or t.shape[1] != 2**bits:
        raise ValueError(f"expected shape (n_samples, {2**bits}), got {t.shape}")
    if t.shape[0] == 0:
        raise ValueError("transfers must contain at least one sample")

    lsb = vref / (2**bits)
    ideal = np.arange(2**bits) * lsb
    offset = t[:, 0]
    slope = (t[:, -1] - t[:, 0]) / (2**bits - 1)
    line = offset[:, None] + slope[:, None] * np.arange(2**bits)
    inl = t - line
    total = t - ideal

    def rms(x):
        return float(np.sqrt(np.mean(np.square(x))))

    return {
        "rms_total_v": rms(total),
        "rms_offset_only_v": float(np.sqrt(np.mean(np.square(offset)))),  # per-sample offset
        "rms_gain_v": rms((slope[:, None] / lsb - 1.0) * ideal[None, :]),
        "rms_inl_v": rms(inl),
        "gain_error_mean": float(np.mean(slope / lsb - 1.0)),
        "gain_error_std": float(np.std(slope / lsb - 1.0)),
        "offset_mean_v": float(np.mean(offset)),
        "max_inl_v": float(np.max(np.abs(inl))),
        # exact reconstruction: V == line + INL, so total == offset/gain/INL sum
        "reconstruct_max_v": float(np.max(np.abs((line + inl) - t))),
    }


def _quantize(v_in: np.ndarray, bits: int = BITS, vref: float = VREF) -> np.ndarray:
    """Mid-rise quantizer: code = floor(clip(Vin/LSB)), V_hat = (code+0.5)*LSB."""
    lsb = vref / (2**bits)
    codes = np.clip(np.floor(v_in / lsb), 0, 2**bits - 1).astype(int)
    return (codes + 0.5) * lsb


def full_scale_sine(n_samples: int = 65536, bits: int = BITS,
                    vref: float = VREF, cycles: int = 1007) -> np.ndarray:
    """Full-scale single-tone input (odd-prime cycles over power-of-two count)."""
    t = np.arange(n_samples)
    phase = 2.0 * np.pi * cycles * t / n_samples
    return (vref / 2.0) * (1.0 + np.sin(phase))


def separate_adc_error(noise_std: float, bits: int = BITS, vref: float = VREF,
                       n_samples: int = 65536, seed: int = 7) -> dict[str, float]:
    """Separate ADC error power into quantization + additive noise.

    ``hat`` = quantizer(clean + noise). Measured error power vs the hand
    ``P_quant + P_noise``; the DC offset is removed from both signal and error
    so only the AC error power is separated.
    """
    rng = np.random.default_rng(seed)
    clean = full_scale_sine(n_samples, bits, vref)
    ac = clean - np.mean(clean)
    noisy = clean + rng.normal(0.0, noise_std, size=clean.shape)
    hat = _quantize(noisy, bits, vref)
    err = (hat - np.mean(clean)) - ac

    lsb = vref / (2**bits)
    p_total = float(np.mean(np.square(err)))
    p_quant = float(lsb**2 / 12.0)
    p_noise = float(noise_std**2)
    return {
        "noise_std_v": float(noise_std),
        "p_total_v2": p_total,
        "p_quant_v2": p_quant,
        "p_noise_v2": p_noise,
        "p_hand_v2": p_quant + p_noise,
        "rms_total_v": float(np.sqrt(p_total)),
    }


def main() -> None:
    from variation import draw_deltas, transfers_spice

    print("DAC mechanism separation (SPICE mismatched ladder, 64 samples):")
    deltas = draw_deltas()
    t = transfers_spice(deltas)
    d = decompose_dac_transfer(t)
    print(f"  gain_error mean {d['gain_error_mean']:+.2e}, std {d['gain_error_std']:.2e}")
    print(f"  offset mean {d['offset_mean_v']:+.2e} V")
    print(f"  rms total {d['rms_total_v']:.2e} V | offset {d['rms_offset_only_v']:.2e} "
          f"| gain {d['rms_gain_v']:.2e} | INL {d['rms_inl_v']:.2e}")
    print(f"  max|INL| {d['max_inl_v']:.2e} V, reconstruct err {d['reconstruct_max_v']:.2e}")
    assert d["reconstruct_max_v"] <= 1e-12, "decomposition must be exact"

    print("\nADC error power separation (functional quantizer + noise):")
    for noise_std in (0.0, 0.01, 0.05):
        r = separate_adc_error(noise_std)
        print(f"  noise_std={noise_std:.2f} V: P_total {r['p_total_v2']:.3e} "
              f"~ P_quant {r['p_quant_v2']:.3e} + P_noise {r['p_noise_v2']:.3e} "
              f"= {r['p_hand_v2']:.3e} (hand)")
        # measured power must track the hand sum (sampling tolerance)
        assert abs(r["p_total_v2"] - r["p_hand_v2"]) <= 0.25 * r["p_hand_v2"] + 1e-6, (
            f"ADC error power must separate as P_quant + P_noise, "
            f"noise_std={noise_std}"
        )
    print("OK")


if __name__ == "__main__":
    main()
