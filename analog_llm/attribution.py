"""Per-mechanism error attribution for analog in-memory crossbar compute.

Decomposes end-to-end MVM error into individual circuit, device, and converter
mechanisms:
1. Input DAC quantization (dac_bits)
2. Weight conductance quantization (g_bits)
3. Programming (write) variation (sigma_prog_rel)
4. Read (temporal) noise (sigma_read_rel)
5. Stuck-at faults (p_stuck_hrs, p_stuck_lrs)
6. Temporal conductance drift (drift_exponent_nu_min/max, drift_time_s)
7. Sub-Ohmic I-V non-linearity (iv_non_linearity_beta)
8. Interconnect IR drop (r_wire_ohm)
9. Output ADC quantization, clipping and noise (adc_bits, adc_noise_std)
10. Combined all non-idealities

Provides both:
- **Standalone attribution**: each mechanism active in isolation against the ideal reference.
- **Leave-one-out (LOO) attribution**: error recovered by idealizing one mechanism while
  keeping all other non-idealities active.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import numpy as np
from numpy.typing import ArrayLike, NDArray

from .device_profile import load_device_profile
from .tile import CrossbarTile


@dataclass(frozen=True)
class MechanismMetrics:
    """Error metrics for a specific mechanism or combination."""

    name: str
    l2_rel_error_pct: float
    max_abs_error: float
    rms_error: float
    cosine_similarity: float
    snr_db: float

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ErrorAttributionResult:
    """Complete per-mechanism attribution result for an MVM evaluation."""

    ideal_output: list[float]
    combined_output: list[float]
    standalone: dict[str, MechanismMetrics]
    leave_one_out_residuals: dict[str, float]
    leave_one_out_contributions: dict[str, float]
    leave_one_out_shares_pct: dict[str, float]
    standalone_shares_pct: dict[str, float]
    summary: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "ideal_output": self.ideal_output,
            "combined_output": self.combined_output,
            "standalone": {k: v.to_dict() for k, v in self.standalone.items()},
            "leave_one_out_residuals": self.leave_one_out_residuals,
            "leave_one_out_contributions": self.leave_one_out_contributions,
            "leave_one_out_shares_pct": self.leave_one_out_shares_pct,
            "standalone_shares_pct": self.standalone_shares_pct,
            "summary": self.summary,
        }


def _compute_metrics(y_pred: NDArray[np.float64], y_ideal: NDArray[np.float64], name: str) -> MechanismMetrics:
    """Compute standard scalar error metrics comparing predicted vs ideal output."""
    diff = y_pred - y_ideal
    norm_ideal = float(np.linalg.norm(y_ideal))
    norm_diff = float(np.linalg.norm(diff))

    if norm_ideal > 1e-12:
        l2_rel_pct = (norm_diff / norm_ideal) * 100.0
        cos_sim = float(np.dot(y_pred, y_ideal) / (np.linalg.norm(y_pred) * norm_ideal + 1e-15))
        snr_val = float(20.0 * np.log10(norm_ideal / (norm_diff + 1e-15))) if norm_diff > 1e-15 else 100.0
    else:
        l2_rel_pct = norm_diff * 100.0
        cos_sim = 1.0 if norm_diff < 1e-9 else 0.0
        snr_val = 0.0

    return MechanismMetrics(
        name=name,
        l2_rel_error_pct=float(l2_rel_pct),
        max_abs_error=float(np.max(np.abs(diff))),
        rms_error=float(np.sqrt(np.mean(np.square(diff)))),
        cosine_similarity=float(cos_sim),
        snr_db=float(snr_val),
    )


ALL_MECHANISM_KEYS = [
    "dac_quantization",
    "g_quantization",
    "programming_variation",
    "read_variation",
    "stuck_faults",
    "temporal_drift",
    "iv_non_linearity",
    "ir_drop",
    "adc_quantization",
]

MECHANISM_LABELS = {
    "dac_quantization": "Input DAC quantization",
    "g_quantization": "Weight conductance resolution",
    "programming_variation": "Programming (write) variation",
    "read_variation": "Read (temporal) noise",
    "stuck_faults": "Stuck-at defect faults",
    "temporal_drift": "Structural relaxation drift",
    "iv_non_linearity": "Sub-Ohmic I-V non-linearity",
    "ir_drop": "Interconnect IR drop",
    "adc_quantization": "Output ADC quantization & noise",
}


def attribute_tile_error(
    weights: ArrayLike,
    inputs: ArrayLike,
    *,
    g_bits: int = 4,
    dac_bits: int = 4,
    adc_bits: int = 4,
    gmin: float = 10.0e-6,
    gmax: float = 100.0e-6,
    vin_max: float = 2.34375,
    vout_max: float = 2.5,
    sigma_prog_rel: float = 0.03,
    sigma_read_rel: float = 0.01,
    p_stuck_hrs: float = 0.0255,
    p_stuck_lrs: float = 0.0045,
    drift_exponent_nu_min: float = 0.02,
    drift_exponent_nu_max: float = 0.06,
    drift_time_s: float = 3.15e7,  # default: 1 year
    iv_non_linearity_beta: float = 1.0,
    v_read_max: float = 0.25,
    r_wire_ohm: float = 1.0,
    adc_noise_std: float = 0.0,
    adc_gain: float = 1.0,
    adc_offset: float = 0.0,
    seed: int = 42,
) -> ErrorAttributionResult:
    """Decompose MVM error into individual standalone and leave-one-out mechanism shares."""
    w = np.asarray(weights, dtype=np.float64)
    x = np.asarray(inputs, dtype=np.float64).reshape(-1)
    rows, cols = w.shape
    if x.shape[0] != cols:
        raise ValueError(f"expected inputs shape ({cols},), got {x.shape}")

    # 1. Ideal floating-point reference
    y_ideal = w @ x

    # Helper to construct and run a tile with designated active parameters
    def run_tile(params: dict[str, Any], s: int = seed) -> NDArray[np.float64]:
        tile = CrossbarTile(
            rows=rows,
            cols=cols,
            g_bits=params.get("g_bits", 16),
            dac_bits=params.get("dac_bits", 16),
            adc_bits=params.get("adc_bits", 16),
            gmin=gmin,
            gmax=gmax,
            vin_max=vin_max,
            vout_max=vout_max,
            sigma_prog_rel=params.get("sigma_prog_rel", 0.0),
            sigma_read_rel=params.get("sigma_read_rel", 0.0),
            p_stuck_hrs=params.get("p_stuck_hrs", 0.0),
            p_stuck_lrs=params.get("p_stuck_lrs", 0.0),
            drift_exponent_nu_min=params.get("drift_exponent_nu_min", 0.0),
            drift_exponent_nu_max=params.get("drift_exponent_nu_max", 0.0),
            drift_time_s=params.get("drift_time_s", 0.0),
            iv_non_linearity_beta=params.get("iv_non_linearity_beta", 0.0),
            v_read_max=v_read_max,
            r_wire_ohm=params.get("r_wire_ohm", 0.0),
            adc_noise_std=params.get("adc_noise_std", 0.0),
            adc_gain=params.get("adc_gain", 1.0),
            adc_offset=params.get("adc_offset", 0.0),
            rng=s,
        )
        tile.program(w)
        return tile.forward(x)

    full_params = {
        "g_bits": g_bits,
        "dac_bits": dac_bits,
        "adc_bits": adc_bits,
        "sigma_prog_rel": sigma_prog_rel,
        "sigma_read_rel": sigma_read_rel,
        "p_stuck_hrs": p_stuck_hrs,
        "p_stuck_lrs": p_stuck_lrs,
        "drift_exponent_nu_min": drift_exponent_nu_min,
        "drift_exponent_nu_max": drift_exponent_nu_max,
        "drift_time_s": drift_time_s,
        "iv_non_linearity_beta": iv_non_linearity_beta,
        "r_wire_ohm": r_wire_ohm,
        "adc_noise_std": adc_noise_std,
        "adc_gain": adc_gain,
        "adc_offset": adc_offset,
    }

    # Combined output (all active)
    y_combined = run_tile(full_params, seed)
    combined_metrics = _compute_metrics(y_combined, y_ideal, "combined_all")

    # Standalone runs (only one mechanism active at its physical value, others ideal)
    standalone_runs: dict[str, dict[str, Any]] = {
        "dac_quantization": {"dac_bits": dac_bits},
        "g_quantization": {"g_bits": g_bits},
        "programming_variation": {"sigma_prog_rel": sigma_prog_rel},
        "read_variation": {"sigma_read_rel": sigma_read_rel},
        "stuck_faults": {"p_stuck_hrs": p_stuck_hrs, "p_stuck_lrs": p_stuck_lrs},
        "temporal_drift": {
            "drift_exponent_nu_min": drift_exponent_nu_min,
            "drift_exponent_nu_max": drift_exponent_nu_max,
            "drift_time_s": drift_time_s,
        },
        "iv_non_linearity": {"iv_non_linearity_beta": iv_non_linearity_beta},
        "ir_drop": {"r_wire_ohm": r_wire_ohm},
        "adc_quantization": {
            "adc_bits": adc_bits,
            "adc_noise_std": adc_noise_std,
            "adc_gain": adc_gain,
            "adc_offset": adc_offset,
        },
    }

    standalone_results: dict[str, MechanismMetrics] = {}
    for key, p_dict in standalone_runs.items():
        y_mech = run_tile(p_dict, seed)
        standalone_results[key] = _compute_metrics(y_mech, y_ideal, key)
    standalone_results["combined_all"] = combined_metrics

    # Leave-One-Out (LOO) runs: full_params with only key set to ideal
    ideal_overrides: dict[str, dict[str, Any]] = {
        "dac_quantization": {"dac_bits": 16},
        "g_quantization": {"g_bits": 16},
        "programming_variation": {"sigma_prog_rel": 0.0},
        "read_variation": {"sigma_read_rel": 0.0},
        "stuck_faults": {"p_stuck_hrs": 0.0, "p_stuck_lrs": 0.0},
        "temporal_drift": {"drift_time_s": 0.0},
        "iv_non_linearity": {"iv_non_linearity_beta": 0.0},
        "ir_drop": {"r_wire_ohm": 0.0},
        "adc_quantization": {
            "adc_bits": 16,
            "adc_noise_std": 0.0,
            "adc_gain": 1.0,
            "adc_offset": 0.0,
        },
    }

    loo_residuals: dict[str, float] = {}
    loo_contributions: dict[str, float] = {}
    combined_rms = combined_metrics.rms_error

    for key, override in ideal_overrides.items():
        p_loo = dict(full_params)
        p_loo.update(override)
        y_loo = run_tile(p_loo, seed)
        m_loo = _compute_metrics(y_loo, y_ideal, f"loo_without_{key}")
        loo_residuals[key] = m_loo.rms_error
        # contribution = error recovered by idealizing that single mechanism
        loo_contributions[key] = max(0.0, combined_rms - m_loo.rms_error)

    # Compute percentage shares
    total_loo_contrib = sum(loo_contributions.values())
    loo_shares = {
        k: (c / total_loo_contrib * 100.0 if total_loo_contrib > 0.0 else 0.0)
        for k, c in loo_contributions.items()
    }

    total_standalone_rms = sum(standalone_results[k].rms_error for k in ALL_MECHANISM_KEYS)
    standalone_shares = {
        k: (
            standalone_results[k].rms_error / total_standalone_rms * 100.0
            if total_standalone_rms > 0.0
            else 0.0
        )
        for k in ALL_MECHANISM_KEYS
    }

    summary = {
        "combined_rms_error": combined_rms,
        "combined_l2_rel_error_pct": combined_metrics.l2_rel_error_pct,
        "combined_cosine_similarity": combined_metrics.cosine_similarity,
        "dominant_mechanism_standalone": max(
            ALL_MECHANISM_KEYS, key=lambda k: standalone_results[k].rms_error
        ),
        "dominant_mechanism_loo": (
            max(ALL_MECHANISM_KEYS, key=lambda k: loo_contributions[k])
            if total_loo_contrib > 0.0
            else "none"
        ),
    }

    return ErrorAttributionResult(
        ideal_output=y_ideal.tolist(),
        combined_output=y_combined.tolist(),
        standalone=standalone_results,
        leave_one_out_residuals=loo_residuals,
        leave_one_out_contributions=loo_contributions,
        leave_one_out_shares_pct=loo_shares,
        standalone_shares_pct=standalone_shares,
        summary=summary,
    )


def attribute_from_profiles(
    weights: ArrayLike,
    inputs: ArrayLike,
    crossbar_profile: dict[str, Any] | str | Path,
    dac_profile: dict[str, Any] | str | Path,
    adc_profile: dict[str, Any] | str | Path,
    *,
    g_bits: int = 4,
    drift_time_s: float = 3.15e7,
    seed: int = 42,
) -> ErrorAttributionResult:
    """Run per-mechanism error attribution consuming validated profiles."""
    cb = load_device_profile(crossbar_profile, physical_claim=False)
    dac = load_device_profile(dac_profile, physical_claim=False)
    adc = load_device_profile(adc_profile, physical_claim=False)

    cb_f = cb.get("fields", {})
    dac_f = dac.get("fields", {})
    adc_f = adc.get("fields", {})

    return attribute_tile_error(
        weights,
        inputs,
        g_bits=g_bits,
        dac_bits=int(dac_f.get("bits", {}).get("value", 4)),
        adc_bits=int(adc_f.get("bits", {}).get("value", 4)),
        gmin=float(cb_f.get("g0_s", {}).get("value", 10.0e-6)),
        gmax=float(cb_f.get("g0_s", {}).get("value", 10.0e-6))
        + float(cb_f.get("gscale_s_per_w", {}).get("value", 90.0e-6)),
        vin_max=float(dac_f.get("full_scale_v", {}).get("value", 2.34375)),
        vout_max=float(adc_f.get("input_range_v", {}).get("value", 2.5)),
        sigma_prog_rel=float(cb_f.get("sigma_prog_rel", {}).get("value", 0.03)),
        sigma_read_rel=float(cb_f.get("sigma_read_rel", {}).get("value", 0.01)),
        p_stuck_hrs=float(cb_f.get("p_stuck_hrs", {}).get("value", 0.0255)),
        p_stuck_lrs=float(cb_f.get("p_stuck_lrs", {}).get("value", 0.0045)),
        drift_exponent_nu_min=float(cb_f.get("drift_exponent_nu_min", {}).get("value", 0.02)),
        drift_exponent_nu_max=float(cb_f.get("drift_exponent_nu_max", {}).get("value", 0.06)),
        drift_time_s=drift_time_s,
        iv_non_linearity_beta=float(cb_f.get("iv_non_linearity_beta", {}).get("value", 1.0)),
        v_read_max=float(cb_f.get("v_read_max_v", {}).get("value", 0.25)),
        r_wire_ohm=float(cb_f.get("r_wire_ohm", {}).get("value", 1.0)),
        seed=seed,
    )


def evaluate_attribution_suite(
    n: int = 16,
    n_vectors: int = 20,
    seed: int = 42,
    drift_time_s: float = 3.15e7,
) -> dict[str, Any]:
    """Run comprehensive error attribution suite across canonical matrix structures."""
    rng = np.random.default_rng(seed)

    canonical_matrices: dict[str, np.ndarray] = {
        "identity": np.eye(n, dtype=np.float64),
        "mixed_sign": rng.uniform(-1.0, 1.0, size=(n, n)),
        "sparse_80pct": rng.choice(
            [0.0, 0.5, -0.5, 1.0, -1.0], size=(n, n), p=[0.80, 0.05, 0.05, 0.05, 0.05]
        ),
        "rank_one": np.outer(rng.uniform(-1.0, 1.0, size=n), rng.uniform(-1.0, 1.0, size=n)),
    }

    test_vectors = rng.uniform(-1.0, 1.0, size=(n_vectors, n))
    results_by_matrix: dict[str, Any] = {}

    for mat_name, w_mat in canonical_matrices.items():
        mech_l2_pcts: dict[str, list[float]] = {k: [] for k in ALL_MECHANISM_KEYS + ["combined_all"]}
        mech_rms: dict[str, list[float]] = {k: [] for k in ALL_MECHANISM_KEYS + ["combined_all"]}
        loo_shares_list: dict[str, list[float]] = {k: [] for k in ALL_MECHANISM_KEYS}

        for idx, x_vec in enumerate(test_vectors):
            res = attribute_tile_error(
                w_mat,
                x_vec,
                seed=seed + idx * 17,
                drift_time_s=drift_time_s,
            )
            for k in ALL_MECHANISM_KEYS + ["combined_all"]:
                mech_l2_pcts[k].append(res.standalone[k].l2_rel_error_pct)
                mech_rms[k].append(res.standalone[k].rms_error)
            for k in ALL_MECHANISM_KEYS:
                loo_shares_list[k].append(res.leave_one_out_shares_pct[k])

        results_by_matrix[mat_name] = {
            "mean_l2_rel_error_pct": {k: float(np.mean(v)) for k, v in mech_l2_pcts.items()},
            "mean_rms_error": {k: float(np.mean(v)) for k, v in mech_rms.items()},
            "mean_loo_share_pct": {k: float(np.mean(v)) for k, v in loo_shares_list.items()},
        }

    return {
        "dimension": n,
        "n_vectors": n_vectors,
        "drift_time_s": drift_time_s,
        "matrices": results_by_matrix,
    }
