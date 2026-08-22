import numpy as np

from analog_llm.generalized_decoder import GeneralizedDecoder
from analog_llm.large_model_eval import (
    compute_cross_entropy_perplexity,
    compute_mean_kl_divergence,
    compute_top1_agreement,
    evaluate_large_model_error_attribution,
)
from analog_llm.model_manifest import ModelManifest


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


def test_perplexity_and_kl_divergence_metrics() -> None:
    # 3 tokens, vocab 4
    logits = np.array([
        [10.0, 0.0, 0.0, 0.0],  # Token 0 -> predicts 0
        [0.0, 10.0, 0.0, 0.0],  # Token 1 -> predicts 1
        [0.0, 0.0, 10.0, 0.0],  # Token 2 -> predicts 2
    ])
    # Target sequence: [0, 1, 2] -> target for pos 0 is 1 (log_p ~ -10.0), target for pos 1 is 2 (log_p ~ -10.0)
    targets = [0, 1, 2]
    ppl = compute_cross_entropy_perplexity(logits, targets)
    assert ppl > 1.0

    # Perfect agreement test
    assert compute_top1_agreement(logits, logits) == 100.0
    assert compute_mean_kl_divergence(logits, logits) < 1e-10

    # Divergent logits
    noisy_logits = logits + np.random.default_rng(42).normal(0, 2.0, logits.shape)
    assert compute_mean_kl_divergence(logits, noisy_logits) > 0.0


def test_large_model_error_attribution_suite() -> None:
    decoder = _build_test_decoder()
    tokens = [1, 5, 2, 4]

    report = evaluate_large_model_error_attribution(decoder, tokens, model_name="test_model")

    assert report.baseline_perplexity > 0.0
    assert "composite_crossbar_v1" in report.mechanisms
    assert "programming_variation" in report.mechanisms
    assert "read_noise" in report.mechanisms

    # Converter resolution sensitivity: 4-bit error >= 8-bit error
    assert "4-bit" in report.converter_bit_sweep
    assert "6-bit" in report.converter_bit_sweep
    assert "8-bit" in report.converter_bit_sweep

    # Depth-wise layer MSE tracking
    assert len(report.depth_wise_layer_mse) == decoder.manifest.num_layers
    for mse in report.depth_wise_layer_mse:
        assert mse >= 0.0
