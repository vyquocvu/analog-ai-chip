"""WP2.1 — converter variation extract: R-2R resistor mismatch (Monte Carlo).

Deterministic extraction from the 0011 variation chapter
(``book/0011-converter-variation/variation.py`` as the single source of truth
for SPICE solves). Draws one fixed set of relative mismatch vectors and runs
the full ``2^N``-code transfer through BOTH the mismatched SPICE ladder and the
independent NumPy network solver, then reports the Monte Carlo statistics:

  * offset, gain error (endpoint-fit),
  * max |INL| and max |DNL| across samples,
  * worst |spice - hand| agreement over all (sample, code) pairs.

``sigma = 0`` is checked to reproduce the ideal ladder (fail-closed sanity).

Note: this is a *variation sensitivity study* with an assumed mismatch
distribution (``sigma = 1%``, Gaussian). It is evidence that the model
propagates mismatch deterministically and matches an independent solver, but
it does NOT publish a new device profile -- the mismatch sigma itself has no
measurement backing, so it fails closed under ``physical_claim``.

Emits: verification/circuit/results/converter-variation-0011-extract.json

Run:  python verification/circuit/extract_converter_variation.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

_REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO / "book" / "0011-converter-variation"))
from variation import (
    BITS,
    N_SAMPLES_DEFAULT,
    R_OHM,
    SEED_DEFAULT,
    SIGMA_DEFAULT,
    VREF,
    draw_deltas,
    mismatch_stats,
    resistor_count,
    transfers_hand,
    transfers_spice,
)

RESULT_PATH = _REPO / "verification" / "circuit" / "results" / "converter-variation-0011-extract.json"


def measure() -> dict[str, object]:
    deltas = draw_deltas()
    t_spice = transfers_spice(deltas)
    t_hand = transfers_hand(deltas)
    stats = mismatch_stats(t_spice)
    hand_stats = mismatch_stats(t_hand)
    max_dev = float(np.max(np.abs(t_spice - t_hand)))

    # fail-closed: sigma = 0 must reproduce the ideal ladder
    nominal = transfers_spice(np.zeros((1, resistor_count(BITS))))
    ideal = [code * VREF / (2**BITS) for code in range(2**BITS)]
    assert float(np.max(np.abs(nominal[0] - ideal))) <= 1e-9, "sigma=0 must be ideal"

    for key in stats:
        assert abs(stats[key] - hand_stats[key]) <= max(1e-6 * abs(hand_stats[key]), 1e-12), key
    assert max_dev <= 1e-9, "SPICE mismatched ladder must match the NumPy network solver"

    return {
        "bits": BITS,
        "r_ohm": R_OHM,
        "vref_v": VREF,
        "sigma": SIGMA_DEFAULT,
        "seed": SEED_DEFAULT,
        "n_samples": N_SAMPLES_DEFAULT,
        "resistors_per_sample": resistor_count(BITS),
        "max_abs_deviation_v": max_dev,
        "offset_mean_v": stats["offset_mean_v"],
        "offset_std_v": stats["offset_std_v"],
        "gain_error_mean": stats["gain_error_mean"],
        "gain_error_std": stats["gain_error_std"],
        "max_inl_mean_v": stats["max_inl_mean_v"],
        "max_inl_std_v": stats["max_inl_std_v"],
        "max_dnl_mean_v": stats["max_dnl_mean_v"],
        "max_dnl_std_v": stats["max_dnl_std_v"],
        "transfers_spice": t_spice.tolist(),
        "transfers_hand": t_hand.tolist(),
    }


def main() -> None:
    extract = measure()
    RESULT_PATH.parent.mkdir(parents=True, exist_ok=True)
    RESULT_PATH.write_text(json.dumps(extract, indent=2, sort_keys=True) + "\n", "utf-8")
    print(f"wrote {RESULT_PATH}")
    for key in ("bits", "r_ohm", "vref_v", "sigma", "seed", "n_samples"):
        print(f"  {key:22s} = {extract[key]}")
    n_pairs = len(extract["transfers_spice"]) * len(extract["transfers_spice"][0])
    print(f"  max |spice - hand| over {n_pairs} (sample, code) pairs = "
          f"{extract['max_abs_deviation_v']:.2e} V")
    print(f"  gain error   mean {extract['gain_error_mean']:+.2e}, "
          f"std {extract['gain_error_std']:.2e}")
    print(f"  max|INL|     mean {extract['max_inl_mean_v']:.2e} V, "
          f"std {extract['max_inl_std_v']:.2e} V")
    print(f"  max|DNL|     mean {extract['max_dnl_mean_v']:.2e} V, "
          f"std {extract['max_dnl_std_v']:.2e} V")


if __name__ == "__main__":
    main()
