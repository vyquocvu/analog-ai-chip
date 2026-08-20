"""WP2.1 — extract the second SPICE-backed converter profile: adc-sar-v1.

Deterministic extraction from the 0010 SAR ADC chapter
(``book/0010-adc-sar/sar_adc.py`` as the single source of truth for SPICE
solves). Re-runs the transfer sweep against the hand reference
``code = floor(Vin/LSB)`` and measures the converter parameters the signal
path needs downstream:

  * bits, reference voltage, unit resistor (design choices),
  * LSB and the differential input envelope,
  * worst |code_spice - code_hand| over the transfer sweep,
  * worst |Vdiff - Vdiff_hat| over the transfer sweep (quantization bound).

Sensitivity/functional studies that carry no physical evidence (assumed
reference-node capacitance, additive-noise ENOB, VREF supply deviation) are
reported in the extract JSON only -- they are not profile fields, because
``assumed``/functional evidence fails closed under ``physical_claim``.

Emits:
  * verification/circuit/results/adc-sar-v1-extract.json  (raw transfer + studies)
  * device_profiles/adc-sar-v1.json                       (versioned profile)

Run:  python verification/circuit/extract_adc_sar.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO / "book" / "0010-adc-sar"))
from sar_adc import (  # noqa: E402
    BITS,
    LSB,
    R_OHM,
    VREF,
    enob_study,
    reference_settle_time,
    reference_settle_time_hand,
    supply_sensitivity,
    transfer_sweep,
    vdiff_from_code,
)

RESULTS_DIR = _REPO / "verification" / "circuit" / "results"
PROFILE_PATH = _REPO / "device_profiles" / "adc-sar-v1.json"

# Settling study conditions (reference-node capacitance is assumed).
CL_FARAD = 1e-12
SETTLE_BAND_V = 0.5 * LSB
SETTLE_STEPS = ((0, 8), (0, 4), (0, 2), (0, 1))


def measure() -> dict[str, float]:
    """Re-run the deterministic SPICE transfer and return measured values."""
    rows = transfer_sweep()  # v_in from 0 .. VREF
    max_code_error = max(
        abs(r["code_spice"] - r["code_hand"]) for r in rows
    )
    errs = [
        abs(2.0 * (r["v_in_v"] - VREF / 2.0) - vdiff_from_code(int(r["code_spice"])))
        for r in rows
    ]
    return {
        "bits": float(BITS),
        "r_ohm": float(R_OHM),
        "vref_v": float(VREF),
        "lsb_v": float(LSB),
        "input_range_v": float(VREF),  # differential envelope is +/- VREF
        "quantization_error_v": float(LSB),  # differential-domain bound
        "max_code_error_codes": float(max_code_error),
        "max_abs_error_v": max(errs),
        "transfer": rows,
    }


def measure_settling() -> list[dict[str, float]]:
    """Reference settle time for representative bit trials (assumed CL)."""
    rows = []
    for code_from, code_to in SETTLE_STEPS:
        rows.append({
            "code_from": float(code_from),
            "code_to": float(code_to),
            "cl_farad": CL_FARAD,
            "band_v": SETTLE_BAND_V,
            "settle_time_s": reference_settle_time(
                code_from, code_to, SETTLE_BAND_V, CL_FARAD
            ),
            "hand_tau_s": reference_settle_time_hand(
                code_to * LSB, SETTLE_BAND_V, CL_FARAD
            ),
        })
    return rows


def _field(value, unit, evidence_class, note):
    return {"value": value, "unit": unit, "evidence_class": evidence_class, "note": note}


def build_profile(measured: dict[str, float]) -> dict[str, object]:
    """Assemble the versioned adc-sar profile from measured values."""
    return {
        "schema_version": 1,
        "name": "adc-sar-v1",
        "version": "0.1.0",
        "evidence_class": "spice",
        "status": "CIRCUIT_SIMULATED",
        "provenance": {
            "tool": "PySpice/ngspice",
            "analysis": "op",
            "sources": ["book/0010-adc-sar/sar_adc.py (R-2R reference + comparator solves)"],
            "command": "python verification/circuit/extract_adc_sar.py",
            "conditions": {
                "bits": BITS,
                "supply_v": VREF,
                "vref_v": VREF,
                "r_ohm": R_OHM,
                "backend": "ngspice (libngspice)",
            },
            "limitations": (
                "DC operating-point solves with an ideal VCVS comparator and "
                "ideal switches. The differential input front (1/2 gain, VREF/2 "
                "level shift) is assumed, not SPICE. Reference-node settling at "
                "an ASSUMED load capacitance (1 pF), additive-noise ENOB and "
                "VREF supply deviation are sensitivity/functional studies "
                "reported in the extract JSON only -- they are not profile "
                "fields because they fail closed under physical_claim. No "
                "comparator noise, reference noise, switch resistance, resistor "
                "mismatch, temperature or Monte Carlo evidence yet."
            ),
        },
        "fields": {
            "bits": _field(measured["bits"], "bits", "derived", "ADC width (design choice)"),
            "r_ohm": _field(measured["r_ohm"], "ohm", "derived", "unit resistor (design choice)"),
            "vref_v": _field(measured["vref_v"], "V", "derived", "reference voltage (design choice)"),
            "lsb_v": _field(
                measured["lsb_v"], "V/code", "derived",
                "VREF/2^N, voltage per code of the reference ladder",
            ),
            "input_range_v": _field(
                measured["input_range_v"], "V", "derived",
                "signed differential input envelope +/-VREF, sourced from the "
                "crossbar-column-v1 output headroom",
            ),
            "quantization_error_v": _field(
                measured["quantization_error_v"], "V", "derived",
                "differential-domain quantization bound = LSB (input front "
                "gain 1/2 doubles the unipolar LSB/2 bound)",
            ),
            "max_code_error_codes": _field(
                measured["max_code_error_codes"], "codes", "spice",
                "worst |code_spice - code_hand| over the 129-sample transfer sweep",
            ),
            "max_abs_error_v": _field(
                measured["max_abs_error_v"], "V", "spice",
                "worst |Vdiff - Vdiff_hat| over the transfer sweep "
                "(equals the quantization bound)",
            ),
        },
    }


def main() -> None:
    measured = measure()
    assert measured["max_code_error_codes"] <= 0, "SPICE SAR must match hand code-for-code"
    assert measured["max_abs_error_v"] <= measured["lsb_v"] + 1e-9, (
        "differential-domain error must respect the quantization bound"
    )
    settling = measure_settling()
    for row in settling:
        assert abs(row["settle_time_s"] - row["hand_tau_s"]) <= 10e-9, (
            f"reference settle must match single-pole hand for "
            f"{int(row['code_from'])}->{int(row['code_to'])}"
        )
    profile = build_profile(measured)

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    scalar = {k: v for k, v in measured.items() if k != "transfer"}
    extract = {
        **scalar,
        "transfer": measured["transfer"],
        "settling": settling,
        "enob": enob_study(),
        "supply_sensitivity": supply_sensitivity(),
    }
    result_path = RESULTS_DIR / "adc-sar-v1-extract.json"
    result_path.write_text(json.dumps(extract, indent=2, sort_keys=True) + "\n", "utf-8")
    PROFILE_PATH.write_text(json.dumps(profile, indent=2, sort_keys=True) + "\n", "utf-8")

    print(f"wrote {result_path}")
    print(f"wrote {PROFILE_PATH}")
    for k in ("bits", "r_ohm", "vref_v", "lsb_v", "input_range_v",
              "quantization_error_v", "max_code_error_codes", "max_abs_error_v"):
        print(f"  {k:22s} = {measured[k]:.6g}")
    print("  settling (assumed CL = 1 pF, band = 0.5 LSB):")
    for row in settling:
        print(f"    {int(row['code_from'])}->{int(row['code_to'])}: "
              f"spice {row['settle_time_s']*1e9:6.1f} ns, "
              f"hand {row['hand_tau_s']*1e9:6.1f} ns")
    print("  enob (functional additive-noise study):")
    for row in enob_study():
        print(f"    noise_std = {row['noise_std_v']:.3f} V -> "
              f"{row['enob_bits']:.2f} bits (hand {row['enob_hand_bits']:.2f})")


if __name__ == "__main__":
    main()
