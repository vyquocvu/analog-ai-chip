"""Tests for Chapter 0032 Transformer Block Error Attribution."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import numpy as np
import pytest

_REPO = Path(__file__).resolve().parent.parent
_MODULE = _REPO / "book" / "0032-transformer-block" / "transformer_block.py"
_EXTRACT = _REPO / "verification" / "circuit" / "results" / "transformer-block-0032-extract.json"
_DIAGRAM = _REPO / "book" / "0032-transformer-block" / "diagrams" / "transformer-block-0032.svg"


def _load_module():
    spec = importlib.util.spec_from_file_location("transformer_block_0032", _MODULE)
    if spec is None or spec.loader is None:
        return None
    mod = importlib.util.module_from_spec(spec)
    sys.modules["transformer_block_0032"] = mod
    spec.loader.exec_module(mod)
    return mod


mod = _load_module()
TransformerBlockConfig = mod.TransformerBlockConfig
AnalogTransformerBlock = mod.AnalogTransformerBlock
evaluate_transformer_block = mod.evaluate_transformer_block
generate_transformer_block_extract = mod.generate_transformer_block_extract


def test_hand_computable_tile_counts() -> None:
    """TinyGPT Block: d_model=64, d_ffn=256, 4 heads:
    - QKV: (192/16) * (64/16) = 12 * 4 = 48 tiles
    - Out: (64/16) * (64/16) = 4 * 4 = 16 tiles
    - Up: (256/16) * (64/16) = 16 * 4 = 64 tiles
    - Down: (64/16) * (256/16) = 4 * 16 = 64 tiles
    - Total = 48 + 16 + 64 + 64 = 192 tiles
    """
    cfg = TransformerBlockConfig(d_model=64, d_ffn=256, num_heads=4, tile_rows=16, tile_cols=16)
    assert cfg.attn_tiles == 64
    assert cfg.mlp_tiles == 128
    assert cfg.total_tiles == 192


def test_transformer_block_forward_shapes() -> None:
    """Evaluates forward output shapes and stage breakdown."""
    rng = np.random.default_rng(42)
    w_qkv = rng.normal(0.0, 0.1, (48, 16))
    w_out = rng.normal(0.0, 0.1, (16, 16))
    w_up = rng.normal(0.0, 0.1, (64, 16))
    w_down = rng.normal(0.0, 0.1, (16, 64))
    x = rng.uniform(-1.0, 1.0, 16)

    cfg = TransformerBlockConfig(d_model=16, d_ffn=64, num_heads=2, tile_rows=16, tile_cols=16)
    block = AnalogTransformerBlock(w_qkv, w_out, w_up, w_down, cfg, nonideality_kwargs=None, seed=42)
    out, stages = block.forward(x, apply_calibration=False)

    assert out.shape == (16,)
    assert "attn_out" in stages
    assert "res1" in stages
    assert "mlp_out" in stages
    assert "block_out" in stages
    assert stages["block_out"].shape == (16,)


def test_leave_one_out_attribution_ranking() -> None:
    """Evaluates that leave-one-out attribution produces non-negative delta errors and ranking."""
    rng = np.random.default_rng(42)
    w_qkv = rng.normal(0.0, 0.1, (48, 16))
    w_out = rng.normal(0.0, 0.1, (16, 16))
    w_up = rng.normal(0.0, 0.1, (64, 16))
    w_down = rng.normal(0.0, 0.1, (16, 64))
    x = rng.uniform(-1.0, 1.0, 16)
    cfg = TransformerBlockConfig(d_model=16, d_ffn=64, num_heads=2, tile_rows=16, tile_cols=16)
    cb_path = _REPO / "device_profiles" / "crossbar-v1.json"

    rep = evaluate_transformer_block(w_qkv, w_out, w_up, w_down, cfg, x, cb_path, seed=42)
    assert len(rep.attributions) > 0
    for attr in rep.attributions:
        assert attr.delta_error_pct >= 0.0
        assert 0.0 <= attr.relative_importance_pct <= 100.0


def test_invalid_transformer_block_fails_closed() -> None:
    with pytest.raises(ValueError, match="positive"):
        TransformerBlockConfig(d_model=0)
    with pytest.raises(ValueError, match="divisible"):
        TransformerBlockConfig(d_model=16, num_heads=3)

    cfg = TransformerBlockConfig(d_model=16, d_ffn=32, num_heads=2, tile_rows=16, tile_cols=16)
    block = AnalogTransformerBlock(np.zeros((48, 16)), np.zeros((16, 16)), np.zeros((32, 16)), np.zeros((16, 32)), cfg)

    # Invalid input length
    with pytest.raises(ValueError, match="input shape"):
        block.forward(np.zeros(8))


def test_transformer_block_extract_is_reproducible() -> None:
    extract = generate_transformer_block_extract()
    assert _EXTRACT.is_file()
    committed = json.loads(_EXTRACT.read_text("utf-8"))
    assert extract == committed
    assert _DIAGRAM.is_file()
    assert extract["gate"] == "R7 — Transformer and LLM validation"
