"""WP2.1 — extract the first SPICE-backed DAC profile: dac-r2r-v1.

Deterministic extraction from the 0009 R-2R ladder DAC chapter
(``book/0009-dac-r2r/r2r_dac.py`` as the single source of truth for SPICE
solves). Sweeps every code of a small-bit prototype, compares against the hand
reference ``Vout = VREF*code/2^N``, and measures the converter parameters the
signal path needs downstream:

  * LSB (voltage per code),
  * full-scale and offset (output range),
  * linearity: INL and DNL,
  * worst |SPICE - hand calc| DC error.

Emits:
  * verification/circuit/results/dac-r2r-v1-extract.json  (raw sweep)
  * device_profiles/dac-r2r-v1.json                       (versioned profile)

Run:  python verification/circuit/extract_dac_r2r.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO / "book" / "0009-dac-r2r"))
from r2r_dac import BITS, R_OHM, VREF, ideal_output, sweep

RESULTS_DIR = _REPO / "verification" / "circuit" / "results"
PROFILE_PATH = _REPO / "device_profiles" / "dac-r2r-v1.json"


def measure() -> dict[str, float]:
    """Re-run the deterministic sweep and return raw measured values."""
    volts = sweep()  # code order, 0 .. 2^BITS - 1
    n = len(volts)
    lsb = (volts[-1] - volts[0]) / (n - 1)  # average step per code
    inl_max = max(abs(v - ideal_output(code)) for code, v in enumerate(volts))
    dnl_max = max(abs(volts[i + 1] - volts[i] - lsb) for i in range(n - 1))
    return {
        "bits": float(BITS),
        "r_ohm": float(R_OHM),
        "vref_v": float(VREF),
        "lsb_v": lsb,
        "full_scale_v": volts[-1],
        "offset_v": volts[0],
        "gain_v_per_v": lsb / (VREF / (2**BITS)),
        "max_inl_v": inl_max,
        "max_dnl_v": dnl_max,
        "max_abs_error_v": inl_max,
        "sweep_v": volts,
    }


def _field(value, unit, evidence_class, note):
    return {"value": value, "unit": unit, "evidence_class": evidence_class, "note": note}


def build_profile(measured: dict[str, float]) -> dict[str, object]:
    """Assemble the versioned dac-r2r profile from measured values."""
    return {
        "schema_version": 1,
        "name": "dac-r2r-v1",
        "version": "0.1.0",
        "evidence_class": "spice",
        "status": "CIRCUIT_SIMULATED",
        "provenance": {
            "tool": "PySpice/ngspice",
            "analysis": "op",
            "sources": ["book/0009-dac-r2r/r2r_dac.py (R-2R ladder solves)"],
            "command": "python verification/circuit/extract_dac_r2r.py",
            "conditions": {
                "bits": BITS,
                "supply_v": VREF,
                "vref_v": VREF,
                "r_ohm": R_OHM,
                "backend": "ngspice (libngspice)",
            },
            "limitations": (
                "DC operating-point solves with ideal switch sources only; "
                "no transient settling, switch resistance, resistor mismatch, "
                "temperature, supply sensitivity or Monte Carlo evidence yet."
            ),
        },
        "fields": {
            "bits": _field(measured["bits"], "bits", "derived", "ladder width (design choice)"),
            "r_ohm": _field(measured["r_ohm"], "ohm", "derived", "unit resistor (design choice)"),
            "vref_v": _field(measured["vref_v"], "V", "derived", "reference voltage (design choice)"),
            "lsb_v": _field(
                measured["lsb_v"], "V/code", "spice",
                "average output step per code over the full sweep",
            ),
            "full_scale_v": _field(
                measured["full_scale_v"], "V", "spice", "output voltage at maximum code",
            ),
            "offset_v": _field(measured["offset_v"], "V", "spice", "output voltage at code 0"),
            "gain_v_per_v": _field(
                measured["gain_v_per_v"], "V/V per LSB", "spice",
                "measured step normalized to the ideal VREF/2^N step",
            ),
            "max_inl_v": _field(
                measured["max_inl_v"], "V", "spice",
                "worst |Vout - VREF*code/2^N| integral non-linearity",
            ),
            "max_dnl_v": _field(
                measured["max_dnl_v"], "V", "spice",
                "worst |step - LSB| differential non-linearity",
            ),
            "max_abs_error_v": _field(
                measured["max_abs_error_v"], "V", "spice",
                "worst |SPICE - hand calc| over all codes",
            ),
        },
    }


def main() -> None:
    measured = measure()
    assert measured["max_abs_error_v"] <= 1e-9, "R-2R ladder must match hand calc"
    profile = build_profile(measured)

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    sweep_only = {k: v for k, v in measured.items() if k != "sweep_v"}
    extract = {**sweep_only, "sweep_v": measured["sweep_v"]}
    result_path = RESULTS_DIR / "dac-r2r-v1-extract.json"
    result_path.write_text(json.dumps(extract, indent=2, sort_keys=True) + "\n", "utf-8")
    PROFILE_PATH.write_text(json.dumps(profile, indent=2, sort_keys=True) + "\n", "utf-8")

    print(f"wrote {result_path}")
    print(f"wrote {PROFILE_PATH}")
    for k in ("bits", "r_ohm", "vref_v", "lsb_v", "full_scale_v", "offset_v",
              "gain_v_per_v", "max_inl_v", "max_dnl_v", "max_abs_error_v"):
        print(f"  {k:18s} = {measured[k]:.6g}")


if __name__ == "__main__":
    main()