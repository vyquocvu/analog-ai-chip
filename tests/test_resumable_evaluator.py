from pathlib import Path

import numpy as np
import pytest

from analog_llm.generalized_decoder import GeneralizedDecoder
from analog_llm.model_manifest import ModelManifest
from analog_llm.resumable_evaluator import (
    TIER_BUDGETS,
    EvaluationMode,
    ResumableModelEvaluator,
)


def _build_test_decoder() -> GeneralizedDecoder:
    manifest = ModelManifest(
        vocab_size=16,
        hidden_size=8,
        num_layers=4,
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
    for i in range(4):
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


def test_resumable_evaluator_parity_and_idempotency(tmp_path: Path) -> None:
    decoder = _build_test_decoder()
    prompt = [1, 5, 2]

    # 1. Full single pass run in fresh directory
    dir_full = tmp_path / "full_run"
    evaluator_full = ResumableModelEvaluator(decoder, checkpoint_dir=dir_full, mode=EvaluationMode.EXACT)
    logits_full, summary_full = evaluator_full.evaluate_prompt(prompt)

    assert summary_full["status"] == "COMPLETED"
    assert summary_full["layers_resumed"] == 0
    assert summary_full["layers_computed"] == 4

    # 2. Interrupted run at layer 1 (evaluates layers 0 and 1)
    dir_interrupted = tmp_path / "resumed_run"
    eval_interrupted = ResumableModelEvaluator(decoder, checkpoint_dir=dir_interrupted, mode=EvaluationMode.EXACT)
    _, summary_part = eval_interrupted.evaluate_prompt(prompt, interrupt_after_layer=1)

    assert summary_part["status"] == "INTERRUPTED"
    assert summary_part["interrupted_at_layer"] == 1
    assert summary_part["layers_computed"] == 2

    # 3. Resumed run in same directory (should resume layers 0, 1 and compute 2, 3)
    eval_resumed = ResumableModelEvaluator(decoder, checkpoint_dir=dir_interrupted, mode=EvaluationMode.EXACT)
    logits_resumed, summary_resumed = eval_resumed.evaluate_prompt(prompt)

    assert summary_resumed["status"] == "COMPLETED"
    assert summary_resumed["layers_resumed"] == 2
    assert summary_resumed["layers_computed"] == 2

    # Exact parity on logits
    np.testing.assert_allclose(logits_resumed, logits_full, atol=1e-12)


def test_tamper_detection_fails_closed(tmp_path: Path) -> None:
    decoder = _build_test_decoder()
    prompt = [1, 2]
    eval_dir = tmp_path / "tamper_test"
    evaluator = ResumableModelEvaluator(decoder, checkpoint_dir=eval_dir, mode=EvaluationMode.EXACT)
    evaluator.evaluate_prompt(prompt, interrupt_after_layer=1)

    # Corrupt layer 0 state file
    state_file = eval_dir / "layer_0000_state.npy"
    corrupt_state = np.ones((2, 8)) * 999.0
    np.save(state_file, corrupt_state)

    # Resuming should fail closed with hash divergence
    eval_resumed = ResumableModelEvaluator(decoder, checkpoint_dir=eval_dir, mode=EvaluationMode.EXACT)
    with pytest.raises(ValueError, match="Corrupt state file|Tamper or state divergence"):
        eval_resumed.evaluate_prompt(prompt)


def test_tier_budgets_definition() -> None:
    for tier in ("T0", "T1", "T2", "T3"):
        assert tier in TIER_BUDGETS
        budget = TIER_BUDGETS[tier]
        assert budget.max_context_tokens >= 2048
        assert budget.max_rss_bytes > 0
        assert budget.max_runtime_seconds > 0
