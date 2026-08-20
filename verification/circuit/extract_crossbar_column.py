"""WP1.1 — extract the first SPICE-backed device profile: crossbar-column-v1.

Deterministic extraction from the 0007 current-mode differential crossbar
column circuit (plus the 0005 rail/headroom non-ideality model). The script
reuses the chapter's own ``crossbar_column.py`` as the single source of truth
for SPICE solves, runs fixed cases/sweeps, and emits:

  * verification/circuit/results/crossbar-column-v1-extract.json
  * device_profiles/crossbar-column-v1.json

Run:  python verification/circuit/extract_crossbar_column.py
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

if "NGSPICE_LIBRARY_PATH" not in os.environ:
    for path in (
        "/opt/homebrew/lib/libngspice.dylib",
        "/usr/local/lib/libngspice.dylib",
        "/usr/lib/x86_64-linux-gnu/libngspice.so",
    ):
        if os.path.exists(path):
            os.environ["NGSPICE_LIBRARY_PATH"] = path
            break

_REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO / "book" / "0007-crossbar-column"))
from crossbar_column import (  # noqa: E402
    G0,
    GSCALE,
    RF,
    VREF,
    conductances,
    ideal_out,
    run_column,
)

RESULTS_DIR = _REPO / "verification" / "circuit" / "results"
PROFILE_PATH = _REPO / "device_profiles" / "crossbar-column-v1.json"

# Deterministic operating points and weight sets spanning sign, zero and
# magnitude extremes inside the rail headroom (|Vout| <= 2.5 V).
CASES = [
    ([3.0, 2.1], [0.50, 0.25]),
    ([3.0, 2.1], [-0.50, 0.25]),
    ([2.0, 2.9], [0.25, 0.50]),
    ([2.5, 2.5], [0.50, 0.25]),
    ([3.5, 1.5], [1.0, -1.0]),
]

VDD = 5.0                    # single-supply rail from 0005/0006 models
HEADROOM_UP = VDD - VREF     # VDD - VREF
HEADROOM_DOWN = VREF         # VREF - 0 V


def _max_dc_error_v() -> float:
    """Worst |SPICE - hand calc| over the deterministic cases."""
    return max(abs(run_column(xs, w) - ideal_out(xs, w)) for xs, w in CASES)


def _gain_v_per_v_per_unit_weight() -> float:
    """Slope of Vout vs (x - VREF) for one unit weight on a single input."""
    xs_a = [2.6, VREF]
    xs_b = [3.0, VREF]
    va = run_column(xs_a, [1.0, 0.0])
    vb = run_column(xs_b, [1.0, 0.0])
    return (vb - va) / (xs_b[0] - xs_a[0])


def _transimpedance_gain_ohm() -> float:
    """Rf measured as dVout / dIsum for one unit-weight cell."""
    xs = [2.6, VREF]
    vout = run_column(xs, [1.0, 0.0])
    delta_i = (xs[0] - VREF) * GSCALE
    return vout / delta_i


def _differential_mapping_error_s() -> float:
    """Worst |(G+ - G-) - w*GSCALE| over the case weights."""
    ws = [w for _, w in CASES]
    worst = 0.0
    for w in ws:
        gp, gm = conductances(w)
        worst = max(worst, max(abs((gp[i] - gm[i]) - w[i] * GSCALE) for i in range(len(w))))
    return float(worst)


def measure() -> dict[str, float]:
    """Re-run the deterministic extraction and return raw measured values."""
    dc_err = _max_dc_error_v()
    assert dc_err <= 2e-2, f"SPICE column must match hand calc, max err {dc_err}"

    return {
        "vref_v": VREF,
        "g0_s": G0,
        "gscale_s_per_w": GSCALE,
        "rf_nominal_ohm": RF,
        "transimpedance_gain_ohm": _transimpedance_gain_ohm(),
        "gain_v_per_v_per_unit_weight": _gain_v_per_v_per_unit_weight(),
        "dc_error_v_max": dc_err,
        "output_headroom_up_v": HEADROOM_UP,
        "output_headroom_down_v": HEADROOM_DOWN,
        "differential_mapping_error_s_max": _differential_mapping_error_s(),
    }


def _field(value, unit, evidence_class, note):
    return {"value": value, "unit": unit, "evidence_class": evidence_class, "note": note}


def build_profile(measured: dict[str, float]) -> dict[str, object]:
    """Assemble the versioned crossbar-column profile from measured values."""
    profile = {
        "schema_version": 1,
        "name": "crossbar-column-v1",
        "version": "0.1.0",
        "evidence_class": "spice",
        "status": "CIRCUIT_SIMULATED",
        "provenance": {
            "tool": "PySpice/ngspice",
            "analysis": "op",
            "sources": [
                "book/0007-crossbar-column/crossbar_column.py (column solves)",
                "book/0005-one-analog-neuron/sim_neuron_nonideal.py (rail model)",
            ],
            "command": "python verification/circuit/extract_crossbar_column.py",
            "conditions": {
                "supply_v": VDD,
                "vref_v": VREF,
                "temperature_c": "nominal (no temperature model)",
                "backend": "ngspice (libngspice)",
            },
            "limitations": (
                "DC operating-point solves only; no transient/settling, noise, "
                "temperature or Monte Carlo evidence yet. Rail limits taken from the "
                "0005 non-ideal model; headroom is derived from VDD and VREF, not "
                "measured on the 0007 column directly."
            ),
        },
        "fields": {
            "vref_v": _field(measured["vref_v"], "V", "derived", "virtual reference from 0005/0007 designs"),
            "g0_s": _field(measured["g0_s"], "S", "derived", "balanced-zero conductance per 0007 netlist"),
            "gscale_s_per_w": _field(measured["gscale_s_per_w"], "S", "derived", "weight->conductance scale per 0007 netlist"),
            "rf_nominal_ohm": _field(measured["rf_nominal_ohm"], "ohm", "derived", "transimpedance feedback resistor from 0007 netlist"),
            "transimpedance_gain_ohm": _field(measured["transimpedance_gain_ohm"], "ohm", "spice", "dVout/dIsum measured over one unit-weight cell"),
            "gain_v_per_v_per_unit_weight": _field(
                measured["gain_v_per_v_per_unit_weight"], "V/V per weight", "spice",
                "slope of Vout vs (x-VREF) for a unit weight",
            ),
            "dc_error_v_max": _field(measured["dc_error_v_max"], "V", "spice", "worst |SPICE - hand calc| over parameterized cases"),
            "output_headroom_up_v": _field(measured["output_headroom_up_v"], "V", "derived", "VDD - VREF, assumes VDD=5 V rail"),
            "output_headroom_down_v": _field(measured["output_headroom_down_v"], "V", "derived", "VREF - 0 V, assumes 0 V rail"),
            "differential_mapping_error_s_max": _field(
                measured["differential_mapping_error_s_max"], "S", "derived",
                "worst |(G+ - G-) - w*GSCALE| over extracted weights",
            ),
        },
    }
    return profile


def main() -> None:
    measured = measure()
    profile = build_profile(measured)

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    result_path = RESULTS_DIR / "crossbar-column-v1-extract.json"
    result_path.write_text(json.dumps(measured, indent=2, sort_keys=True) + "\n", "utf-8")
    PROFILE_PATH.write_text(json.dumps(profile, indent=2, sort_keys=True) + "\n", "utf-8")

    print(f"wrote {result_path}")
    print(f"wrote {PROFILE_PATH}")
    for k, v in measured.items():
        print(f"  {k:36s} = {v:.6g}")


if __name__ == "__main__":
    main()