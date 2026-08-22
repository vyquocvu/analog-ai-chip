from analog_llm.model_manifest import ModelManifest
from analog_llm.residency import (
    HardwareTopologyConfig,
    analyze_model_residency,
)


def _build_hand_manifest() -> ModelManifest:
    """Hand-computable 2-layer model: hidden 32, intermediate 64, heads 2."""
    return ModelManifest(
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
    )


def test_hand_computable_residency_and_cell_count() -> None:
    manifest = _build_hand_manifest()
    topo = HardwareTopologyConfig(tile_rows=16, tile_cols=16, cells_per_weight=2)

    summary = analyze_model_residency(manifest, topology=topo, model_name="hand_2layer")

    # Hand calculation:
    # Layer attention: Q(32x32)=4, K(32x32)=4, V(32x32)=4, O(32x32)=4 -> 16 tiles
    # Layer MLP: Up(64x32)=8, Down(32x64)=8 -> 16 tiles
    # Total per layer = 32 tiles. 2 layers = 64 tiles.
    assert summary.total_physical_tiles == 64
    assert summary.total_physical_cells == 64 * 256 * 2  # 32,768 cells
    assert summary.usable_cell_utilization_pct == 100.0
    assert summary.is_single_die_resident is True
    assert summary.chiplets_required_for_full_residency == 1


def test_tier_scaling_residency_and_feasibility() -> None:
    # 1. T0 Model (~124M parameters)
    t0_manifest = ModelManifest(
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
    )
    t0_summary = analyze_model_residency(t0_manifest, model_name="t0_gpt2")
    assert t0_summary.is_single_die_resident is True
    assert t0_summary.schedules["fully_resident"].is_physically_viable is True

    # 2. T1 Model (~1.1B parameters)
    t1_manifest = ModelManifest(
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
    )
    t1_summary = analyze_model_residency(t1_manifest, model_name="t1_1.1b")
    assert t1_summary.chiplets_required_for_full_residency <= 12
    assert t1_summary.is_multi_die_package_resident is True

    # 3. T3 Model (7B parameters)
    t3_manifest = ModelManifest(
        vocab_size=32000,
        hidden_size=4096,
        num_layers=32,
        num_attention_heads=32,
        num_key_value_heads=32,
        intermediate_size=11008,
        context_length=4096,
        dtype="float16",
        norm_type="rmsnorm",
        position_type="rope",
        activation_type="swiglu",
        attention_type="mha",
        tied_embeddings=False,
    )
    t3_summary = analyze_model_residency(t3_manifest, model_name="t3_7b")
    assert t3_summary.chiplets_required_for_full_residency > 8
    # Exceeds single 8-chiplet package for stationary full residency
    assert t3_summary.schedules["fully_resident"].is_physically_viable is False
    # But layer-by-layer reload is viable
    assert t3_summary.schedules["layer_resident"].is_physically_viable is True
