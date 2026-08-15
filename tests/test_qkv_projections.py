"""Tests for Chapter 0029 Q/K/V Attention Projections Mapping."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import numpy as np
import pytest

_REPO = Path(__file__).resolve().parent.parent
_MODULE = _REPO / "book" / "0029-qkv-projections" / "qkv_projections.py"
_EXTRACT = _REPO / "verification" / "circuit" / "results" / "qkv-projections-0029-extract.json"
_DIAGRAM = _REPO / "book" / "0029-qkv-projections" / "diagrams" / "qkv-projections-0029.svg"


def _load_module():
    spec = importlib.util.spec_from_file_location("qkv_projections_0029", _MODULE)
    if spec is None or spec.loader is None:
        return None
    mod = importlib.util.module_from_spec(spec)
    sys.modules["qkv_projections_0029"] = mod
    spec.loader.exec_module(mod)
    return mod


mod = _load_module()
AttentionProjectionConfig = mod.AttentionProjectionConfig
AnalogQKVProjection = mod.AnalogQKVProjection
compute_projection_metrics = mod.compute_projection_metrics
evaluate_attention_projections = mod.evaluate_attention_projections
generate_qkv_extract = mod.generate_qkv_extract


def test_tiny_hand_computable_qkv_projection() -> None:
    """Hand-check: 16-dim model with 2 heads (d_head=8) and Identity weights:
    Output Q, K, V should match input vector x.
    """
    w_qkv = np.vstack([np.eye(16), np.eye(16), np.eye(16)])
    w_out = np.eye(16)
    x = np.zeros(16, dtype=np.float64)
    x[0] = 1.0

    cfg = AttentionProjectionConfig(d_model=16, num_heads=2, tile_rows=16, tile_cols=16)
    proj = AnalogQKVProjection(w_qkv, w_out, cfg, nonideality_kwargs=None, seed=42)
    q, k, v = proj.project_qkv(x, apply_calibration=False)

    assert q.shape == (16,)
    assert k.shape == (16,)
    assert v.shape == (16,)
    assert np.argmax(q) == 0
    assert np.argmax(k) == 0
    assert np.argmax(v) == 0


def test_attention_projection_tile_counts() -> None:
    """TinyGPT: d_model=64, num_heads=4:
    - QKV (192 x 64): (192/16) * (64/16) = 12 * 4 = 48 tiles
    - Out (64 x 64): (64/16) * (64/16) = 4 * 4 = 16 tiles
    - Total: 64 tiles
    """
    cfg = AttentionProjectionConfig(d_model=64, num_heads=4, tile_rows=16, tile_cols=16)
    assert cfg.d_head == 16
    assert cfg.qkv_tiles == 48
    assert cfg.out_tiles == 16
    assert cfg.total_tiles == 64


def test_attention_metrics_and_cosine_similarity() -> None:
    """Evaluates that cosine similarity is close to 1.0 and SNR > 0 dB under non-idealities."""
    rng = np.random.default_rng(42)
    w_qkv = rng.normal(0.0, 0.15, (48, 16))
    w_out = rng.normal(0.0, 0.15, (16, 16))
    x = rng.uniform(-1.0, 1.0, 16)
    cfg = AttentionProjectionConfig(d_model=16, num_heads=2, tile_rows=16, tile_cols=16)
    cb_path = _REPO / "device_profiles" / "crossbar-v1.json"

    rep = evaluate_attention_projections("test_attn", w_qkv, w_out, cfg, x, cb_path, seed=42)
    assert rep.q_metrics.cosine_similarity > 0.80
    assert rep.k_metrics.cosine_similarity > 0.80
    assert rep.v_metrics.cosine_similarity > 0.80
    assert rep.o_metrics.cosine_similarity > 0.75
    assert rep.q_metrics.snr_db > 4.0
    assert rep.calibration_recovery_pct >= 0.0


def test_invalid_attention_config_and_inputs_fail_closed() -> None:
    w_qkv = np.zeros((48, 16))
    w_out = np.zeros((16, 16))
    cfg = AttentionProjectionConfig(d_model=16, num_heads=2, tile_rows=16, tile_cols=16)
    proj = AnalogQKVProjection(w_qkv, w_out, cfg)

    # Indivisible num_heads
    with pytest.raises(ValueError, match="divisible"):
        AttentionProjectionConfig(d_model=16, num_heads=3)

    # Mismatched QKV shape
    with pytest.raises(ValueError, match="w_qkv shape"):
        AnalogQKVProjection(np.zeros((32, 16)), w_out, cfg)

    # Mismatched input shape
    with pytest.raises(ValueError, match="input shape"):
        proj.project_qkv(np.zeros(8))


def test_qkv_extract_is_reproducible() -> None:
    extract = generate_qkv_extract()
    assert _EXTRACT.is_file()
    committed = json.loads(_EXTRACT.read_text("utf-8"))
    assert extract == committed
    assert _DIAGRAM.is_file()
    assert extract["gate"] == "R7 — Transformer and LLM validation"
