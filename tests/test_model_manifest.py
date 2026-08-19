import pytest

from analog_llm.model_manifest import ModelManifest


def _tiny_manifest(**overrides) -> ModelManifest:
    values = {
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
    values.update(overrides)
    return ModelManifest(**values)


def test_tiny_mqa_manifest_has_hand_computable_inventory() -> None:
    # H=4, I=6, two query heads and one KV head (D=2).
    # Stored parameters: embeddings 20 + norms 12 + seven matrices 120 = 152.
    manifest = _tiny_manifest()
    specs = manifest.tensor_specs()

    assert manifest.head_dimension == 2
    assert specs["layers.0.attention.k_proj.weight"].shape == (2, 4)
    assert specs["layers.0.mlp.gate_proj.weight"].shape == (6, 4)
    assert "position_embedding.weight" not in specs  # RoPE has no learned table.
    assert "lm_head.weight" not in specs  # tied to token embedding storage.
    assert manifest.parameter_count == 152
    assert manifest.per_layer_projection_macs == 120
    assert manifest.kv_cache_bytes() == 24  # 3 tokens × K/V × 2 values × 2 B.


def test_tensor_inventory_validation_accepts_exact_shapes_and_rejects_missing() -> None:
    manifest = _tiny_manifest()
    inventory = {name: spec.shape for name, spec in manifest.tensor_specs().items()}
    manifest.validate_tensors(inventory)

    del inventory["layers.0.attention.q_proj.weight"]
    with pytest.raises(ValueError, match="missing=.*q_proj"):
        manifest.validate_tensors(inventory)


@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        ({"hidden_size": 5}, "divisible"),
        ({"attention_type": "mha"}, "requires num_key_value_heads=2"),
        ({"position_type": "alibi"}, "unsupported position_type"),
        ({"tensor_layout": "in_out"}, "out_in"),
    ],
)
def test_manifest_fails_closed_on_inconsistent_or_ambiguous_semantics(
    overrides, message
) -> None:
    with pytest.raises(ValueError, match=message):
        _tiny_manifest(**overrides)


def test_kv_cache_rejects_positions_beyond_context() -> None:
    with pytest.raises(ValueError, match=r"\[0, 3\]"):
        _tiny_manifest().kv_cache_bytes(4)
