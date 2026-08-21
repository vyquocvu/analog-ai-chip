"""WP3.2 — extract the 4×4 differential crossbar array evidence (0013).

Deterministic extraction from ``book/0013-crossbar-4x4/crossbar_4x4.py`` (the
single source of truth for SPICE solves) plus the profile-driven
``analog_llm`` tile (the architecture simulator's behavioral model). Measures:

  * SPICE MVM vs the hand reference ``Vout = RF*GSCALE*(W @ u)`` and vs the
    behavioral tile (16-bit conductance/converter quantization), with max and
    RMS error over the deterministic case suite,
  * virtual-ground (loading) error and differential headroom,
  * column currents recovered from the SPICE half-stage outputs vs the hand
    ``sum u*G`` sums, plus the largest cell current (feasibility bound),
  * a 2×2 regression: the scaled module reproduces the committed 0012 results,
  * settling at an ASSUMED summing-node capacitance -- recorded with the caveat
    that the ideal VCVS has no bandwidth model, so it is a data point, not a
    settling claim (bounded settling is 0014).

Emits verification/circuit/results/crossbar-4x4-0013-extract.json. No new
device profile is published (crossbar-v1 is the R4 milestone); the tile uses
the validated crossbar-column-v1 profile.

Run:  python verification/circuit/extract_crossbar_4x4.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

_REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO))
sys.path.insert(0, str(_REPO / "book" / "0013-crossbar-4x4"))

from crossbar_4x4 import (
    CASES,
    G0,
    GSCALE,
    HEADROOM_V,
    RF,
    VREF,
    column_currents_hand,
    column_currents_spice,
    half_stage_rc_tau_s,
    ideal_out,
    max_cell_current_a,
    run_array,
    settle_time,
    settle_time_hand,
)

from analog_llm import build_tile_factory

RESULTS_DIR = _REPO / "verification" / "circuit" / "results"
RESULT_PATH = RESULTS_DIR / "crossbar-4x4-0013-extract.json"
EXTRACT_12 = RESULTS_DIR / "crossbar-2x2-0012-extract.json"

# Behavioral tile: validated crossbar-column profile, high-resolution
# programming/converter bits so the tile error is its quantization floor.
TILE_KWARGS = {"g_bits": 16, "dac_bits": 16, "adc_bits": 16}

# Settling study conditions (summing-node capacitance is assumed).
CL_FARAD = 1e-12
SETTLE_BAND_V = 1e-3
SETTLE_DV = 1.0


def _rms(a: np.ndarray, b: np.ndarray) -> float:
    return float(np.sqrt(np.mean((np.asarray(a) - np.asarray(b)) ** 2)))


def measure() -> dict[str, object]:
    """Re-run the deterministic suite and return raw measured values."""
    tile = build_tile_factory(
        "device_profiles/crossbar-column-v1.json", 4, 4, **TILE_KWARGS
    )()

    cases = []
    worst_sh, worst_t, worst_st = 0.0, 0.0, 0.0
    rms_sh, rms_t, rms_st = 0.0, 0.0, 0.0
    max_vg = 0.0
    max_abs_vout = 0.0
    worst_i = 0.0
    max_cell_i = 0.0
    for w, u in CASES:
        xs = [ui + VREF for ui in u]
        vout, vg = run_array(xs, w)
        ideal = ideal_out(xs, w)
        tile.program(w)
        vtile = np.asarray(tile.forward(np.asarray(xs) - VREF), dtype=float)

        e_sh = float(np.max(np.abs(vout - ideal)))
        e_t = float(np.max(np.abs(vtile - ideal)))
        e_st = float(np.max(np.abs(vout - vtile)))
        worst_sh = max(worst_sh, e_sh)
        worst_t = max(worst_t, e_t)
        worst_st = max(worst_st, e_st)
        rms_sh = max(rms_sh, _rms(vout, ideal))
        rms_t = max(rms_t, _rms(vtile, ideal))
        rms_st = max(rms_st, _rms(vout, vtile))
        max_vg = max(max_vg, float(vg.max()))
        max_abs_vout = max(max_abs_vout, float(np.max(np.abs(vout))))

        ic = column_currents_spice(xs, w)
        ih = column_currents_hand(xs, w)
        d = max(float(np.max(np.abs(ic["iplus"] - ih["iplus"]))),
                float(np.max(np.abs(ic["iminus"] - ih["iminus"]))))
        worst_i = max(worst_i, d)
        max_cell_i = max(max_cell_i, max_cell_current_a(np.asarray(u)))

        cases.append({
            "w": [[float(v) for v in row] for row in w],
            "u": [float(v) for v in u],
            "vout_spice": [float(v) for v in vout],
            "vout_hand": [float(v) for v in ideal],
            "vout_tile": [float(v) for v in vtile],
            "max_abs_err_spice_hand_v": e_sh,
            "max_abs_err_tile_hand_v": e_t,
            "max_abs_err_spice_tile_v": e_st,
            "rms_err_spice_hand_v": _rms(vout, ideal),
            "rms_err_tile_hand_v": _rms(vtile, ideal),
            "rms_err_spice_tile_v": _rms(vout, vtile),
            "iplus_spice_a": [float(v) for v in ic["iplus"]],
            "iplus_hand_a": [float(v) for v in ih["iplus"]],
            "iminus_spice_a": [float(v) for v in ic["iminus"]],
            "iminus_hand_a": [float(v) for v in ih["iminus"]],
            "max_current_err_a": d,
            "max_virtual_ground_err_v": float(vg.max()),
        })

    # 2x2 regression: the scaled module reproduces the committed 0012 extract
    ext12 = json.loads(EXTRACT_12.read_text("utf-8"))
    regress_12 = []
    for row in ext12["cases"]:
        vout, _ = run_array(row["xs"], row["w"])
        regress_12.append(float(np.max(np.abs(vout - np.asarray(row["vout_spice"])))))
    regression_2x2_max_err = max(regress_12)

    # settling (assumed CL; recorded data point, not a physical claim)
    gs = np.asarray([G0 + 0.5 * GSCALE, G0 + 0.25 * GSCALE, G0, G0 + 0.5 * GSCALE])
    xs_from = [VREF, VREF, VREF, VREF]
    xs_to = [VREF + SETTLE_DV, VREF, VREF, VREF]
    ts = settle_time(xs_from, xs_to, gs, SETTLE_BAND_V, CL_FARAD)
    tau = half_stage_rc_tau_s(CL_FARAD, gs)
    th = settle_time_hand(SETTLE_DV, SETTLE_BAND_V, tau)
    settling = [{
        "cl_farad": CL_FARAD,
        "band_v": SETTLE_BAND_V,
        "step_v": SETTLE_DV,
        "sum_g_s": float(np.sum(gs)),
        "tau_single_pole_s": tau,
        "settle_time_spice_s": ts,
        "hand_lower_bound_s": th,
        "note": ("ideal VCVS has no bandwidth model; the transient is "
                 "model-dominated, so this is a recorded data point, not a "
                 "settling claim (bounded settling is 0014)"),
    }]

    return {
        "name": "crossbar-4x4-0013",
        "vref_v": VREF,
        "g0_s": G0,
        "gscale_s_per_w": GSCALE,
        "rf_ohm": RF,
        "headroom_v": HEADROOM_V,
        "tile": {"profile": "device_profiles/crossbar-column-v1.json", **TILE_KWARGS},
        "worst_abs_err_spice_hand_v": worst_sh,
        "rms_err_spice_hand_v": rms_sh,
        "worst_abs_err_tile_hand_v": worst_t,
        "rms_err_tile_hand_v": rms_t,
        "worst_abs_err_spice_tile_v": worst_st,
        "rms_err_spice_tile_v": rms_st,
        "max_abs_vout_v": max_abs_vout,
        "max_virtual_ground_err_v": max_vg,
        "worst_current_err_a": worst_i,
        "max_cell_current_a": max_cell_i,
        "regression_2x2_max_abs_err_v": regression_2x2_max_err,
        "settling": settling,
        "cases": cases,
    }


def main() -> None:
    measured = measure()
    assert measured["worst_abs_err_spice_hand_v"] <= 2e-3, "SPICE must match hand MVM"
    assert measured["worst_abs_err_tile_hand_v"] <= 2e-3, "tile must match hand MVM"
    assert measured["max_abs_vout_v"] <= measured["headroom_v"] + 1e-3, "headroom"
    assert measured["max_virtual_ground_err_v"] <= 0.05, "virtual ground bound"
    assert measured["worst_current_err_a"] <= 5e-6, "currents must match hand sums"
    assert measured["regression_2x2_max_abs_err_v"] <= 1e-6, "must reproduce 0012"

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    RESULT_PATH.write_text(json.dumps(measured, indent=2, sort_keys=True) + "\n", "utf-8")

    print(f"wrote {RESULT_PATH}")
    print(f"  |spice-hand|  worst {measured['worst_abs_err_spice_hand_v']:.2e} V, "
          f"rms {measured['rms_err_spice_hand_v']:.2e} V")
    print(f"  |tile-hand|   worst {measured['worst_abs_err_tile_hand_v']:.2e} V, "
          f"rms {measured['rms_err_tile_hand_v']:.2e} V")
    print(f"  |spice-tile|  worst {measured['worst_abs_err_spice_tile_v']:.2e} V, "
          f"rms {measured['rms_err_spice_tile_v']:.2e} V")
    print(f"  max |Vout| {measured['max_abs_vout_v']:.4f} V (headroom "
          f"+/-{measured['headroom_v']} V)  max virtual-ground "
          f"{measured['max_virtual_ground_err_v']:.2e} V")
    print(f"  worst current err {measured['worst_current_err_a']:.2e} A, "
          f"max cell current {measured['max_cell_current_a']:.2e} A")
    print(f"  2x2 regression max |err| {measured['regression_2x2_max_abs_err_v']:.2e} V")
    s = measured["settling"][0]
    print(f"  settling (assumed CL): spice {s['settle_time_spice_s']*1e9:.1f} ns "
          f"(single-pole lower bound {s['hand_lower_bound_s']*1e9:.1f} ns) -- "
          f"recorded data point, not a claim")


if __name__ == "__main__":
    main()
