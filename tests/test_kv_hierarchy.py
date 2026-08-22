from analog_llm.kv_hierarchy import (
    KVHierarchyConfig,
    analyze_kv_hierarchy,
    calculate_kv_cache_bytes,
)
from analog_llm.model_manifest import ModelManifest


def _build_hand_gqa_manifest() -> ModelManifest:
    return ModelManifest(
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
    )


def test_hand_computable_kv_cache_sizing_and_gqa_reduction() -> None:
    manifest = _build_hand_gqa_manifest()
    # Context length = 16 tokens, dtype = 2 bytes (FP16)
    # Calculation: 2 * layers(2) * num_kv_heads(2) * head_dim(8) * tokens(16) * dtype(2) = 2048 bytes
    bytes_calc = calculate_kv_cache_bytes(manifest, context_length=16, dtype_bytes=2)
    assert bytes_calc == 2048

    summary = analyze_kv_hierarchy(manifest, context_sweep=(16, 32))
    assert summary.gqa_compression_ratio == 2.0  # 4 Q heads / 2 KV heads
    assert summary.steps[16].kv_cache_bytes == 2048
    assert summary.steps[16].paged_blocks_count == 1  # 16 tokens / 16 block_size


def test_prefill_vs_decode_mac_accounting() -> None:
    manifest = _build_hand_gqa_manifest()
    summary = analyze_kv_hierarchy(manifest, context_sweep=(16,))
    step = summary.steps[16]

    # Prefill: 2 * (16^2) * 32(hidden) * 2(layers) = 2 * 256 * 32 * 2 = 32,768 MACs
    assert step.prefill_attention_macs == 32768
    # Decode step 16: 2 * 16 * 32 * 2 = 2,048 MACs
    assert step.decode_attention_macs_per_token == 2048


def test_attention_wall_crossover_detection() -> None:
    # 7B model manifest with 8K context
    t3_manifest = ModelManifest(
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
    )
    # SRAM config to test transition from SRAM to HBM and bottleneck crossover
    cfg = KVHierarchyConfig(
        sram_kv_capacity_mb=128.0,  # 128 MB SRAM
        analog_projection_latency_us_per_token=25.0,  # 32 layers x ~0.8 us
    )
    summary = analyze_kv_hierarchy(t3_manifest, config=cfg, context_sweep=(128, 512, 2048, 8192))

    assert summary.crossover_context_length is not None
    assert summary.steps[128].is_digital_attention_bottleneck is False
    assert summary.steps[8192].is_digital_attention_bottleneck is True
