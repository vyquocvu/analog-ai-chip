r"""Chapter 0048 — Generalized Decoder Functional Reference (Gate R10, Scalable Models).

Executes and verifies the manifest-driven GeneralizedDecoder across diverse architectural
families (GPT-2 MHA, LLaMA GQA, Hand-Calc MQA) confirming strict mathematical parity,
KV-cache equivalence, and analog accelerator compatibility.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import numpy as np

_REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO))

from analog_llm.accelerator import Accelerator
from analog_llm.generalized_decoder import GeneralizedDecoder
from analog_llm.model_manifest import ModelManifest
from analog_llm.tile import CrossbarTile

RESULTS_DIR = _REPO / "verification" / "circuit" / "results"
RESULT_PATH = RESULTS_DIR / "generalized-decoder-0048-extract.json"


def get_benchmark_models() -> dict[str, ModelManifest]:
    """Define benchmark architectures for verification."""
    return {
        "hand_calc_mqa": ModelManifest(
            vocab_size=5,
            hidden_size=4,
            num_layers=1,
            num_attention_heads=2,
            num_key_value_heads=1,
            intermediate_size=6,
            context_length=3,
            dtype="float16",
            norm_type="rmsnorm",
            position_type="rope",
            activation_type="swiglu",
            attention_type="mqa",
            linear_bias=False,
            tied_embeddings=True,
        ),
        "gpt2_style_mha": ModelManifest(
            vocab_size=128,
            hidden_size=64,
            num_layers=2,
            num_attention_heads=4,
            num_key_value_heads=4,
            intermediate_size=256,
            context_length=16,
            dtype="float32",
            norm_type="layernorm",
            position_type="learned",
            activation_type="gelu",
            attention_type="mha",
            linear_bias=True,
            tied_embeddings=True,
        ),
        "llama_style_gqa": ModelManifest(
            vocab_size=128,
            hidden_size=64,
            num_layers=2,
            num_attention_heads=4,
            num_key_value_heads=2,
            intermediate_size=192,
            context_length=16,
            dtype="float32",
            norm_type="rmsnorm",
            position_type="rope",
            activation_type="swiglu",
            attention_type="gqa",
            linear_bias=False,
            tied_embeddings=False,
        ),
    }


def run_generalized_decoder_extract() -> dict[str, Any]:
    """Execute parity verification across benchmark architectures."""
    manifests = get_benchmark_models()
    model_reports: dict[str, Any] = {}

    for name, manifest in manifests.items():
        decoder = GeneralizedDecoder(manifest)
        seq_len = min(4, manifest.context_length)
        prompt = list(range(seq_len))

        # 1. Full context forward
        full_logits = decoder.forward_logits(prompt)

        # 2. Step-by-step KV cache forward
        cache = decoder._init_kv_cache()
        step_logits = []
        for pos, tok in enumerate(prompt):
            step_logits.append(decoder._forward_step(tok, pos, cache))
        step_logits_arr = np.stack(step_logits)

        # 3. Compute exact error delta
        max_abs_logit_err = float(np.max(np.abs(full_logits - step_logits_arr)))
        assert max_abs_logit_err < 1e-12, f"{name} KV cache parity failure"

        # 4. Generation parity
        max_new = 4 if manifest.context_length >= 8 else 1
        gen_full = decoder.generate(prompt, max_new=max_new, greedy=True)
        gen_cache = decoder.generate_kvcache(prompt, max_new=max_new, greedy=True)
        assert gen_full == gen_cache, f"{name} generation parity failure"

        model_reports[name] = {
            "norm_type": manifest.norm_type,
            "position_type": manifest.position_type,
            "activation_type": manifest.activation_type,
            "attention_type": manifest.attention_type,
            "parameter_count": manifest.parameter_count,
            "per_layer_projection_macs": manifest.per_layer_projection_macs,
            "kv_cache_full_bytes": manifest.kv_cache_bytes(),
            "max_abs_logit_error_vs_cache": max_abs_logit_err,
            "greedy_generation_parity": True,
            "generated_tokens": gen_cache,
        }

    # 5. Analog Accelerator Integration Check
    llama = manifests["llama_style_gqa"]
    llama_dec = GeneralizedDecoder(llama)
    acc = Accelerator(
        lambda: CrossbarTile(16, 16, g_bits=8, dac_bits=8, adc_bits=8, vout_max=4.0),
        tile_rows=16,
        tile_cols=16,
        tile_count=32,
    )
    analog_logits = llama_dec.forward_logits([0, 1, 2], accelerator=acc)
    analog_integration = {
        "status": "PASSED",
        "analog_macs_executed": acc.macs,
        "analog_tile_cycles": acc.tile_cycles,
        "output_shape": list(analog_logits.shape),
    }

    payload: dict[str, Any] = {
        "chapter": "0048-generalized-decoder",
        "gate": "R10",
        "status": "PASSED",
        "claim_level": "functional/software-reference",
        "model_reports": model_reports,
        "analog_accelerator_integration": analog_integration,
    }

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    with open(RESULT_PATH, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)

    return payload


def main() -> None:
    results = run_generalized_decoder_extract()
    print("=" * 80)
    print("CHAPTER 0048: GENERALIZED DECODER FUNCTIONAL REFERENCE (GATE R10)")
    print("=" * 80)
    print(f"Status: {results['status']} | Claim Level: {results['claim_level']}\n")
    print(
        f"{'Model Arch':<18} | {'Norm/Pos':<16} | {'Act/Attn':<16} | {'Params':<10} | {'KV Parity Error':<16}"
    )
    print("-" * 80)
    for name, r in results["model_reports"].items():
        norm_pos = f"{r['norm_type']}/{r['position_type']}"
        act_attn = f"{r['activation_type']}/{r['attention_type']}"
        print(
            f"{name:<18} | {norm_pos:<16} | {act_attn:<16} | {r['parameter_count']:<10,d} | "
            f"{r['max_abs_logit_error_vs_cache']:<16.3e}"
        )
    print("=" * 80)
    print(f"Analog MVM Execution: {results['analog_accelerator_integration']['analog_macs_executed']:,d} MACs executed")
    print(f"Extracted artifact saved to: {RESULT_PATH}\n")


if __name__ == "__main__":
    main()
