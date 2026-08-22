from analog_llm.model_manifest import ModelManifest
from analog_llm.physical_ledger import (
    PhysicalLedgerConfig,
    compute_tier_physical_ledger,
)


def _build_hand_manifest() -> ModelManifest:
    """Hand-computable 2-layer reference manifest."""
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


def test_hand_computable_physical_ledger() -> None:
    manifest = _build_hand_manifest()
    cfg = PhysicalLedgerConfig()
    metrics = compute_tier_physical_ledger(
        manifest,
        batch_size=1,
        context_length=16,
        config=cfg,
        model_name="hand_2layer",
    )

    # Basic physical sanity assertions
    assert metrics.ttft_ms > 0.0
    assert metrics.decode_tokens_per_second > 0.0
    assert metrics.decode_energy_per_token_uj > 0.0
    assert metrics.active_power_w > 0.0
    assert metrics.die_count == 1
    assert metrics.thermal_classification in ("PASS_AIR_COOLED", "PASS_LIQUID_COOLED")

    # Subsystem energy checks
    breakdown = metrics.decode_breakdown
    assert breakdown.analog_mvm_uj > 0.0
    assert breakdown.adc_dac_conversion_uj > 0.0
    assert breakdown.sram_and_noc_uj > 0.0
    assert breakdown.total_energy_uj == (
        breakdown.analog_mvm_uj
        + breakdown.adc_dac_conversion_uj
        + breakdown.sram_and_noc_uj
        + breakdown.inter_die_ucie_uj
        + breakdown.package_hbm_uj
        + breakdown.digital_attention_uj
    )


def test_tier_scaling_parametric_ledger() -> None:
    # 1. T0 Model (124M)
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
    t0_metrics = compute_tier_physical_ledger(t0_manifest, batch_size=1, context_length=512, model_name="t0_124m")
    assert t0_metrics.die_count == 1
    assert t0_metrics.thermal_classification == "PASS_AIR_COOLED"
    assert t0_metrics.decode_tokens_per_second > 100.0  # Stationary crossbar decode throughput

    # 2. T1 Model (1.1B)
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
    t1_metrics = compute_tier_physical_ledger(t1_manifest, batch_size=1, context_length=2048, model_name="t1_1.1b")
    assert t1_metrics.die_count == 11
    assert t1_metrics.total_silicon_area_mm2 > 3000.0
    assert t1_metrics.decode_breakdown.inter_die_ucie_uj > 0.0
