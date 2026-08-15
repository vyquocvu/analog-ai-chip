"""Tests for Chapter 0027 Linear Layer Mapping."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import numpy as np
import pytest

_REPO = Path(__file__).resolve().parent.parent
_MODULE = _REPO / "book" / "0027-linear-layer" / "linear_layer.py"
_EXTRACT = _REPO / "verification" / "circuit" / "results" / "linear-layer-0027-extract.json"
_DIAGRAM = _REPO / "book" / "0027-linear-layer" / "diagrams" / "linear-layer-0027.svg"


def _load_module():
    spec = importlib.util.spec_from_file_location("linear_layer_0027", _MODULE)
    if spec is None or spec.loader is None:
        return None
    mod = importlib.util.module_from_spec(spec)
    sys.modules["linear_layer_0027"] = mod
    spec.loader.exec_module(mod)
    return mod


mod = _load_module()
LinearLayerConfig = mod.LinearLayerConfig
AnalogLinearLayer = mod.AnalogLinearLayer
compute_evaluation_metrics = mod.compute_evaluation_metrics
evaluate_linear_layer = mod.evaluate_linear_layer
generate_linear_layer_extract = mod.generate_linear_layer_extract


def test_tiny_hand_computable_identity_mapping() -> None:
    """Hand-check: 16x16 identity matrix on 16x16 ideal tile:
    Output for unit vector e_0 should align with e_0.
    """
    w_eye = np.eye(16, dtype=np.float64)
    x = np.zeros(16, dtype=np.float64)
    x[0] = 1.0

    cfg = LinearLayerConfig(m_out=16, m_in=16, tile_rows=16, tile_cols=16)
    layer = AnalogLinearLayer(w_eye, cfg, nonideality_kwargs=None, seed=42)
    out = layer.forward(x, apply_calibration=False)

    assert out.shape == (16,)
    assert out[0] > 0.0
    assert np.argmax(out) == 0


def test_multi_tile_spatial_reduction_parity() -> None:
    """32x32 matrix on 16x16 tiles (Kr=2, Kc=2 -> 4 tiles):
    Forward pass runs all 4 tiles and sums 2 column partial sums per row.
    """
    w = np.ones((32, 32), dtype=np.float64) * 0.1
    x = np.ones(32, dtype=np.float64)

    cfg = LinearLayerConfig(m_out=32, m_in=32, tile_rows=16, tile_cols=16)
    assert cfg.kr == 2
    assert cfg.kc == 2
    assert cfg.total_tiles == 4

    layer = AnalogLinearLayer(w, cfg, nonideality_kwargs=None, seed=42)
    out = layer.forward(x, apply_calibration=False)

    assert out.shape == (32,)
    # All rows are identical and symmetric
    assert np.allclose(out, out[0], rtol=1e-5)


def test_calibration_reduces_nonideal_residual_error() -> None:
    """Evaluates that applying calibration gain a*=0.9795135 improves MVM error."""
    rng = np.random.default_rng(42)
    w = rng.normal(0.0, 0.2, (64, 64))
    x = rng.uniform(-1.0, 1.0, 64)
    cfg = LinearLayerConfig(m_out=64, m_in=64, tile_rows=16, tile_cols=16)
    cb_path = _REPO / "device_profiles" / "crossbar-v1.json"

    report = evaluate_linear_layer("test_layer", w, cfg, x, cb_path, seed=42)
    assert report.ideal_quantized.rel_l2_error_pct < report.raw_nonideal.rel_l2_error_pct
    assert report.calibrated_nonideal.rel_l2_error_pct <= report.raw_nonideal.rel_l2_error_pct
    assert report.calibration_improvement_pct >= 0.0


def test_invalid_linear_layer_inputs_fail_closed() -> None:
    w = np.zeros((16, 16))
    cfg = LinearLayerConfig(m_out=16, m_in=16, tile_rows=16, tile_cols=16)
    layer = AnalogLinearLayer(w, cfg, nonideality_kwargs=None)

    # Mismatched weight shape
    with pytest.raises(ValueError, match="weight shape"):
        AnalogLinearLayer(np.zeros((8, 16)), cfg)

    # Mismatched input vector shape
    with pytest.raises(ValueError, match="input shape"):
        layer.forward(np.zeros(8))

    # Invalid config dimensions
    with pytest.raises(ValueError, match="positive"):
        LinearLayerConfig(m_out=0, m_in=16)


def test_linear_layer_extract_is_reproducible() -> None:
    extract = generate_linear_layer_extract()
    assert _EXTRACT.is_file()
    committed = json.loads(_EXTRACT.read_text("utf-8"))
    assert extract == committed
    assert _DIAGRAM.is_file()
    assert extract["gate"] == "R7 — Transformer and LLM validation"
