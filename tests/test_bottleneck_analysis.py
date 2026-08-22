from analog_llm.bottleneck_analysis import (
    LimitingResource,
    evaluate_bottleneck_and_pareto,
    identify_primary_bottleneck,
)
from analog_llm.model_manifest import ModelManifest


def _build_t0_manifest() -> ModelManifest:
    return ModelManifest(
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


def _build_t3_manifest() -> ModelManifest:
    return ModelManifest(
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


def test_bottleneck_identification() -> None:
    t0 = _build_t0_manifest()
    bn_t0, util_t0 = identify_primary_bottleneck(t0, context_length=64)
    assert bn_t0 == LimitingResource.ADC_AREA_BANDWIDTH_LIMIT
    assert util_t0["analog_mvm_pct"] + util_t0["adc_dac_conversion_pct"] > 50.0

    t3 = _build_t3_manifest()
    bn_t3, _util_t3 = identify_primary_bottleneck(t3, context_length=8192)
    # T3 either exceeds single package crossbar capacity or is bottlenecked by digital attention wall
    assert bn_t3 in (LimitingResource.CROSSBAR_CAPACITY_LIMIT, LimitingResource.DIGITAL_ATTENTION_COMPUTE_LIMIT)


def test_pareto_frontier_and_edp_optimization() -> None:
    t0 = _build_t0_manifest()
    report = evaluate_bottleneck_and_pareto(t0, context_length=512, model_name="t0_gpt2")

    assert len(report.pareto_points) > 0
    pareto_opt_points = [p for p in report.pareto_points if p.is_pareto_optimal]
    assert len(pareto_opt_points) >= 1

    # Optimal point must have minimal EDP
    all_edps = [p.energy_delay_product_pj_s for p in report.pareto_points]
    assert report.optimal_point.energy_delay_product_pj_s == min(all_edps)

    # Digital baseline comparison checks
    for p in report.pareto_points:
        assert p.digital_28nm_speedup > 1.0  # Analog stationary crossbar speedup over 28nm digital
        assert p.digital_28nm_energy_reduction_factor > 1.0  # Energy advantage over digital ASIC
