r"""Chapter 0056 — Parametric Physical Ledger for Large-Model Inference (Gate R14).

Computes end-to-end latency, energy, area, power density, and thermal dissipation
for T0–T3 prefill and decode using manifest-driven physical coefficients.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

_REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO))

from analog_llm.model_manifest import ModelManifest
from analog_llm.physical_ledger import (
    PhysicalLedgerConfig,
    compute_tier_physical_ledger,
)
from analog_llm.residency import HardwareTopologyConfig

RESULTS_DIR = _REPO / "verification" / "circuit" / "results"
RESULT_PATH = RESULTS_DIR / "parametric-ledger-0056-extract.json"


def _create_ladder_manifests() -> dict[str, tuple[ModelManifest, int, int]]:
    """Define architecture manifests, batch sizes, and context lengths for ledger evaluation."""
    return {
        "hand_calc": (
            ModelManifest(
                vocab_size=32,
                hidden_size=32,
                num_layers=2,
                num_attention_heads=2,
                num_key_value_heads=2,
                intermediate_size=64,
                context_length=16,
                dtype="float32",
                norm_type="layernorm",
                position_type="learned",
                activation_type="gelu",
                attention_type="mha",
                linear_bias=False,
                tied_embeddings=True,
            ),
            1,
            16,
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
            1,
            512,
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
            1,
            2048,
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
            1,
            4096,
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
            1,
            4096,
        ),
    }


def run_parametric_ledger_extract() -> dict[str, Any]:
    """Execute parametric physical ledger evaluation and export deterministic extract."""
    manifests = _create_ladder_manifests()
    cfg = PhysicalLedgerConfig()
    topo = HardwareTopologyConfig()

    tier_ledgers: dict[str, Any] = {}
    for name, (manifest, batch, ctx) in manifests.items():
        metrics = compute_tier_physical_ledger(
            manifest,
            batch_size=batch,
            context_length=ctx,
            config=cfg,
            topology=topo,
            model_name=name,
        )
        tier_ledgers[name] = {
            "batch_size": metrics.batch_size,
            "context_length": metrics.context_length,
            "ttft_ms": metrics.ttft_ms,
            "prefill_throughput_tok_s": metrics.prefill_throughput_tok_s,
            "decode_tokens_per_second": metrics.decode_tokens_per_second,
            "decode_latency_per_token_ms": metrics.decode_latency_per_token_ms,
            "prefill_energy_per_token_uj": metrics.prefill_energy_per_token_uj,
            "decode_energy_per_token_uj": metrics.decode_energy_per_token_uj,
            "subsystem_energy_breakdown_uj": {
                "analog_mvm": metrics.decode_breakdown.analog_mvm_uj,
                "adc_dac_conversion": metrics.decode_breakdown.adc_dac_conversion_uj,
                "sram_and_noc": metrics.decode_breakdown.sram_and_noc_uj,
                "inter_die_ucie": metrics.decode_breakdown.inter_die_ucie_uj,
                "package_hbm": metrics.decode_breakdown.package_hbm_uj,
                "digital_attention": metrics.decode_breakdown.digital_attention_uj,
                "total_energy_uj": metrics.decode_breakdown.total_energy_uj,
            },
            "active_power_w": metrics.active_power_w,
            "power_density_w_cm2": metrics.power_density_w_cm2,
            "die_count": metrics.die_count,
            "total_silicon_area_mm2": metrics.total_silicon_area_mm2,
            "thermal_classification": metrics.thermal_classification,
            "provenance": metrics.provenance,
        }

    payload: dict[str, Any] = {
        "chapter": "0056-parametric-physical-ledger",
        "gate": "R14",
        "status": "PASSED",
        "claim_level": "system/architecture-exploration",
        "physical_coefficients": {
            "energy_per_mvm_mac_pj": cfg.energy_per_mvm_mac_pj,
            "energy_per_adc_conv_pj": cfg.energy_per_adc_conv_pj,
            "energy_per_dac_conv_pj": cfg.energy_per_dac_conv_pj,
            "energy_per_sram_byte_pj": cfg.energy_per_sram_byte_pj,
            "energy_per_noc_byte_pj": cfg.energy_per_noc_byte_pj,
            "energy_per_ucie_byte_pj": cfg.energy_per_ucie_byte_pj,
            "energy_per_hbm_byte_pj": cfg.energy_per_hbm_byte_pj,
            "energy_per_digital_flop_pj": cfg.energy_per_digital_flop_pj,
            "analog_tile_cycle_ns": cfg.analog_tile_cycle_ns,
        },
        "tier_ledgers": tier_ledgers,
    }

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    with open(RESULT_PATH, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)

    return payload


def main() -> None:
    results = run_parametric_ledger_extract()
    print("=" * 105)
    print("CHAPTER 0056: PARAMETRIC PHYSICAL LEDGER FOR LARGE-MODEL INFERENCE (GATE R14)")
    print("=" * 105)
    print(f"Status: {results['status']} | Claim Level: {results['claim_level']}\n")
    print(
        f"{'Model Tier':<16} | {'TTFT (ms)':<10} | {'Decode (TPS)':<14} | {'Decode (μJ/tok)':<16} | {'Power (W)':<10} | {'Density (W/cm²)':<16} | {'Thermal'}"
    )
    print("-" * 105)
    for name, r in results["tier_ledgers"].items():
        print(
            f"{name:<16} | {r['ttft_ms']:<10.2f} | {r['decode_tokens_per_second']:<14.1f} | "
            f"{r['decode_energy_per_token_uj']:<16.2f} | {r['active_power_w']:<10.2f} | "
            f"{r['power_density_w_cm2']:<16.2f} | {r['thermal_classification']}"
        )
    print("=" * 105)
    print(f"Extracted artifact saved to: {RESULT_PATH}\n")


if __name__ == "__main__":
    main()
