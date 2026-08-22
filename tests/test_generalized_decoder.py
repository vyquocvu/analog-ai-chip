from typing import Any

import numpy as np
import pytest

from analog_llm.accelerator import Accelerator
from analog_llm.generalized_decoder import GeneralizedDecoder
from analog_llm.model_manifest import ModelManifest
from analog_llm.tile import CrossbarTile
from analog_llm.transformer import TinyGPT, TinyGPTConfig


def _tiny_manifest(**overrides: Any) -> ModelManifest:
    defaults: dict[str, Any] = {
        "vocab_size": 5,
        "hidden_size": 4,
        "num_layers": 1,
        "num_attention_heads": 2,
        "num_key_value_heads": 1,
        "intermediate_size": 6,
        "context_length": 3,
        "dtype": "float16",
        "norm_type": "rmsnorm",
        "position_type": "rope",
        "activation_type": "swiglu",
        "attention_type": "mqa",
        "linear_bias": False,
        "tied_embeddings": True,
    }
    defaults.update(overrides)
    return ModelManifest(**defaults)


def test_tiny_hand_calc_forward_shape_and_execution() -> None:
    manifest = _tiny_manifest()
    decoder = GeneralizedDecoder(manifest)
    tokens = [0, 1, 2]
    logits = decoder.forward_logits(tokens)
    assert logits.shape == (3, 5)


def test_llama_style_gqa_rmsnorm_rope_swiglu_full_context_matches_kv_cache() -> None:
    manifest = ModelManifest(
        vocab_size=32,
        hidden_size=16,
        num_layers=2,
        num_attention_heads=4,
        num_key_value_heads=2,
        intermediate_size=32,
        context_length=8,
        dtype="float32",
        norm_type="rmsnorm",
        position_type="rope",
        activation_type="swiglu",
        attention_type="gqa",
        linear_bias=False,
        tied_embeddings=False,
    )
    decoder = GeneralizedDecoder(manifest)
    prompt = [3, 7, 12, 1]

    # Full context forward
    full_logits = decoder.forward_logits(prompt)

    # Step-by-step KV cache forward
    cache = decoder._init_kv_cache()
    step_logits = []
    for pos, tok in enumerate(prompt):
        step_logits.append(decoder._forward_step(tok, pos, cache))
    step_logits_arr = np.stack(step_logits)

    np.testing.assert_allclose(full_logits, step_logits_arr, atol=1e-12)

    # Autoregressive generation parity
    gen_full = decoder.generate(prompt, max_new=4, greedy=True)
    gen_cache = decoder.generate_kvcache(prompt, max_new=4, greedy=True)
    assert gen_full == gen_cache


def test_mqa_style_kv_cache_parity() -> None:
    manifest = ModelManifest(
        vocab_size=16,
        hidden_size=8,
        num_layers=2,
        num_attention_heads=4,
        num_key_value_heads=1,
        intermediate_size=16,
        context_length=6,
        dtype="float32",
        norm_type="rmsnorm",
        position_type="rope",
        activation_type="swiglu",
        attention_type="mqa",
        linear_bias=False,
        tied_embeddings=True,
    )
    decoder = GeneralizedDecoder(manifest)
    prompt = [1, 5, 2]

    full_logits = decoder.forward_logits(prompt)
    cache = decoder._init_kv_cache()
    step_logits = [decoder._forward_step(tok, pos, cache) for pos, tok in enumerate(prompt)]

    np.testing.assert_allclose(full_logits, np.stack(step_logits), atol=1e-12)


