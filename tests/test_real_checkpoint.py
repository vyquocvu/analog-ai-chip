"""Tests for Chapter 0035 Real Pretrained Checkpoint Execution."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import numpy as np

_REPO = Path(__file__).resolve().parent.parent
_MODULE = _REPO / "book" / "0035-real-checkpoint" / "real_checkpoint.py"
_EXTRACT = _REPO / "verification" / "circuit" / "results" / "real-checkpoint-0035-extract.json"
_DIAGRAM = _REPO / "book" / "0035-real-checkpoint" / "diagrams" / "real-checkpoint-0035.svg"


def _load_module():
    spec = importlib.util.spec_from_file_location("real_checkpoint_0035", _MODULE)
    if spec is None or spec.loader is None:
        return None
    mod = importlib.util.module_from_spec(spec)
    sys.modules["real_checkpoint_0035"] = mod
    spec.loader.exec_module(mod)
    return mod


mod = _load_module()
create_hf_checkpoint_fixture = mod.create_hf_checkpoint_fixture
evaluate_real_checkpoint = mod.evaluate_real_checkpoint
generate_real_checkpoint_extract = mod.generate_real_checkpoint_extract


def test_hf_checkpoint_fixture_creation(tmp_path) -> None:
    """Verifies that create_hf_checkpoint_fixture produces valid safetensors + config.json."""
    ckpt_dir = tmp_path / "test_gpt2"
    create_hf_checkpoint_fixture(ckpt_dir, vocab_size=16, n_embd=8, n_layer=1, n_head=2, seed=0)

    assert (ckpt_dir / "model.safetensors").is_file()
    assert (ckpt_dir / "config.json").is_file()

    config = json.loads((ckpt_dir / "config.json").read_text("utf-8"))
    assert config["vocab_size"] == 16
    assert config["n_embd"] == 8
    assert config["n_layer"] == 1


def test_real_checkpoint_loader_integration(tmp_path) -> None:
    """Evaluates checkpoint loading into TinyGPT and running inference."""
    from analog_llm.gpt_loader import load_gpt2

    ckpt_dir = tmp_path / "gpt2_small"
    create_hf_checkpoint_fixture(ckpt_dir, vocab_size=32, n_embd=16, n_layer=1, n_head=2, seed=1)

    model = load_gpt2(ckpt_dir, block_size=8)
    prompt = np.array([1, 5, 10, 15], dtype=np.int64)

    logits = model.forward_logits(prompt)
    assert logits.shape == (4, 32)
    assert np.all(np.isfinite(logits))


def test_real_checkpoint_evaluation_metrics(tmp_path) -> None:
    """Evaluates that evaluation metrics are properly computed on the checkpoint."""
    ckpt_dir = tmp_path / "gpt2_eval"
    create_hf_checkpoint_fixture(ckpt_dir, vocab_size=32, n_embd=16, n_layer=1, n_head=2, seed=2)
    prompt = np.array([2, 4, 6, 8], dtype=np.int64)

    result = evaluate_real_checkpoint(ckpt_dir, prompt, seed=42)
    assert "parity_metrics" in result
    pm = result["parity_metrics"]
    assert pm["logit_rel_l2_error_pct"] > 0.0
    assert pm["float_perplexity"] > 0.0
    assert pm["analog_perplexity"] > 0.0
    assert result["accelerator_ledger"]["total_macs"] > 0


def test_real_checkpoint_extract_is_reproducible() -> None:
    extract = generate_real_checkpoint_extract()
    assert _EXTRACT.is_file()
    committed = json.loads(_EXTRACT.read_text("utf-8"))
    assert extract == committed
    assert _DIAGRAM.is_file()
    diagram_dir = _DIAGRAM.parent
    assert (diagram_dir / "real-checkpoint-ingestion-0035.svg").is_file()
    assert (diagram_dir / "real-checkpoint-parity-0035.svg").is_file()
    assert (diagram_dir / "real-checkpoint-floorplan-0035.svg").is_file()
    assert extract["gate"] == "R7 — Transformer and LLM validation"
    assert extract["tile_breakdown"]["total_physical_tiles"] == 416
