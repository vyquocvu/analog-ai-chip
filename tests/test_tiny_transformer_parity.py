"""Tests for Chapter 0033 Tiny Transformer End-to-End Parity Study."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import numpy as np

_REPO = Path(__file__).resolve().parent.parent
_MODULE = _REPO / "book" / "0033-tiny-transformer" / "tiny_transformer.py"
_EXTRACT = _REPO / "verification" / "circuit" / "results" / "tiny-transformer-0033-extract.json"
_DIAGRAM = _REPO / "book" / "0033-tiny-transformer" / "diagrams" / "tiny-transformer-0033.svg"


def _load_module():
    spec = importlib.util.spec_from_file_location("tiny_transformer_0033", _MODULE)
    if spec is None or spec.loader is None:
        return None
    mod = importlib.util.module_from_spec(spec)
    sys.modules["tiny_transformer_0033"] = mod
    spec.loader.exec_module(mod)
    return mod


mod = _load_module()
compute_tile_count = mod.compute_tile_count
compute_cross_entropy = mod.compute_cross_entropy
compute_parity_metrics = mod.compute_parity_metrics
generate_tiny_transformer_extract = mod.generate_tiny_transformer_extract


def test_hand_computable_tile_counts() -> None:
    """TinyGPT tile counts:
    Per layer: QKV=ceil(192/16)*ceil(64/16)=12*4=48, Out=4*4=16,
    Up=ceil(256/16)*4=16*4=64, Down=4*16=64 => 192 tiles/layer.
    2 layers: 384. Head: ceil(128/16)*4=8*4=32. Total: 416.
    """
    from analog_llm import TinyGPTConfig
    cfg = TinyGPTConfig(vocab_size=128, n_embd=64, n_layer=2, n_head=4, block_size=16, ffn_mult=4)
    tiles = compute_tile_count(cfg, 16, 16)

    assert tiles["qkv_tiles_per_layer"] == 48
    assert tiles["out_tiles_per_layer"] == 16
    assert tiles["up_tiles_per_layer"] == 64
    assert tiles["down_tiles_per_layer"] == 64
    assert tiles["tiles_per_layer"] == 192
    assert tiles["total_layer_tiles"] == 384
    assert tiles["head_tiles"] == 32
    assert tiles["total_physical_tiles"] == 416


def test_float_reference_determinism() -> None:
    """Float reference forward pass is deterministic across re-runs."""
    from analog_llm import TinyGPT, TinyGPTConfig
    cfg = TinyGPTConfig(seed=0)
    model = TinyGPT(cfg)
    prompt = np.array([3, 9, 14, 22, 5], dtype=np.int64)

    logits1 = model.forward_logits(prompt, accelerator=None)
    logits2 = model.forward_logits(prompt, accelerator=None)
    np.testing.assert_array_equal(logits1, logits2)


def test_cross_entropy_computation() -> None:
    """Hand-check cross-entropy with uniform logits -> log(vocab_size)."""
    vocab_size = 4
    logits = np.zeros((2, vocab_size))  # uniform distribution
    targets = np.array([0, 1])
    ce = compute_cross_entropy(logits, targets)
    expected = np.log(vocab_size)
    assert abs(ce - expected) < 1e-6


def test_parity_metrics_measurable() -> None:
    """Parity metrics are computable and in valid ranges."""
    float_logits = np.random.default_rng(42).normal(0, 1, (4, 10))
    analog_logits = float_logits + np.random.default_rng(43).normal(0, 0.5, (4, 10))
    targets = np.array([0, 1, 2, 3])
    float_gen = np.array([1, 2, 3, 4, 5])
    analog_gen = np.array([1, 2, 3, 6, 7])

    parity = compute_parity_metrics(float_logits, analog_logits, targets, float_gen, analog_gen)
    assert 0.0 <= parity.logit_rel_l2_error_pct
    assert 0.0 <= parity.top1_token_agreement_pct <= 100.0
    assert 0.0 <= parity.generation_token_agreement_pct <= 100.0
    assert parity.float_perplexity > 0.0
    assert parity.analog_perplexity > 0.0


def test_tiny_transformer_extract_is_reproducible() -> None:
    """Extract is deterministic and matches committed artifact."""
    extract = generate_tiny_transformer_extract()
    assert _EXTRACT.is_file()
    committed = json.loads(_EXTRACT.read_text("utf-8"))
    assert extract == committed
    assert _DIAGRAM.is_file()
    assert extract["gate"] == "R7 — Transformer and LLM validation"
    assert extract["tile_breakdown"]["total_physical_tiles"] == 416
