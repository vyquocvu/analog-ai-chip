"""WP2.1 — extract the first SPICE-backed DAC profile: dac-r2r-v1.

Deterministic extraction from the 0009 R-2R ladder DAC chapter
(``book/0009-dac-r2r/r2r_dac.py`` as the single source of truth for SPICE
solves). Sweeps every code of a small-bit prototype, compares against the hand
reference ``Vout = VREF*code/2^N``, and measures the converter parameters the
signal path needs downstream:

  * LSB (voltage per code),
  * full-scale and offset (output range),
  * linearity: INL and DNL,
  * worst |SPICE - hand calc| DC error,
  * Thevenin output resistance (two-point DC load line),
  * transient settling vs the single-pole hand reference
    (assumed load capacitance, reported as a sensitivity study, not a profile
    field -- assumed evidence fails closed under ``physical_claim``),
  * VREF supply deviation (a pure gain error on the ratio ladder: SPICE
    ``gain_error = dVREF/VREF``; a design condition on an ideal model, so it
    is reported in the extract JSON only, not a profile field).

Emits:
  * verification/circuit/results/dac-r2r-v1-extract.json  (raw sweep + settling)
  * device_profiles/dac-r2r-v1.json                       (versioned profile)

Run:  python verification/circuit/extract_dac_r2r.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO / "book" / "0009-dac-r2r"))
from r2r_dac import (  # noqa: E402
    BITS,
    R_OHM,
    VREF,
    ideal_output,
    output_resistance_ohm,
    settle_time,
    settle_time_hand,
    supply_sensitivity,
    sweep,
)

RESULTS_DIR = _REPO / "verification" / "circuit" / "results"
PROFILE_PATH = _REPO / "device_profiles" / "dac-r2r-v1.json"

# Settling study conditions (load capacitance is assumed -- no device evidence).
CL_FARAD = 1e-12
SETTLE_BAND_V = VREF / (2 ** (BITS + 1))  # 0.5 LSB
SETTLE_STEPS = ((0, 8), (8, 15), (0, 15))


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
        "rth_ohm": output_resistance_ohm(0, BITS, R_OHM, VREF),
        "sweep_v": volts,
    }


def measure_settling() -> list[dict[str, float]]:
    """Transient settling for representative steps (assumed CL), in seconds."""
    rows = []
    for code_from, code_to in SETTLE_STEPS:
        rows.append({
            "code_from": float(code_from),
            "code_to": float(code_to),
            "cl_farad": CL_FARAD,
            "band_v": SETTLE_BAND_V,
            "settle_time_s": settle_time(code_from, code_to, SETTLE_BAND_V, CL_FARAD),
            "hand_tau_s": settle_time_hand(code_from, code_to, SETTLE_BAND_V, CL_FARAD),
        })
    return rows


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
                "DC operating-point solves with ideal switch sources plus a "
                "transient settling study at an ASSUMED load capacitance "
                "(1 pF, reported in the extract JSON only -- it fails closed "
                "under physical_claim because CL has no device evidence yet). "
                "VREF supply deviation is a pure gain error "
                "(gain_error = dVREF/VREF on the ratio-based ladder), reported "
                "in the extract JSON only and not a profile field. No switch "
                "resistance, resistor mismatch, temperature or Monte Carlo "
                "evidence yet."
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
            "rth_ohm": _field(
                measured["rth_ohm"], "ohm", "spice",
                "Thevenin output resistance from a two-point DC load line "
                "(equals 2R for this ladder orientation, code-independent)",
            ),
        },
    }


def main() -> None:
    measured = measure()
    assert measured["max_abs_error_v"] <= 1e-9, "R-2R ladder must match hand calc"
    assert abs(measured["rth_ohm"] - 2 * R_OHM) / (2 * R_OHM) < 1e-6, "Rth must equal 2R"
    settling = measure_settling()
    for row in settling:
        assert abs(row["settle_time_s"] - row["hand_tau_s"]) <= 10e-9, (
            f"transient settle must match single-pole hand for "
            f"{int(row['code_from'])}->{int(row['code_to'])}"
        )
    profile = build_profile(measured)

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    sweep_only = {k: v for k, v in measured.items() if k != "sweep_v"}
    extract = {
        **sweep_only,
        "sweep_v": measured["sweep_v"],
        "settling": settling,
        "supply_sensitivity": supply_sensitivity(),
    }
    result_path = RESULTS_DIR / "dac-r2r-v1-extract.json"
    result_path.write_text(json.dumps(extract, indent=2, sort_keys=True) + "\n", "utf-8")
    PROFILE_PATH.write_text(json.dumps(profile, indent=2, sort_keys=True) + "\n", "utf-8")

    print(f"wrote {result_path}")
    print(f"wrote {PROFILE_PATH}")
    for k in ("bits", "r_ohm", "vref_v", "lsb_v", "full_scale_v", "offset_v",
              "gain_v_per_v", "max_inl_v", "max_dnl_v", "max_abs_error_v", "rth_ohm"):
        print(f"  {k:18s} = {measured[k]:.6g}")
    print("  settling (assumed CL = 1 pF, band = 0.5 LSB):")
    for row in settling:
        print(f"    {int(row['code_from'])}->{int(row['code_to']):2d}: "
              f"spice {row['settle_time_s']*1e9:6.1f} ns, "
              f"hand {row['hand_tau_s']*1e9:6.1f} ns")
    print("  supply sensitivity (pure gain error = dVREF/VREF):")
    for row in supply_sensitivity():
        print(f"    dVREF/VREF = {row['gain_error_hand']:+.0%}  "
              f"gain_err = {row['gain_error']:+.2e}  "
              f"offset = {row['offset_v']:.1e} V  "
              f"max_abs_err = {row['max_abs_error_v']:.2e} V")


if __name__ == "__main__":
    main()