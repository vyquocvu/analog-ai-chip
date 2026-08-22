r"""Chapter 0049 — Block-Streamed Linear Execution (Gate R11, Memory-Bounded Simulator).

Demonstrates and verifies block-streamed linear evaluation across physical tile
partitions, proving bitwise/machine-precision equivalence and calculating working
memory bounds across T0, T1, and T2 scalable design tiers.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import numpy as np

_REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO))

from analog_llm.block_stream import (
    calculate_execution_memory_budget,
    streamed_linear_mvm,
)

RESULTS_DIR = _REPO / "verification" / "circuit" / "results"
RESULT_PATH = RESULTS_DIR / "block-streamed-0049-extract.json"


def run_block_stream_extract() -> dict[str, Any]:
    """Execute block-streaming verification suites and memory budgets."""
    benchmarks: dict[str, Any] = {}

    # 1. Hand-computable validation case (4x6 matrix, 2x2 blocks)
    W_hand = np.array([
        [1.0, 2.0, 3.0, 4.0, 5.0, 6.0],
        [2.0, 0.0, 1.0, -1.0, 0.5, 2.0],
        [-1.0, 1.0, 0.0, 2.0, -2.0, 1.0],
        [0.5, -0.5, 1.0, 0.0, 3.0, -1.0],
    ])
    b_hand = np.array([0.1, -0.2, 0.3, 0.4])
    x_hand = np.array([1.0, 0.5, 2.0, -1.0, 0.0, 1.5])
    expected_hand = x_hand @ W_hand.T + b_hand
    actual_hand = streamed_linear_mvm(x_hand, W_hand, bias=b_hand, tile_rows=2, tile_cols=2)
    hand_err = float(np.max(np.abs(actual_hand - expected_hand)))
    assert hand_err < 1e-12, "Hand calculation block streaming failed"

    benchmarks["hand_calc_4x6"] = {
        "out_features": 4,
        "in_features": 6,
        "tile_rows": 2,
        "tile_cols": 2,
        "max_abs_error": hand_err,
        "memory_budget": calculate_execution_memory_budget(6, 4, tokens=1, dtype_bytes=2, tile_rows=2, tile_cols=2).__dict__,
    }

    # 2. Scalable Tier Projections Evaluation (T0: 64D, T1: 2048D, T2: 4096D)
    tier_configs = [
        ("t0_tinygpt_proj", 64, 64, 16),
        ("t1_1b_attn_proj", 2048, 2048, 16),
        ("t2_7b_attn_proj", 4096, 4096, 16),
    ]

    for name, in_f, out_f, tile_dim in tier_configs:
        rng = np.random.default_rng(42)
        tokens = 4
        W = rng.normal(0.0, 0.02, (out_f, in_f))
        X = rng.normal(0.0, 1.0, (tokens, in_f))

        expected = X @ W.T
        actual = streamed_linear_mvm(X, W, tile_rows=tile_dim, tile_cols=tile_dim)
        max_err = float(np.max(np.abs(actual - expected)))
        assert max_err < 1e-12, f"{name} block streaming failed"

        budget_single = calculate_execution_memory_budget(
            in_f, out_f, tokens=1, dtype_bytes=2, tile_rows=tile_dim, tile_cols=tile_dim
        )
        budget_batched = calculate_execution_memory_budget(
            in_f, out_f, tokens=tokens, dtype_bytes=2, tile_rows=tile_dim, tile_cols=tile_dim
        )

        benchmarks[name] = {
            "out_features": out_f,
            "in_features": in_f,
            "tile_dimension": f"{tile_dim}x{tile_dim}",
            "total_blocks": (in_f // tile_dim) * (out_f // tile_dim),
            "max_abs_error": max_err,
            "single_token_memory_budget": budget_single.__dict__,
            "batched_prefill_memory_budget": budget_batched.__dict__,
        }

    payload: dict[str, Any] = {
        "chapter": "0049-block-streamed-execution",
        "gate": "R11",
        "status": "PASSED",
        "claim_level": "functional/software-reference",
        "benchmarks": benchmarks,
    }

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    with open(RESULT_PATH, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)

    return payload


def main() -> None:
    results = run_block_stream_extract()
    print("=" * 85)
    print("CHAPTER 0049: BLOCK-STREAMED LINEAR EXECUTION (GATE R11)")
    print("=" * 85)
    print(f"Status: {results['status']} | Claim Level: {results['claim_level']}\n")
    print(
        f"{'Benchmark':<18} | {'Shape':<12} | {'Blocks':<8} | {'Float64 Mem':<14} | {'Streamed Mem':<14} | {'Reduction':<10}"
    )
    print("-" * 85)
    for name, r in results["benchmarks"].items():
        if "single_token_memory_budget" in r:
            b = r["single_token_memory_budget"]
            shape_str = f"{r['out_features']}x{r['in_features']}"
            print(
                f"{name:<18} | {shape_str:<12} | {r['total_blocks']:<8,d} | "
                f"{b['whole_matrix_float64_bytes']:<14,d} | {b['peak_working_bytes']:<14,d} | "
                f"{b['memory_reduction_ratio']:<10.1f}x"
            )
    print("=" * 85)
    print(f"Extracted artifact saved to: {RESULT_PATH}\n")


if __name__ == "__main__":
    main()
