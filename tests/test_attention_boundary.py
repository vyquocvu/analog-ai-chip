"""Tests for Chapter 0030 Attention Analog / Digital Boundary."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parent.parent
_MODULE = _REPO / "book" / "0030-attention-boundary" / "attention_boundary.py"
_EXTRACT = _REPO / "verification" / "circuit" / "results" / "attention-boundary-0030-extract.json"
_DIAGRAM = _REPO / "book" / "0030-attention-boundary" / "diagrams" / "attention-boundary-0030.svg"


def _load_module():
    spec = importlib.util.spec_from_file_location("attention_boundary_0030", _MODULE)
    if spec is None or spec.loader is None:
        return None
    mod = importlib.util.module_from_spec(spec)
    sys.modules["attention_boundary_0030"] = mod
    spec.loader.exec_module(mod)
    return mod


mod = _load_module()
AttentionBoundaryConfig = mod.AttentionBoundaryConfig
compute_boundary_ledger = mod.compute_boundary_ledger
generate_boundary_report = mod.generate_boundary_report
generate_boundary_extract = mod.generate_boundary_extract


def test_hand_computable_boundary_flops() -> None:
    """Hand-check: d_model=64, num_heads=4, L=16:
    - Analog: 8 * 16 * 64^2 = 8 * 16 * 4096 = 524,288 FLOPs
    - Digital: 4 * 16^2 * 64 + 3 * 4 * 16^2 = 4 * 256 * 64 + 12 * 256 = 65,536 + 3,072 = 68,608 FLOPs
    - Boundary: 3*16*64*4/8 + 16*64*4/8 = 1536 + 512 = 2048 Bytes
    """
    cfg = AttentionBoundaryConfig(d_model=64, num_heads=4)
    ledger = compute_boundary_ledger(cfg, seq_len=16)

    assert ledger.analog_proj_flops == 524288
    assert ledger.digital_attn_flops == 68608
    assert ledger.boundary_transfer_bytes == 2048


def test_dynamic_analog_reprogramming_penalty() -> None:
    """Evaluates that dynamic tile reprogramming has significant energy penalty over digital execution."""
    cfg = AttentionBoundaryConfig(d_model=64, num_heads=4)
    ledger = compute_boundary_ledger(cfg, seq_len=64)

    assert ledger.dynamic_analog_penalty_factor > 1.0
    assert ledger.hypothetical_dynamic_analog_energy_nj > ledger.digital_attn_energy_nj


def test_boundary_scaling_across_context_lengths() -> None:
    """Evaluates scaling behavior: Digital FLOPs grow O(L^2) while Analog FLOPs grow O(L)."""
    cfg = AttentionBoundaryConfig(d_model=64, num_heads=4)
    rep = generate_boundary_report(cfg)

    l16 = rep.scaling_analysis[0]
    l64 = rep.scaling_analysis[1]

    # Analog FLOPs 4x
    assert l64.analog_proj_flops == 4 * l16.analog_proj_flops
    # Digital FLOPs 16x (quadratic)
    assert l64.digital_attn_flops == 16 * l16.digital_attn_flops


def test_invalid_boundary_config_fails_closed() -> None:
    with pytest.raises(ValueError, match="positive"):
        AttentionBoundaryConfig(d_model=0)
    with pytest.raises(ValueError, match="divisible"):
        AttentionBoundaryConfig(d_model=64, num_heads=5)


def test_boundary_extract_is_reproducible() -> None:
    extract = generate_boundary_extract()
    assert _EXTRACT.is_file()
    committed = json.loads(_EXTRACT.read_text("utf-8"))
    assert extract == committed
    assert _DIAGRAM.is_file()
    assert extract["gate"] == "R7 — Transformer and LLM validation"
