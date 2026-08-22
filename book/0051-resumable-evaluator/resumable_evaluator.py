r"""Chapter 0051 — Resumable Model Evaluator & Execution Envelope (Gate R11 Exit).

Demonstrates per-layer serialized checkpoints, interruption resumption with
SHA256 integrity verification, ledger anti-double-counting, and tier budgets.
"""

from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path
from typing import Any

import numpy as np

_REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO))

from analog_llm.generalized_decoder import GeneralizedDecoder
from analog_llm.model_manifest import ModelManifest
from analog_llm.resumable_evaluator import (
    TIER_BUDGETS,
    EvaluationMode,
    ResumableModelEvaluator,
)

RESULTS_DIR = _REPO / "verification" / "circuit" / "results"
RESULT_PATH = RESULTS_DIR / "resumable-evaluator-0051-extract.json"
SCRATCH_DIR = _REPO / "scratch" / "resumable_0051"


def _build_demo_decoder() -> GeneralizedDecoder:
    manifest = ModelManifest(
        vocab_size=32,
        hidden_size=16,
        num_layers=4,
        num_attention_heads=4,
        num_key_value_heads=2,
        intermediate_size=32,
        context_length=16,
        dtype="float32",
        norm_type="rmsnorm",
        position_type="rope",
        activation_type="swiglu",
        attention_type="gqa",
        linear_bias=False,
        tied_embeddings=False,
    )
    rng = np.random.default_rng(100)
    w: dict[str, np.ndarray] = {
        "token_embedding.weight": rng.normal(0, 0.02, (32, 16)),
        "final_norm.weight": np.ones((16,)),
        "lm_head.weight": rng.normal(0, 0.02, (32, 16)),
    }
    head_dim = manifest.head_dimension
    for i in range(4):
        p = f"layers.{i}."
        w[f"{p}attention_norm.weight"] = np.ones((16,))
        w[f"{p}attention.q_proj.weight"] = rng.normal(0, 0.02, (16, 16))
        w[f"{p}attention.k_proj.weight"] = rng.normal(0, 0.02, (manifest.num_key_value_heads * head_dim, 16))
        w[f"{p}attention.v_proj.weight"] = rng.normal(0, 0.02, (manifest.num_key_value_heads * head_dim, 16))
        w[f"{p}attention.out_proj.weight"] = rng.normal(0, 0.02, (16, 16))

        w[f"{p}mlp_norm.weight"] = np.ones((16,))
        w[f"{p}mlp.gate_proj.weight"] = rng.normal(0, 0.02, (32, 16))
        w[f"{p}mlp.up_proj.weight"] = rng.normal(0, 0.02, (32, 16))
        w[f"{p}mlp.down_proj.weight"] = rng.normal(0, 0.02, (16, 32))

    return GeneralizedDecoder(manifest, weights=w)


def run_resumable_extract() -> dict[str, Any]:
    """Execute resumable evaluation verification and extract deterministic artifacts."""
    if SCRATCH_DIR.exists():
        shutil.rmtree(SCRATCH_DIR)
    SCRATCH_DIR.mkdir(parents=True, exist_ok=True)

    decoder = _build_demo_decoder()
    prompt = [1, 7, 14, 3]

    # 1. Baseline Full Execution
    full_dir = SCRATCH_DIR / "full"
    eval_full = ResumableModelEvaluator(decoder, checkpoint_dir=full_dir, mode=EvaluationMode.EXACT)
    logits_full, summary_full = eval_full.evaluate_prompt(prompt)

    # 2. Interrupted Execution (stops after layer 1)
    resumed_dir = SCRATCH_DIR / "resumed"
    eval_part = ResumableModelEvaluator(decoder, checkpoint_dir=resumed_dir, mode=EvaluationMode.EXACT)
    _, _summary_interrupted = eval_part.evaluate_prompt(prompt, interrupt_after_layer=1)

    # 3. Resumed Execution (resumes layers 0, 1 from disk, computes layers 2, 3)
    eval_resumed = ResumableModelEvaluator(decoder, checkpoint_dir=resumed_dir, mode=EvaluationMode.EXACT)
    logits_resumed, summary_resumed = eval_resumed.evaluate_prompt(prompt)

    max_diff = float(np.max(np.abs(logits_resumed - logits_full)))
    assert max_diff < 1e-12, "Resumed evaluation logits diverged from full single-pass run"
    assert summary_resumed["layers_resumed"] == 2
    assert summary_resumed["layers_computed"] == 2
    assert summary_resumed["cumulative_macs"] == summary_full["cumulative_macs"]

    # Tier Budgets
    tier_budgets_dict = {
        k: {
            "parameter_range": v.parameter_range,
            "max_context_tokens": v.max_context_tokens,
            "max_rss_mb": v.max_rss_bytes // (1024 * 1024),
            "max_runtime_seconds": v.max_runtime_seconds,
        }
        for k, v in TIER_BUDGETS.items()
    }

    payload: dict[str, Any] = {
        "chapter": "0051-resumable-evaluator",
        "gate": "R11",
        "status": "PASSED",
        "claim_level": "functional/execution-envelope",
        "resumption_benchmark": {
            "prompt_length": len(prompt),
            "total_layers": 4,
            "interrupted_at_layer": 1,
            "layers_resumed": summary_resumed["layers_resumed"],
            "layers_computed": summary_resumed["layers_computed"],
            "max_logit_abs_error": max_diff,
            "cumulative_macs_full": summary_full["cumulative_macs"],
            "cumulative_macs_resumed": summary_resumed["cumulative_macs"],
            "ledger_idempotency_verified": True,
        },
        "tier_budgets": tier_budgets_dict,
    }

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    with open(RESULT_PATH, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)

    return payload


def main() -> None:
    results = run_resumable_extract()
    b = results["resumption_benchmark"]
    print("=" * 80)
    print("CHAPTER 0051: RESUMABLE MODEL EVALUATOR (GATE R11 EXIT)")
    print("=" * 80)
    print(f"Status: {results['status']} | Claim Level: {results['claim_level']}\n")
    print(f"Total Layers:          {b['total_layers']}")
    print(f"Interrupted At:        Layer {b['interrupted_at_layer']}")
    print(f"Resumed From Disk:     {b['layers_resumed']} layers")
    print(f"Computed on Resume:    {b['layers_computed']} layers")
    print(f"Max Logit Error:       {b['max_logit_abs_error']:.3e} (Exact Match)")
    print(f"Ledger Idempotency:    {b['ledger_idempotency_verified']} (0 double counting)\n")
    print("Workload Ladder Resource Envelopes:")
    print(f"{'Tier':<6} | {'Params':<12} | {'Context':<10} | {'Max RSS (MB)':<14} | {'Max Time (s)':<12}")
    print("-" * 65)
    for t_name, tb in results["tier_budgets"].items():
        print(
            f"{t_name:<6} | {tb['parameter_range']:<12} | {tb['max_context_tokens']:<10} | "
            f"{tb['max_rss_mb']:<14,d} | {tb['max_runtime_seconds']:<12.1f}"
        )
    print("=" * 80)
    print(f"Extracted artifact saved to: {RESULT_PATH}\n")


if __name__ == "__main__":
    main()
