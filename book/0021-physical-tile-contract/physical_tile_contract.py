r"""Chapter 0021 — Physical Tile Contract (Gate R5).

Validates the end-to-end behavioral compute tile (`analog_llm.CrossbarTile`)
configured from the trio of validated physical profiles:
1. `device_profiles/crossbar-v1.json` (G in [10 uS, 100 uS], differential pair, +/-2.5V headroom)
2. `device_profiles/dac-r2r-v1.json` (4-bit R-2R DAC, 2.34V full scale)
3. `device_profiles/adc-sar-v1.json` (4-bit SAR ADC, +/-2.5V input envelope)

Signal Flow & Mathematics:
--------------------------
1. Input Normalization:
   x_norm = (x / ||x||_inf) * V_dac_max
2. DAC Quantization:
   V_in = DAC_4bit(x_norm) in [0, V_dac_max]
3. Weight Normalization & Conductance Mapping:
   W_norm = W / ||W||_inf in [-1, 1]
   (G+, G-) = map_differential(W_norm, bits=g_bits, gmin=10uS, gmax=100uS)
4. Analog Current Summation & Differential TIA:
   I+ = (G+)^T V_in,  I- = (G-)^T V_in
   V_diff = Rf * (I+ - I-) with Rf = 10 kOhm
5. Output SAR ADC Quantization & Digital Recovery:
   y_norm = ADC_4bit(V_diff)
   y = y_norm * (||W||_inf * ||x||_inf / V_dac_max) / (gmax - gmin)
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np

from analog_llm.profile_adapter import (
    build_tile_factory_from_converter_profiles,
    tile_config_from_profile,
)

_REPO = Path(__file__).resolve().parents[2]
_PROFILES_DIR = _REPO / "device_profiles"
_CROSSBAR_PROFILE = _PROFILES_DIR / "crossbar-v1.json"
_DAC_PROFILE = _PROFILES_DIR / "dac-r2r-v1.json"
_ADC_PROFILE = _PROFILES_DIR / "adc-sar-v1.json"

DEFAULT_SEED = 42


def evaluate_canonical_matrices(n: int = 16) -> dict[str, Any]:
    """Evaluate physical tile across canonical matrix structures."""
    factory_4b = build_tile_factory_from_converter_profiles(
        _CROSSBAR_PROFILE,
        _DAC_PROFILE,
        _ADC_PROFILE,
        n,
        n,
        g_bits=4,
        physical_claim=False,
    )
    factory_6b = build_tile_factory_from_converter_profiles(
        _CROSSBAR_PROFILE,
        _DAC_PROFILE,
        _ADC_PROFILE,
        n,
        n,
        g_bits=6,
        physical_claim=False,
    )

    rng = np.random.default_rng(DEFAULT_SEED)

    # Canonical Matrices:
    matrices: dict[str, np.ndarray] = {
        "identity": np.eye(n, dtype=np.float64),
        "positive_uniform": rng.uniform(0.1, 1.0, size=(n, n)),
        "negative_uniform": rng.uniform(-1.0, -0.1, size=(n, n)),
        "mixed_sign": rng.uniform(-1.0, 1.0, size=(n, n)),
        "rank_one": np.outer(rng.uniform(-1.0, 1.0, size=n), rng.uniform(-1.0, 1.0, size=n)),
        "sparse_90pct": rng.choice([0.0, 0.5, -0.5, 1.0, -1.0], size=(n, n), p=[0.90, 0.025, 0.025, 0.025, 0.025]),
        "zero_matrix": np.zeros((n, n), dtype=np.float64),
    }

    # 100 test input vectors per matrix
    n_vectors = 100
    test_vectors = rng.uniform(-1.0, 1.0, size=(n_vectors, n))

    results_by_matrix: dict[str, Any] = {}

    for name, w_mat in matrices.items():
        tile_4b = factory_4b()
        tile_6b = factory_6b()

        tile_4b.program(w_mat)
        tile_6b.program(w_mat)

        errs_4b = []
        errs_6b = []
        cos_sims_4b = []
        cos_sims_6b = []

        for x in test_vectors:
            y_ideal = w_mat @ x
            y_4b = tile_4b.forward(x)
            y_6b = tile_6b.forward(x)

            norm_ideal = np.linalg.norm(y_ideal)
            if norm_ideal > 1e-12:
                err_4b = float(np.linalg.norm(y_4b - y_ideal) / norm_ideal * 100.0)
                err_6b = float(np.linalg.norm(y_6b - y_ideal) / norm_ideal * 100.0)
                cos_4b = float(np.dot(y_4b, y_ideal) / (np.linalg.norm(y_4b) * norm_ideal + 1e-15))
                cos_6b = float(np.dot(y_6b, y_ideal) / (np.linalg.norm(y_6b) * norm_ideal + 1e-15))
            else:
                err_4b = float(np.linalg.norm(y_4b))
                err_6b = float(np.linalg.norm(y_6b))
                cos_4b = 1.0
                cos_6b = 1.0

            errs_4b.append(err_4b)
            errs_6b.append(err_6b)
            cos_sims_4b.append(cos_4b)
            cos_sims_6b.append(cos_6b)

        results_by_matrix[name] = {
            "mean_error_4b_pct": float(np.mean(errs_4b)),
            "max_error_4b_pct": float(np.max(errs_4b)),
            "rms_error_4b_pct": float(np.sqrt(np.mean(np.square(errs_4b)))),
            "mean_cosine_sim_4b": float(np.mean(cos_sims_4b)),
            "mean_error_6b_pct": float(np.mean(errs_6b)),
            "max_error_6b_pct": float(np.max(errs_6b)),
            "rms_error_6b_pct": float(np.sqrt(np.mean(np.square(errs_6b)))),
            "mean_cosine_sim_6b": float(np.mean(cos_sims_6b)),
        }

    return results_by_matrix


def run_physical_tile_extract() -> dict[str, Any]:
    """Run comprehensive characterization across matrix types and tile sizes."""
    matrix_results = evaluate_canonical_matrices(n=16)

    # Dimension scaling evaluation (4x4 to 32x32)
    dim_sweeps = []
    for dim in [4, 8, 16, 32]:
        res = evaluate_canonical_matrices(n=dim)
        dim_sweeps.append({
            "dimension": dim,
            "mixed_sign_mean_error_4b_pct": res["mixed_sign"]["mean_error_4b_pct"],
            "mixed_sign_mean_error_6b_pct": res["mixed_sign"]["mean_error_6b_pct"],
            "mixed_sign_cosine_sim_4b": res["mixed_sign"]["mean_cosine_sim_4b"],
        })

    # Linearity sweep for 1D transfer curve plotting
    rng = np.random.default_rng(DEFAULT_SEED)
    w_fixed = rng.uniform(-1.0, 1.0, size=(16, 16))
    factory = build_tile_factory_from_converter_profiles(
        _CROSSBAR_PROFILE,
        _DAC_PROFILE,
        _ADC_PROFILE,
        16,
        16,
        g_bits=4,
        physical_claim=False,
    )
    tile = factory()
    tile.program(w_fixed)

    x_base = rng.uniform(-1.0, 1.0, size=16)
    x_base = x_base / np.linalg.norm(x_base)

    scale_factors = np.linspace(-1.0, 1.0, 50)
    transfer_curve = []
    for s in scale_factors:
        x_vec = s * x_base
        y_ideal = w_fixed @ x_vec
        y_actual = tile.forward(x_vec)
        transfer_curve.append({
            "scale": float(s),
            "ideal_out_0": float(y_ideal[0]),
            "tile_out_0": float(y_actual[0]),
            "error_out_0": float(y_actual[0] - y_ideal[0]),
        })

    # Baseline tile config
    tile_cfg = tile_config_from_profile(_CROSSBAR_PROFILE, g_bits=4, dac_bits=4, adc_bits=4, physical_claim=False)

    extract = {
        "schema_version": "0.1.0",
        "chapter": "0021-physical-tile-contract",
        "title": "Physical Tile Contract & Multi-Profile Integration",
        "profiles_consumed": {
            "crossbar": str(_CROSSBAR_PROFILE.relative_to(_REPO)),
            "dac": str(_DAC_PROFILE.relative_to(_REPO)),
            "adc": str(_ADC_PROFILE.relative_to(_REPO)),
        },
        "tile_parameters": {
            "gmin_s": tile_cfg["gmin"],
            "gmax_s": tile_cfg["gmax"],
            "dac_bits": 4,
            "adc_bits": 4,
            "vin_max_v": tile_cfg["vin_max"],
            "vout_max_v": tile_cfg["vout_max"],
        },
        "canonical_matrix_results_16x16": matrix_results,
        "dimension_sweeps": dim_sweeps,
        "transfer_curve_50pts": transfer_curve,
        "summary": {
            "mixed_sign_mean_error_4b_pct": matrix_results["mixed_sign"]["mean_error_4b_pct"],
            "mixed_sign_rms_error_4b_pct": matrix_results["mixed_sign"]["rms_error_4b_pct"],
            "mixed_sign_cosine_sim_4b": matrix_results["mixed_sign"]["mean_cosine_sim_4b"],
            "mixed_sign_mean_error_6b_pct": matrix_results["mixed_sign"]["mean_error_6b_pct"],
            "zero_matrix_error": matrix_results["zero_matrix"]["mean_error_4b_pct"],
            "evidence_class": "derived",
            "provenance": "Profile-driven behavioral CrossbarTile execution consuming crossbar-v1, dac-r2r-v1, and adc-sar-v1 profiles",
        },
    }
    return extract


def main() -> None:
    print("Running Chapter 0021 Physical Tile Contract Extraction...")
    extract = run_physical_tile_extract()
    out_dir = Path(__file__).resolve().parents[2] / "verification" / "circuit" / "results"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / "physical-tile-0021-extract.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(extract, f, indent=2)
    print(f"Committed extract written to {out_file}")
    s = extract["summary"]
    print(f"  Mixed-Sign MVM Mean Error (4-bit cell): {s['mixed_sign_mean_error_4b_pct']:.2f}%")
    print(f"  Mixed-Sign MVM Mean Error (6-bit cell): {s['mixed_sign_mean_error_6b_pct']:.2f}%")
    print(f"  Mixed-Sign Output Cosine Similarity:   {s['mixed_sign_cosine_sim_4b']:.5f}")
    print(f"  Zero Matrix Output Error:             {s['zero_matrix_error']:.6f}")


if __name__ == "__main__":
    main()
