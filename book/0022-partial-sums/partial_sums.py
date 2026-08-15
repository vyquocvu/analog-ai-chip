r"""Chapter 0022 — Partial Sums & Multi-Tile Spatial Partitioning (Gate R5).

Models spatial matrix decomposition across modular physical crossbar tiles
and digital partial-sum accumulation:

1. **Spatial Decomposition & Tiling**:
   A logical matrix W \in \mathbb{R}^{M_{out} \times M_{in}} is partitioned into
   a K_r \times K_c grid of sub-blocks W_{i,j} of size R \times C \le 32 \times 32.
   The full matrix-vector product is computed as:
       y_i = \sum_{j=0}^{K_c - 1} y_{i,j}, \quad y_{i,j} = \text{TileForward}(W_{i,j}, x_j)

2. **Noise and Quantization Variance Scaling**:
   Independent converter quantization and read noise across K_c tiles add in variance:
       \sigma_{accum}^2 = \sum_{j=0}^{K_c - 1} \sigma_{ADC,j}^2 = K_c \cdot \sigma_{ADC}^2
       \implies \sigma_{accum} = \sqrt{K_c} \cdot \sigma_{ADC}

3. **Digital Accumulator Precision**:
   Accumulating K_c partial sums from B_{ADC}-bit converters requires:
       B_{acc} \ge B_{ADC} + \lceil \log_2 K_c \rceil \text{ bits}
   to guarantee overflow-free integer addition.

4. **Tiled vs Monolithic IR-Drop Tradeoff**:
   Monolithic arrays scale error quadratically with dimension (\text{Error}_{IR} \propto N^2).
   Tiling into modular 16\times 16 or 32\times 32 sub-arrays eliminates large-scale IR drop,
   replacing it with bounded, predictable partial-sum quantization.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

from analog_llm.profile_adapter import build_tile_factory_from_converter_profiles
from analog_llm.tile import CrossbarTile

_REPO = Path(__file__).resolve().parents[2]
_PROFILES_DIR = _REPO / "device_profiles"
_CROSSBAR_PROFILE = _PROFILES_DIR / "crossbar-v1.json"
_DAC_PROFILE = _PROFILES_DIR / "dac-r2r-v1.json"
_ADC_PROFILE = _PROFILES_DIR / "adc-sar-v1.json"

DEFAULT_SEED = 42


@dataclass
class TiledMatrixResult:
    """Result of tiled matrix-vector multiplication."""

    y_actual: np.ndarray
    y_ideal: np.ndarray
    rel_error_pct: float
    cosine_similarity: float
    num_tiles_used: int
    partial_sums_per_output: int


class TiledMatrixExecutor:
    """Executes arbitrary-dimension MVM over a grid of physical CrossbarTiles."""

    def __init__(
        self,
        tile_rows: int = 16,
        tile_cols: int = 16,
        g_bits: int = 4,
        acc_bits: int | None = None,
    ) -> None:
        self.tile_rows = tile_rows
        self.tile_cols = tile_cols
        self.g_bits = g_bits
        self.acc_bits = acc_bits
        self.tile_factory = build_tile_factory_from_converter_profiles(
            _CROSSBAR_PROFILE,
            _DAC_PROFILE,
            _ADC_PROFILE,
            tile_rows,
            tile_cols,
            g_bits=g_bits,
            physical_claim=False,
        )

    def execute_mvm(self, w: np.ndarray, x: np.ndarray) -> TiledMatrixResult:
        """Partition W and x into tiles and accumulate partial sums."""
        m_out, m_in = w.shape
        x_flat = x.reshape(-1)

        k_r = math.ceil(m_out / self.tile_rows)
        k_c = math.ceil(m_in / self.tile_cols)

        y_actual = np.zeros(m_out, dtype=np.float64)
        y_ideal = w @ x_flat

        tiles_used = 0
        for i in range(k_r):
            r_start = i * self.tile_rows
            r_end = min(r_start + self.tile_rows, m_out)
            r_len = r_end - r_start

            for j in range(k_c):
                c_start = j * self.tile_cols
                c_end = min(c_start + self.tile_cols, m_in)
                c_len = c_end - c_start

                w_block = w[r_start:r_end, c_start:c_end]
                x_block = x_flat[c_start:c_end]

                # Pad to physical tile dimensions if on matrix boundary
                w_padded = np.zeros((self.tile_rows, self.tile_cols), dtype=np.float64)
                w_padded[:r_len, :c_len] = w_block

                x_padded = np.zeros(self.tile_cols, dtype=np.float64)
                x_padded[:c_len] = x_block

                tile: CrossbarTile = self.tile_factory()
                tile.program(w_padded)
                y_block = tile.forward(x_padded)

                y_actual[r_start:r_end] += y_block[:r_len]
                tiles_used += 1

        norm_ideal = np.linalg.norm(y_ideal)
        if norm_ideal > 1e-12:
            rel_error = float(np.linalg.norm(y_actual - y_ideal) / norm_ideal * 100.0)
            cos_sim = float(np.dot(y_actual, y_ideal) / (np.linalg.norm(y_actual) * norm_ideal + 1e-15))
        else:
            rel_error = float(np.linalg.norm(y_actual))
            cos_sim = 1.0

        return TiledMatrixResult(
            y_actual=y_actual,
            y_ideal=y_ideal,
            rel_error_pct=rel_error,
            cosine_similarity=cos_sim,
            num_tiles_used=tiles_used,
            partial_sums_per_output=k_c,
        )


def evaluate_noise_scaling(k_c_list: list[int], tile_dim: int = 16) -> list[dict[str, Any]]:
    """Analyze noise and variance growth as number of partial sums K_c increases."""
    rng = np.random.default_rng(DEFAULT_SEED)
    executor = TiledMatrixExecutor(tile_rows=tile_dim, tile_cols=tile_dim, g_bits=4)

    results = []
    n_trials = 50

    for kc in k_c_list:
        m_in = kc * tile_dim
        m_out = tile_dim

        errors = []
        for _ in range(n_trials):
            w = rng.uniform(-1.0, 1.0, size=(m_out, m_in))
            x = rng.uniform(-1.0, 1.0, size=m_in)
            res = executor.execute_mvm(w, x)
            errors.append(res.rel_error_pct)

        mean_err = float(np.mean(errors))
        std_err = float(np.std(errors))
        rms_err = float(np.sqrt(np.mean(np.square(errors))))

        # Required accumulator bit width for 4-bit ADC output + log2(Kc)
        acc_bits_required = 4 + math.ceil(math.log2(max(kc, 1)))

        results.append({
            "num_partial_sums_kc": kc,
            "matrix_input_dim": m_in,
            "mean_error_pct": mean_err,
            "std_error_pct": std_err,
            "rms_error_pct": rms_err,
            "acc_bits_required": acc_bits_required,
            "theoretical_noise_scale": float(np.sqrt(kc)),
        })

    return results


def evaluate_tiled_vs_monolithic() -> list[dict[str, Any]]:
    """Compare tiled architecture accuracy against monolithic crossbars subject to IR drop."""
    rng = np.random.default_rng(DEFAULT_SEED)
    sizes = [16, 32, 64, 128, 256]

    exec_16 = TiledMatrixExecutor(tile_rows=16, tile_cols=16, g_bits=4)
    exec_32 = TiledMatrixExecutor(tile_rows=32, tile_cols=32, g_bits=4)

    comparisons = []
    for n in sizes:
        w = rng.uniform(-1.0, 1.0, size=(n, n))
        x = rng.uniform(-1.0, 1.0, size=n)

        # 1. Tiled with 16x16
        res_16 = exec_16.execute_mvm(w, x)

        # 2. Tiled with 32x32
        res_32 = exec_32.execute_mvm(w, x)

        # 3. Monolithic IR-drop model: Error_IR ~ (N/32)^2 * 6.77%
        # Derived from Chapter 0017 scaling law (N^2 * R_wire * G_max)
        monolithic_ir_error = float(6.7726 * ((n / 32.0) ** 2))

        comparisons.append({
            "dimension": n,
            "tiled_16x16_error_pct": res_16.rel_error_pct,
            "tiled_16x16_tiles": res_16.num_tiles_used,
            "tiled_32x32_error_pct": res_32.rel_error_pct,
            "tiled_32x32_tiles": res_32.num_tiles_used,
            "monolithic_ir_error_pct": monolithic_ir_error,
            "tiling_advantage": "Tiling avoids quadratic IR drop breakdown" if n >= 64 else "Comparable",
        })

    return comparisons


def run_partial_sums_extract() -> dict[str, Any]:
    """Run full characterization of partial sums and multi-tile partitioning."""
    k_c_sweeps = evaluate_noise_scaling([1, 2, 4, 8, 16, 32], tile_dim=16)
    monolithic_vs_tiled = evaluate_tiled_vs_monolithic()

    extract = {
        "schema_version": "0.1.0",
        "chapter": "0022-partial-sums",
        "title": "Partial Sums and Multi-Tile Spatial Partitioning",
        "partial_sum_scaling_kc": k_c_sweeps,
        "monolithic_vs_tiled_comparison": monolithic_vs_tiled,
        "accumulator_rules": {
            "adc_bits": 4,
            "formula": "B_acc >= B_adc + ceil(log2(K_c))",
            "for_kc_4": 6,
            "for_kc_16": 8,
            "for_kc_64": 10,
        },
        "summary": {
            "kc_1_mean_error_pct": k_c_sweeps[0]["mean_error_pct"],
            "kc_16_mean_error_pct": k_c_sweeps[4]["mean_error_pct"],
            "monolithic_64_ir_error_pct": monolithic_vs_tiled[2]["monolithic_ir_error_pct"],
            "tiled_64_16x16_error_pct": monolithic_vs_tiled[2]["tiled_16x16_error_pct"],
            "evidence_class": "derived",
            "provenance": "Profile-driven multi-tile spatial partitioner accumulating digital partial sums across crossbar-v1 tiles",
        },
    }
    return extract


def main() -> None:
    print("Running Chapter 0022 Partial Sums Extraction...")
    extract = run_partial_sums_extract()
    out_dir = Path(__file__).resolve().parents[2] / "verification" / "circuit" / "results"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / "partial-sums-0022-extract.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(extract, f, indent=2)
    print(f"Committed extract written to {out_file}")
    s = extract["summary"]
    print(f"  Single Tile Error (Kc=1):     {s['kc_1_mean_error_pct']:.2f}%")
    print(f"  16-Tile Partial Sum Error (Kc=16): {s['kc_16_mean_error_pct']:.2f}%")
    print(f"  64x64 Monolithic IR Drop Error: {s['monolithic_64_ir_error_pct']:.2f}%")
    print(f"  64x64 Tiled (16x16) Error:     {s['tiled_64_16x16_error_pct']:.2f}%")


if __name__ == "__main__":
    main()
