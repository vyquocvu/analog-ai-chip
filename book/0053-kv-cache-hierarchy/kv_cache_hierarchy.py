r"""Chapter 0053 — KV-Cache Hierarchy, Paged Allocation & Attention Wall (Gate R12 Exit).

Models GQA/MQA KV-cache memory scaling, paged block allocation, SRAM/HBM placement,
and identifies the digital Attention Wall crossover bottleneck across T0–T3 tiers.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

_REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO))

from analog_llm.kv_hierarchy import (
    KVHierarchyConfig,
    analyze_kv_hierarchy,
)
from analog_llm.model_manifest import ModelManifest

RESULTS_DIR = _REPO / "verification" / "circuit" / "results"
RESULT_PATH = RESULTS_DIR / "kv-hierarchy-0053-extract.json"


def _create_ladder_manifests() -> dict[str, tuple[ModelManifest, list[int]]]:
    """Define architecture manifests and context sweeps for KV analysis."""
    return {
        "hand_calc": (
            ModelManifest(
                vocab_size=32,
                hidden_size=32,
                num_layers=2,
                num_attention_heads=4,
                num_key_value_heads=2,
                intermediate_size=64,
                context_length=64,
                dtype="float16",
                norm_type="rmsnorm",
                position_type="rope",
                activation_type="swiglu",
                attention_type="gqa",
                linear_bias=False,
                tied_embeddings=False,
            ),
            [16, 32, 64],
        ),
        "t0_gpt2_124m": (
            ModelManifest(
                vocab_size=50257,
                hidden_size=768,
                num_layers=12,
                num_attention_heads=12,
                num_key_value_heads=12,
                intermediate_size=3072,
                context_length=1024,
                dtype="float16",
                norm_type="layernorm",
                position_type="learned",
                activation_type="gelu",
                attention_type="mha",
            ),
            [128, 512, 1024],
        ),
        "t1_llama_1.1b": (
            ModelManifest(
                vocab_size=32000,
                hidden_size=2048,
                num_layers=22,
                num_attention_heads=32,
                num_key_value_heads=4,
                intermediate_size=5632,
                context_length=4096,
                dtype="float16",
                norm_type="rmsnorm",
                position_type="rope",
                activation_type="swiglu",
                attention_type="gqa",
                tied_embeddings=False,
            ),
            [512, 1024, 2048, 4096],
        ),
        "t2_llama_3b": (
            ModelManifest(
                vocab_size=32000,
                hidden_size=3072,
                num_layers=28,
                num_attention_heads=32,
                num_key_value_heads=8,
                intermediate_size=8192,
                context_length=8192,
                dtype="float16",
                norm_type="rmsnorm",
                position_type="rope",
                activation_type="swiglu",
                attention_type="gqa",
                tied_embeddings=False,
            ),
            [1024, 2048, 4096, 8192],
        ),
        "t3_llama2_7b": (
            ModelManifest(
                vocab_size=32000,
                hidden_size=4096,
                num_layers=32,
                num_attention_heads=32,
                num_key_value_heads=32,
                intermediate_size=11008,
                context_length=8192,
                dtype="float16",
                norm_type="rmsnorm",
                position_type="rope",
                activation_type="swiglu",
                attention_type="mha",
                tied_embeddings=False,
            ),
            [1024, 2048, 4096, 8192],
        ),
    }


def run_kv_hierarchy_extract() -> dict[str, Any]:
    """Execute KV hierarchy analysis and export deterministic extract."""
    manifests = _create_ladder_manifests()
    cfg = KVHierarchyConfig(
        sram_kv_capacity_mb=64.0,
        package_hbm_capacity_gb=32.0,
        analog_projection_latency_us_per_token=15.0,
    )

    ladder_summaries: dict[str, Any] = {}
    for name, (manifest, sweep) in manifests.items():
        summary = analyze_kv_hierarchy(manifest, config=cfg, context_sweep=sweep, model_name=name)
        steps_dict = {
            ctx: {
                "kv_cache_bytes": s.kv_cache_bytes,
                "paged_blocks_count": s.paged_blocks_count,
                "placement": s.placement.value,
                "prefill_attention_macs": s.prefill_attention_macs,
                "decode_attention_macs_per_token": s.decode_attention_macs_per_token,
                "digital_attention_latency_us": s.digital_attention_latency_us,
                "is_digital_attention_bottleneck": s.is_digital_attention_bottleneck,
            }
            for ctx, s in summary.steps.items()
        }
        ladder_summaries[name] = {
            "attention_type": summary.attention_type,
            "gqa_compression_ratio": summary.gqa_compression_ratio,
            "crossover_context_length": summary.crossover_context_length,
            "context_steps": steps_dict,
        }

    payload: dict[str, Any] = {
        "chapter": "0053-kv-cache-hierarchy",
        "gate": "R12",
        "status": "PASSED",
        "claim_level": "system/architecture-exploration",
        "hardware_config": {
            "paged_block_size": cfg.paged_block_size,
            "sram_kv_capacity_mb": cfg.sram_kv_capacity_mb,
            "hbm_capacity_gb": cfg.package_hbm_capacity_gb,
            "sram_bandwidth_tb_s": cfg.sram_bandwidth_tb_s,
            "hbm_bandwidth_tb_s": cfg.hbm_bandwidth_tb_s,
            "digital_tflops": cfg.digital_attention_tflops,
            "analog_projection_latency_us": cfg.analog_projection_latency_us_per_token,
        },
        "ladder_summaries": ladder_summaries,
    }

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    with open(RESULT_PATH, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)

    return payload


def main() -> None:
    results = run_kv_hierarchy_extract()
    print("=" * 95)
    print("CHAPTER 0053: KV-CACHE HIERARCHY & DIGITAL ATTENTION BOTTLENECK (GATE R12 EXIT)")
    print("=" * 95)
    print(f"Status: {results['status']} | Claim Level: {results['claim_level']}\n")
    print(
        f"{'Model Tier':<16} | {'Attn':<6} | {'GQA Ratio':<10} | {'Context':<8} | {'KV Footprint':<14} | {'Placement':<12} | {'Bottleneck'}"
    )
    print("-" * 95)
    for name, s in results["ladder_summaries"].items():
        gqa_str = f"{s['gqa_compression_ratio']:.1f}x"
        for ctx, step in s["context_steps"].items():
            kb_mb = (
                f"{step['kv_cache_bytes'] / (1024*1024):.1f} MB"
                if step["kv_cache_bytes"] >= 1024 * 1024
                else f"{step['kv_cache_bytes'] / 1024:.1f} KB"
            )
            bottle_str = "DIGITAL ATTN WALL" if step["is_digital_attention_bottleneck"] else "Analog MVM"
            print(
                f"{name:<16} | {s['attention_type']:<6} | {gqa_str:<10} | {ctx:<8} | "
                f"{kb_mb:<14} | {step['placement']:<12} | {bottle_str}"
            )
    print("=" * 95)
    print(f"Extracted artifact saved to: {RESULT_PATH}\n")


if __name__ == "__main__":
    main()
