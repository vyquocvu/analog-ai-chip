"""TDD contract for R10 / WP10.1 architecture-neutral model manifests."""

from __future__ import annotations

import pytest

from analog_llm.model_manifest import ModelManifest, TensorDescriptor


def _tiny_gpt2_style() -> ModelManifest:
    return ModelManifest(
        schema_version="1.0",
        architecture="decoder-only",
        vocab_size=10,
        hidden_size=4,
        num_layers=2,
        num_attention_heads=2,
        num_key_value_heads=2,
        head_dim=2,
        intermediate_size=8,
        max_context=8,
        dtype="float32",
        tie_embeddings=True,
        norm_type="layernorm",
        norm_bias=True,
        position_type="learned",
        activation="gelu",
        linear_bias=True,
    )


def test_tiny_manifest_has_hand_computable_shapes_parameters_macs_and_kv() -> None:
    manifest = _tiny_gpt2_style()

    specs = manifest.expected_tensors()
    assert specs["token_embedding.weight"].shape == (10, 4)
    assert specs["position_embedding.weight"].shape == (8, 4)
    assert specs["layers.0.attn.q.weight"].shape == (4, 4)
    assert specs["layers.0.attn.k.weight"].shape == (4, 4)
    assert specs["layers.0.mlp.up.weight"].shape == (8, 4)
    assert specs["layers.0.mlp.down.weight"].shape == (4, 8)
    assert "lm_head.weight" not in specs  # tied to token_embedding.weight

    # Hand count:
    # embeddings 10*4 + 8*4 = 72
    # each layer: attention 80 + MLP 76 + two LayerNorms 16 = 172
    # two layers = 344; final LayerNorm = 8; total = 424.
    assert manifest.parameter_count() == 424

    # One-token dense projection MACs per layer:
    # q/k/v/o = 4*4*4 = 64; MLP up/down = 4*8 + 8*4 = 64.
    assert manifest.per_layer_linear_macs() == 128

    # K and V: 2 tensors * 2 KV heads * head_dim 2 * fp32 4 bytes.
    assert manifest.kv_bytes_per_token_per_layer() == 32
    assert manifest.kv_cache_bytes(tokens=8) == 2 * 8 * 32


def test_llama_style_semantics_are_not_coerced_to_gpt2() -> None:
    manifest = ModelManifest(
        schema_version="1.0",
        architecture="decoder-only",
        vocab_size=32,
        hidden_size=8,
        num_layers=1,
        num_attention_heads=4,
        num_key_value_heads=2,
        head_dim=2,
        intermediate_size=12,
        max_context=16,
        dtype="float16",
        tie_embeddings=False,
        norm_type="rmsnorm",
        norm_bias=False,
        position_type="rope",
        activation="swiglu",
        linear_bias=False,
    )

    specs = manifest.expected_tensors()
    assert "position_embedding.weight" not in specs
    assert specs["layers.0.attn.k.weight"].shape == (4, 8)  # GQA: 2 KV heads * dim 2
    assert specs["layers.0.attn.v.weight"].shape == (4, 8)
    assert specs["layers.0.mlp.gate.weight"].shape == (12, 8)
    assert specs["layers.0.mlp.up.weight"].shape == (12, 8)
    assert specs["lm_head.weight"].shape == (32, 8)
    assert not any(name.endswith(".bias") for name in specs)
    assert manifest.kv_bytes_per_token_per_layer() == 2 * 2 * 2 * 2


def test_tensor_inventory_requires_exact_shapes_and_explicit_layout() -> None:
    manifest = _tiny_gpt2_style()
    expected = manifest.expected_tensors()
    inventory = {
        name: TensorDescriptor(shape=spec.shape, layout=spec.layout)
        for name, spec in expected.items()
    }
    manifest.validate_tensor_inventory(inventory)

    missing = dict(inventory)
    missing.pop("layers.0.attn.q.weight")
    with pytest.raises(ValueError, match="missing tensors"):
        manifest.validate_tensor_inventory(missing)

    wrong_shape = dict(inventory)
    wrong_shape["layers.0.attn.q.weight"] = TensorDescriptor((4, 3), "out_in")
    with pytest.raises(ValueError, match="shape"):
        manifest.validate_tensor_inventory(wrong_shape)

    ambiguous = dict(inventory)
    ambiguous["layers.0.attn.q.weight"] = TensorDescriptor((4, 4), "unknown")
    with pytest.raises(ValueError, match="layout"):
        manifest.validate_tensor_inventory(ambiguous)


def test_manifest_fails_closed_on_unsupported_or_inconsistent_semantics() -> None:
    base = dict(
        schema_version="1.0",
        architecture="decoder-only",
        vocab_size=10,
        hidden_size=8,
        num_layers=1,
        num_attention_heads=4,
        num_key_value_heads=2,
        head_dim=2,
        intermediate_size=16,
        max_context=32,
        dtype="float32",
        tie_embeddings=True,
        norm_type="rmsnorm",
        norm_bias=False,
        position_type="rope",
        activation="swiglu",
        linear_bias=False,
    )

    with pytest.raises(ValueError, match="attention heads"):
        ModelManifest(**{**base, "num_attention_heads": 3})
    with pytest.raises(ValueError, match="head_dim"):
        ModelManifest(**{**base, "head_dim": 3})
    with pytest.raises(ValueError, match="num_key_value_heads"):
        ModelManifest(**{**base, "num_key_value_heads": 3})
    with pytest.raises(ValueError, match="norm_type"):
        ModelManifest(**{**base, "norm_type": "mysterynorm"})
    with pytest.raises(ValueError, match="position_type"):
        ModelManifest(**{**base, "position_type": "alibi"})
    with pytest.raises(ValueError, match="activation"):
        ModelManifest(**{**base, "activation": "relu"})
    with pytest.raises(ValueError, match="dtype"):
        ModelManifest(**{**base, "dtype": "float128"})


def test_manifest_round_trip_is_versioned_and_deterministic() -> None:
    manifest = _tiny_gpt2_style()
    encoded = manifest.to_dict()
    assert encoded["schema_version"] == "1.0"
    assert ModelManifest.from_dict(encoded) == manifest