def test_gpt2_architecture_parity_with_tinygpt() -> None:
    # 1. Configure matching TinyGPT and GeneralizedDecoder
    cfg = TinyGPTConfig(
        vocab_size=16,
        n_embd=8,
        n_layer=2,
        n_head=2,
        block_size=6,
        ffn_mult=2,
        seed=123,
    )
    tiny = TinyGPT(cfg)

    manifest = ModelManifest(
        vocab_size=16,
        hidden_size=8,
        num_layers=2,
        num_attention_heads=2,
        num_key_value_heads=2,
        intermediate_size=16,
        context_length=6,
        dtype="float32",
        norm_type="layernorm",
        position_type="learned",
        activation_type="gelu",
        attention_type="mha",
        linear_bias=True,
        tied_embeddings=False,
    )

    # 2. Map TinyGPT weights into canonical GeneralizedDecoder layout
    weights: dict[str, np.ndarray] = {
        "token_embedding.weight": tiny.weights["tok_emb"],
        "position_embedding.weight": tiny.weights["pos_emb"],
        "final_norm.weight": tiny.weights["lnf"],
        "final_norm.bias": tiny.weights["lnfb"],
        "lm_head.weight": tiny.weights["head"],
    }
    for i in range(cfg.n_layer):
        p = f"{i}."
        gp = f"layers.{i}."
        weights[f"{gp}attention_norm.weight"] = tiny.weights[p + "ln1"]
        weights[f"{gp}attention_norm.bias"] = tiny.weights[p + "ln1b"]

        wqkv = tiny.weights[p + "wqkv"]
        wqkvb = tiny.weights[p + "wqkvb"]
        C = cfg.n_embd
        weights[f"{gp}attention.q_proj.weight"] = wqkv[:C]
        weights[f"{gp}attention.q_proj.bias"] = wqkvb[:C]
        weights[f"{gp}attention.k_proj.weight"] = wqkv[C : 2 * C]
        weights[f"{gp}attention.k_proj.bias"] = wqkvb[C : 2 * C]
        weights[f"{gp}attention.v_proj.weight"] = wqkv[2 * C :]
        weights[f"{gp}attention.v_proj.bias"] = wqkvb[2 * C :]

        weights[f"{gp}attention.out_proj.weight"] = tiny.weights[p + "wo"]
        weights[f"{gp}attention.out_proj.bias"] = tiny.weights[p + "wob"]

        weights[f"{gp}mlp_norm.weight"] = tiny.weights[p + "ln2"]
        weights[f"{gp}mlp_norm.bias"] = tiny.weights[p + "ln2b"]
        weights[f"{gp}mlp.up_proj.weight"] = tiny.weights[p + "wup"]
        weights[f"{gp}mlp.up_proj.bias"] = tiny.weights[p + "wupb"]
        weights[f"{gp}mlp.down_proj.weight"] = tiny.weights[p + "wdown"]
        weights[f"{gp}mlp.down_proj.bias"] = tiny.weights[p + "wdownb"]

    decoder = GeneralizedDecoder(manifest, weights=weights)

    # 3. Test forward logit exact parity
    tokens = np.array([2, 5, 1, 4])
    tiny_logits = tiny.forward_logits(tokens)
    gen_logits = decoder.forward_logits(tokens)
    np.testing.assert_allclose(gen_logits, tiny_logits, atol=1e-12)

    # 4. Test generation parity
    tiny_gen = tiny.generate(tokens, max_new=2, greedy=True).tolist()
    gen_gen = decoder.generate(tokens, max_new=2, greedy=True)
    assert gen_gen == tiny_gen

    tiny_cache_gen = tiny.generate_kvcache(tokens, max_new=2, greedy=True).tolist()
    gen_cache_gen = decoder.generate_kvcache(tokens, max_new=2, greedy=True)
    assert gen_cache_gen == tiny_cache_gen


def test_analog_accelerator_routing() -> None:
    manifest = ModelManifest(
        vocab_size=8,
        hidden_size=8,
        num_layers=1,
        num_attention_heads=2,
        num_key_value_heads=2,
        intermediate_size=16,
        context_length=4,
        dtype="float32",
        norm_type="layernorm",
        position_type="learned",
        activation_type="gelu",
        attention_type="mha",
        linear_bias=True,
        tied_embeddings=True,
    )
    decoder = GeneralizedDecoder(manifest)
    acc = Accelerator(
        lambda: CrossbarTile(8, 8, g_bits=8, dac_bits=8, adc_bits=8, vout_max=4.0),
        tile_rows=8,
        tile_cols=8,
        tile_count=8,
    )
    logits = decoder.forward_logits([0, 1], accelerator=acc)
    assert logits.shape == (2, 8)
    assert acc.macs > 0


def test_generalized_decoder_fails_closed() -> None:
    manifest = _tiny_manifest(context_length=3)
    decoder = GeneralizedDecoder(manifest)

    # Context overflow
    with pytest.raises(ValueError, match="sequence length must be in"):
        decoder.forward_logits([0, 1, 2, 3])

    with pytest.raises(ValueError, match="position 3 exceeds context_length 3"):
        decoder._forward_step(0, 3, decoder._init_kv_cache())
