import numpy as np

from analog_llm.generalized_decoder import GeneralizedDecoder
from analog_llm.model_manifest import ModelManifest
from analog_llm.recovery import (
    RecoveryStrategy,
    evaluate_layer_sensitivities,
    evaluate_scalable_recovery_suite,
)


def _build_test_decoder() -> GeneralizedDecoder:
    manifest = ModelManifest(
        vocab_size=16,
        hidden_size=8,
        num_layers=2,
        num_attention_heads=2,
        num_key_value_heads=2,
        intermediate_size=16,
        context_length=8,
        dtype="float32",
        norm_type="layernorm",
        position_type="learned",
        activation_type="gelu",
        attention_type="mha",
        linear_bias=True,
        tied_embeddings=True,
    )
    rng = np.random.default_rng(42)
    w: dict[str, np.ndarray] = {
        "token_embedding.weight": rng.normal(0, 0.02, (16, 8)),
        "position_embedding.weight": rng.normal(0, 0.02, (8, 8)),
        "final_norm.weight": np.ones((8,)),
        "final_norm.bias": np.zeros((8,)),
    }
    for i in range(2):
        p = f"layers.{i}."
        w[f"{p}attention_norm.weight"] = np.ones((8,))
        w[f"{p}attention_norm.bias"] = np.zeros((8,))
        w[f"{p}attention.q_proj.weight"] = rng.normal(0, 0.02, (8, 8))
        w[f"{p}attention.q_proj.bias"] = np.zeros((8,))
        w[f"{p}attention.k_proj.weight"] = rng.normal(0, 0.02, (8, 8))
        w[f"{p}attention.k_proj.bias"] = np.zeros((8,))
        w[f"{p}attention.v_proj.weight"] = rng.normal(0, 0.02, (8, 8))
        w[f"{p}attention.v_proj.bias"] = np.zeros((8,))
        w[f"{p}attention.out_proj.weight"] = rng.normal(0, 0.02, (8, 8))
        w[f"{p}attention.out_proj.bias"] = np.zeros((8,))

        w[f"{p}mlp_norm.weight"] = np.ones((8,))
        w[f"{p}mlp_norm.bias"] = np.zeros((8,))
        w[f"{p}mlp.up_proj.weight"] = rng.normal(0, 0.02, (16, 8))
        w[f"{p}mlp.up_proj.bias"] = np.zeros((16,))
        w[f"{p}mlp.down_proj.weight"] = rng.normal(0, 0.02, (8, 16))
        w[f"{p}mlp.down_proj.bias"] = np.zeros((8,))

    return GeneralizedDecoder(manifest, weights=w)


def test_layer_sensitivity_profiling() -> None:
    decoder = _build_test_decoder()
    tokens = [1, 5, 2, 4]

    sensitivities = evaluate_layer_sensitivities(decoder, tokens)
    assert len(sensitivities) == 2
    ranks = [s.sensitivity_rank for s in sensitivities]
    assert set(ranks) == {1, 2}
    for s in sensitivities:
        assert s.isolated_mse >= 0.0
        assert s.perplexity_impact > 0.0


def test_scalable_recovery_ladder_and_ledger() -> None:
    decoder = _build_test_decoder()
    tokens = [1, 5, 2, 4]

    report = evaluate_scalable_recovery_suite(
        decoder,
        tokens,
        model_name="test_model",
        acceptance_ppl_factor=1.3,
        acceptance_min_top1_pct=50.0,
    )

    ladder = report.recovery_ladder
    assert RecoveryStrategy.UNMITIGATED.value in ladder
    assert RecoveryStrategy.OUTPUT_CALIBRATION.value in ladder
    assert RecoveryStrategy.WRITE_VERIFY_TUNING.value in ladder
    assert RecoveryStrategy.DEFECT_REMAPPING.value in ladder
    assert RecoveryStrategy.SELECTIVE_DIGITAL_FALLBACK.value in ladder
    assert RecoveryStrategy.COMPOSITE_RECOVERY.value in ladder

    unmit = ladder[RecoveryStrategy.UNMITIGATED.value]
    comp = ladder[RecoveryStrategy.COMPOSITE_RECOVERY.value]

    # Composite recovery improves top-1 agreement and reduces KL divergence
    assert comp.top1_agreement_pct >= unmit.top1_agreement_pct
    assert comp.mean_kl_divergence <= unmit.mean_kl_divergence

    # Hardware ledger checks
    assert comp.metadata_storage_bytes > 0
    assert comp.programming_energy_multiplier > 1.0  # Write-verify overhead
    assert comp.digital_fallback_layers_count == 1  # 1 digital layer fallback
    assert comp.digital_compute_overhead_pct == 50.0  # 1 of 2 layers
