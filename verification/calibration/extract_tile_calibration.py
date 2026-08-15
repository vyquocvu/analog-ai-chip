"""Extract a zero-preserving R5 tile calibration profile and evidence report."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np

_REPO = Path(__file__).resolve().parents[2]
_TILE_EXTRACT = _REPO / "verification" / "circuit" / "results" / "physical-tile-0021-extract.json"
_PROFILE_OUT = _REPO / "device_profiles" / "tile-calibration-v1.json"
_RESULT_OUT = (
    _REPO / "verification" / "calibration" / "results" / "tile-calibration-v1-extract.json"
)


def _flatten_evidence(equivalence: dict[str, Any]) -> tuple[np.ndarray, np.ndarray]:
    raw: list[float] = []
    target: list[float] = []
    for array in equivalence["arrays"].values():
        for case in array["cases"]:
            raw.extend(case["tile_output_v"])
            target.extend(case["spice_output_v"])
    raw_array = np.asarray(raw, dtype=np.float64)
    target_array = np.asarray(target, dtype=np.float64)
    if raw_array.size == 0 or raw_array.shape != target_array.shape:
        raise ValueError("tile/SPICE calibration evidence must contain paired outputs")
    if np.any(~np.isfinite(raw_array)) or np.any(~np.isfinite(target_array)):
        raise ValueError("tile/SPICE calibration evidence must be finite")
    return raw_array, target_array


def _gain_feasible_interval(
    raw: np.ndarray, target: np.ndarray, budget_v: float
) -> tuple[float, float]:
    """Return gains satisfying ``|gain*raw_i-target_i| <= budget_v``."""
    lower = 0.0
    upper = float("inf")
    for raw_i, target_i in zip(raw, target):
        if raw_i == 0.0:
            if abs(target_i) > budget_v:
                raise ValueError("zero raw output cannot satisfy the frozen error budget")
            continue
        endpoint_a = (target_i - budget_v) / raw_i
        endpoint_b = (target_i + budget_v) / raw_i
        lower = max(lower, min(endpoint_a, endpoint_b))
        upper = min(upper, max(endpoint_a, endpoint_b))
    if not np.isfinite(lower) or not np.isfinite(upper) or lower > upper:
        raise ValueError("no positive calibration gain satisfies the frozen error budget")
    return float(lower), float(upper)


def derive_calibration(equivalence: dict[str, Any]) -> dict[str, Any]:
    """Fit minimum-RMS gain without degrading the observed maximum error."""
    raw, target = _flatten_evidence(equivalence)
    budget_v = float(equivalence["frozen_budget"]["value"])
    raw_residual = raw - target
    raw_rms = float(np.sqrt(np.mean(np.square(raw_residual))))
    raw_max = float(np.max(np.abs(raw_residual)))
    max_error_constraint_v = min(raw_max, budget_v)
    denominator = float(np.dot(raw, raw))
    if denominator == 0.0:
        raise ValueError("calibration requires at least one non-zero raw output")

    unconstrained_gain = float(np.dot(raw, target) / denominator)
    gain_min, gain_max = _gain_feasible_interval(raw, target, max_error_constraint_v)
    correction_gain = float(np.clip(unconstrained_gain, gain_min, gain_max))
    corrected = correction_gain * raw
    calibrated_residual = corrected - target

    calibrated_rms = float(np.sqrt(np.mean(np.square(calibrated_residual))))
    calibrated_max = float(np.max(np.abs(calibrated_residual)))
    if calibrated_rms >= raw_rms:
        raise AssertionError("calibration must reduce RMS error")
    if calibrated_max > max_error_constraint_v + 1e-12:
        raise AssertionError("calibration must not degrade the observed maximum error")

    return {
        "formula": {
            "least_squares_gain": "a_ls = sum(y_raw*y_spice) / sum(y_raw^2)",
            "max_constraint": "E_constraint = min(E_raw_max,E_budget)",
            "feasible_interval": "[a_min,a_max] = intersection_i {|a*y_raw_i-y_spice_i| <= E_constraint}",
            "correction": "a_star = clip(a_ls,[a_min,a_max]); y_cal = a_star*y_raw",
        },
        "sample_count": int(raw.size),
        "frozen_budget_v": budget_v,
        "max_error_constraint_v": max_error_constraint_v,
        "unconstrained_gain": unconstrained_gain,
        "feasible_gain_min": gain_min,
        "feasible_gain_max": gain_max,
        "correction_gain": correction_gain,
        "correction_offset_v": 0.0,
        "raw_rms_error_v": raw_rms,
        "calibrated_rms_error_v": calibrated_rms,
        "rms_improvement_pct": float((raw_rms - calibrated_rms) / raw_rms * 100.0),
        "raw_max_abs_error_v": raw_max,
        "calibrated_max_abs_error_v": calibrated_max,
        "preserves_balanced_zero": True,
        "passes_frozen_budget": True,
        "raw_outputs_v": raw.tolist(),
        "spice_outputs_v": target.tolist(),
        "calibrated_outputs_v": corrected.tolist(),
    }


def build_artifacts() -> tuple[dict[str, Any], dict[str, Any]]:
    tile_extract = json.loads(_TILE_EXTRACT.read_text("utf-8"))
    equivalence = tile_extract["small_array_spice_equivalence"]
    calibration = derive_calibration(equivalence)

    profile = {
        "schema_version": 1,
        "name": "tile-calibration-v1",
        "version": "0.1.0",
        "evidence_class": "derived",
        "status": "SYSTEM_SIMULATED",
        "fields": {
            "correction_gain": {
                "value": calibration["correction_gain"],
                "unit": "1",
                "evidence_class": "derived",
                "note": "zero-offset least-squares gain clipped to the ADC-derived max-error constraint",
            },
            "correction_offset_v": {
                "value": 0.0,
                "unit": "V",
                "evidence_class": "derived",
                "note": "fixed at zero to preserve balanced differential cancellation",
            },
            "fit_sample_count": {
                "value": calibration["sample_count"],
                "unit": "outputs",
                "evidence_class": "derived",
            },
            "raw_rms_error_v": {
                "value": calibration["raw_rms_error_v"],
                "unit": "V",
                "evidence_class": "derived",
            },
            "calibrated_rms_error_v": {
                "value": calibration["calibrated_rms_error_v"],
                "unit": "V",
                "evidence_class": "derived",
            },
            "rms_improvement_pct": {
                "value": calibration["rms_improvement_pct"],
                "unit": "%",
                "evidence_class": "derived",
            },
            "frozen_max_error_budget_v": {
                "value": calibration["frozen_budget_v"],
                "unit": "V",
                "evidence_class": "derived",
                "source": "device_profiles/adc-sar-v1.json#/fields/quantization_error_v",
            },
        },
        "provenance": {
            "tool": "NumPy deterministic constrained least-squares extraction",
            "analysis": "system-level affine output calibration",
            "sources": [
                "verification/circuit/results/physical-tile-0021-extract.json#/small_array_spice_equivalence",
                "device_profiles/adc-sar-v1.json#/fields/quantization_error_v",
                "verification/calibration/extract_tile_calibration.py",
            ],
            "conditions": {
                "tile_profiles": ["crossbar-v1", "dac-r2r-v1", "adc-sar-v1"],
                "g_bits": 4,
                "dac_bits": 4,
                "adc_bits": 4,
                "fit_arrays": ["2x2", "4x4"],
                "offset_constraint_v": 0.0,
            },
            "limitations": (
                "Coefficients are fitted and evaluated on the same 30 committed SPICE/system outputs; "
                "no held-out arrays, temperature/process corners, drift tracking, or hardware measurements. "
                "This SYSTEM_SIMULATED profile cannot support a physical calibration claim."
            ),
            "command": "python verification/calibration/extract_tile_calibration.py",
        },
    }
    result = {
        "schema_version": 1,
        "name": "tile-calibration-v1-extract",
        "profile": "device_profiles/tile-calibration-v1.json",
        "source": "verification/circuit/results/physical-tile-0021-extract.json",
        "claim_level": "SYSTEM_SIMULATED",
        "calibration": calibration,
        "limitations": profile["provenance"]["limitations"],
    }
    return profile, result


def main() -> None:
    profile, result = build_artifacts()
    _RESULT_OUT.parent.mkdir(parents=True, exist_ok=True)
    _PROFILE_OUT.write_text(json.dumps(profile, indent=2) + "\n", "utf-8")
    _RESULT_OUT.write_text(json.dumps(result, indent=2) + "\n", "utf-8")
    metrics = result["calibration"]
    print(f"Wrote {_PROFILE_OUT.relative_to(_REPO)}")
    print(f"Wrote {_RESULT_OUT.relative_to(_REPO)}")
    print(
        f"RMS: {metrics['raw_rms_error_v']:.6f} V -> "
        f"{metrics['calibrated_rms_error_v']:.6f} V "
        f"({metrics['rms_improvement_pct']:.2f}% improvement)"
    )
    print(
        f"Max: {metrics['raw_max_abs_error_v']:.6f} V -> "
        f"{metrics['calibrated_max_abs_error_v']:.6f} V "
        f"(budget {metrics['frozen_budget_v']:.6f} V)"
    )


if __name__ == "__main__":
    main()
