"""Tests for Chapter 0028 Multi-Layer Perceptron (MLP) Block Mapping."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import numpy as np
import pytest

_REPO = Path(__file__).resolve().parent.parent
_MODULE = _REPO / "book" / "0028-mlp" / "mlp.py"
_EXTRACT = _REPO / "verification" / "circuit" / "results" / "mlp-0028-extract.json"
_DIAGRAM = _REPO / "book" / "0028-mlp" / "diagrams" / "mlp-0028.svg"


def _load_module():
    spec = importlib.util.spec_from_file_location("mlp_0028", _MODULE)
    if spec is None or spec.loader is None:
        return None
    mod = importlib.util.module_from_spec(spec)
    sys.modules["mlp_0028"] = mod
    spec.loader.exec_module(mod)
    return mod


mod = _load_module()
ActivationFunction = mod.ActivationFunction
MLPConfig = mod.MLPConfig
AnalogMLPBlock = mod.AnalogMLPBlock
compute_mlp_metrics = mod.compute_mlp_metrics
evaluate_mlp_block = mod.evaluate_mlp_block
generate_mlp_extract = mod.generate_mlp_extract


def test_tiny_hand_computable_mlp_forward() -> None:
    """Hand-check: 16 -> 16 -> 16 MLP with Identity weights and ReLU:
    For positive unit vector x = [1, 0, ...], output should be x + ReLU(x) = 2*x.
    """
    w_eye = np.eye(16, dtype=np.float64)
    x = np.zeros(16, dtype=np.float64)
    x[0] = 1.0

    cfg = MLPConfig(
        d_model=16,
        d_ffn=16,
        tile_rows=16,
        tile_cols=16,
        activation=ActivationFunction.RELU,
        include_residual=True,
    )
    block = AnalogMLPBlock(w_eye, w_eye, cfg, nonideality_kwargs=None, seed=42)
    out = block.forward(x, apply_calibration=False)

    assert out.shape == (16,)
    assert out[0] > 1.5  # ideally close to 2.0
    assert np.argmax(out) == 0


def test_mlp_tile_counts_and_structure() -> None:
    """TinyGPT: d_model=64, d_ffn=256, 16x16 tiles:
    - Up: (256/16) * (64/16) = 16 * 4 = 64 tiles
    - Down: (64/16) * (256/16) = 4 * 16 = 64 tiles
    - Total: 128 physical tiles
    """
    cfg = MLPConfig(d_model=64, d_ffn=256, tile_rows=16, tile_cols=16)
    assert cfg.up_tiles == 64
    assert cfg.down_tiles == 64
    assert cfg.total_tiles == 128


def test_mlp_activations_and_calibration_improvement() -> None:
    """Evaluates that calibration reduces compound error across GELU and SiLU activations."""
    rng = np.random.default_rng(42)
    w_up = rng.normal(0.0, 0.15, (64, 32))
    w_down = rng.normal(0.0, 0.15, (32, 64))
    x = rng.uniform(-1.0, 1.0, 32)
    cfg = MLPConfig(d_model=32, d_ffn=64, tile_rows=16, tile_cols=16, activation=ActivationFunction.GELU)
    cb_path = _REPO / "device_profiles" / "crossbar-v1.json"

    rep = evaluate_mlp_block("test_mlp", w_up, w_down, cfg, x, cb_path, seed=42)
    assert rep.ideal_quantized.snr_db > 0.0
    assert rep.raw_nonideal.snr_db > 0.0
    assert rep.calibrated_nonideal.snr_db > 0.0
    assert rep.calibrated_nonideal.rel_l2_error_pct < 100.0
    assert rep.calibration_improvement_pct >= 0.0


def test_invalid_mlp_inputs_fail_closed() -> None:
    w_up = np.zeros((32, 16))
    w_down = np.zeros((16, 32))
    cfg = MLPConfig(d_model=16, d_ffn=32, tile_rows=16, tile_cols=16)
    block = AnalogMLPBlock(w_up, w_down, cfg)

    # Invalid weights shapes
    with pytest.raises(ValueError, match="w_up shape"):
        AnalogMLPBlock(np.zeros((16, 16)), w_down, cfg)
    with pytest.raises(ValueError, match="w_down shape"):
        AnalogMLPBlock(w_up, np.zeros((16, 16)), cfg)

    # Invalid input vector shape
    with pytest.raises(ValueError, match="input shape"):
        block.forward(np.zeros(8))

    # Invalid config
    with pytest.raises(ValueError, match="positive"):
        MLPConfig(d_model=0, d_ffn=32)


def test_mlp_extract_is_reproducible() -> None:
    extract = generate_mlp_extract()
    assert _EXTRACT.is_file()
    committed = json.loads(_EXTRACT.read_text("utf-8"))
    assert extract == committed
    assert _DIAGRAM.is_file()
    assert extract["gate"] == "R7 — Transformer and LLM validation"
