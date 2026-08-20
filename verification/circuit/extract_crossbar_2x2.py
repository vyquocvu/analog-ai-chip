"""WP3.1 — extract the 2×2 differential crossbar array evidence (0012).

Deterministic extraction from ``book/0012-crossbar-2x2/crossbar_2x2.py`` (the
single source of truth for SPICE solves). Runs the fixed case set -- signed
weights, zero/balanced cells, one zero per row, boundary envelope -- and
measures:

  * per-case SPICE MVM ``Vout = RF*GSCALE * W @ (x - VREF)`` vs the hand
    reference and the worst error over all cases,
  * output-stage headroom: every differential output stays inside +/-2.5 V,
  * virtual-ground (loading) error per half-stage,
  * column independence: changing only column 1's weights leaves Vout_0
    unchanged (shared input rows, uncoupled TIA networks),
  * the half-stage rail finding: a full-scale weight at the input envelope
    edge pushes the G+ half-stage below the single 0 V rail, bounding the
    usable per-input envelope to |u| <= VREF/(RF*(G0+GSCALE)) = 1.25 V.

Emits verification/circuit/results/crossbar-2x2-0012-extract.json. This is
array-level MVM evidence for the behavioral mapping; it publishes no new
device profile (crossbar-v1 is the R4 milestone).

Run:  python verification/circuit/extract_crossbar_2x2.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

_REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO / "book" / "0012-crossbar-2x2"))
from crossbar_2x2 import (  # noqa: E402
    CASES,
    G0,
    GSCALE,
    HEADROOM_V,
    RF,
    VREF,
    half_stage_outputs,
    half_stage_rail_envelope_v,
    ideal_out,
    independence_error,
    run_array,
)

RESULTS_DIR = _REPO / "verification" / "circuit" / "results"
RESULT_PATH = RESULTS_DIR / "crossbar-2x2-0012-extract.json"

# Column-independence probe: same column 0, different column 1.
_IND_XS = [3.0, 2.1]
_IND_A = [[0.50, 0.25], [0.25, 0.50]]
_IND_B = [[0.50, 0.25], [-1.0, 0.0]]


def measure() -> dict[str, object]:
    """Re-run the deterministic cases and return raw measured values."""
    cases = []
    worst_err = 0.0
    max_abs_vout = 0.0
    max_vg = 0.0
    half_stage_violations = 0
    for xs, w in CASES:
        vout, vg = run_array(xs, w)
        ideal = ideal_out(xs, w)
        err = float(np.max(np.abs(vout - ideal)))
        worst_err = max(worst_err, err)
        max_abs_vout = max(max_abs_vout, float(np.max(np.abs(vout))))
        max_vg = max(max_vg, float(vg.max()))
        halves = half_stage_outputs(xs, w)
        half_stage_violations += sum(1 for h in halves if not (0.0 <= h <= 5.0))
        cases.append({
            "xs": [float(v) for v in xs],
            "w": [[float(v) for v in row] for row in w],
            "vout_spice": [float(v) for v in vout],
            "vout_hand": [float(v) for v in ideal],
            "half_stage_outputs_v": [float(h) for h in halves],
            "max_abs_err_v": err,
            "max_virtual_ground_err_v": float(vg.max()),
        })

    ind = independence_error(_IND_XS, _IND_A, _IND_B)
    return {
        "name": "crossbar-2x2-0012",
        "vref_v": VREF,
        "g0_s": G0,
        "gscale_s_per_w": GSCALE,
        "rf_ohm": RF,
        "headroom_v": HEADROOM_V,
        "half_stage_rail_envelope_v": half_stage_rail_envelope_v(),
        "worst_abs_err_v": worst_err,
        "max_abs_vout_v": max_abs_vout,
        "max_virtual_ground_err_v": max_vg,
        "column_independence_err_v": ind,
        "half_stage_rail_violations": half_stage_violations,
        "cases": cases,
    }


def main() -> None:
    measured = measure()
    assert measured["worst_abs_err_v"] <= 2e-3, "SPICE array must match hand MVM"
    assert measured["max_abs_vout_v"] <= measured["headroom_v"] + 1e-3, (
        "differential outputs must stay inside the +-2.5 V headroom"
    )
    assert measured["max_virtual_ground_err_v"] <= 0.05, "virtual ground loading bound"
    assert measured["column_independence_err_v"] <= 2e-3, "columns must be independent"
    assert measured["half_stage_rail_violations"] == 1, (
        "expected exactly the boundary-case G+ half-stage below the 0 V rail"
    )

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    RESULT_PATH.write_text(json.dumps(measured, indent=2, sort_keys=True) + "\n", "utf-8")

    print(f"wrote {RESULT_PATH}")
    print(f"  worst |SPICE - hand|  = {measured['worst_abs_err_v']:.2e} V "
          f"({len(measured['cases'])} cases x 2 outputs)")
    print(f"  max |Vout|           = {measured['max_abs_vout_v']:.4f} V "
          f"(headroom +/-{measured['headroom_v']} V)")
    print(f"  max virtual-ground   = {measured['max_virtual_ground_err_v']:.2e} V")
    print(f"  column independence  = {measured['column_independence_err_v']:.2e} V")
    print(f"  half-stage violations= {measured['half_stage_rail_violations']} "
          f"(rail envelope |u| <= {measured['half_stage_rail_envelope_v']:.2f} V)")


if __name__ == "__main__":
    main()
