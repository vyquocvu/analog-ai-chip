"""Tests for Chapter 0034 Full Autoregressive Path Architecture Ledger."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import numpy as np

_REPO = Path(__file__).resolve().parent.parent
_MODULE = _REPO / "book" / "0034-autoregressive-path" / "autoregressive_path.py"
_EXTRACT = _REPO / "verification" / "circuit" / "results" / "autoregressive-path-0034-extract.json"
_DIAGRAM = _REPO / "book" / "0034-autoregressive-path" / "diagrams" / "autoregressive-path-0034.svg"


def _load_module():
    spec = importlib.util.spec_from_file_location("autoregressive_path_0034", _MODULE)
    if spec is None or spec.loader is None:
        return None
    mod = importlib.util.module_from_spec(spec)
    sys.modules["autoregressive_path_0034"] = mod
    spec.loader.exec_module(mod)
    return mod


mod = _load_module()
trace_step = mod.trace_step
trace_autoregressive_generation = mod.trace_autoregressive_generation
generate_autoregressive_path_extract = mod.generate_autoregressive_path_extract


def test_hand_computable_step_macs() -> None:
    """Hand check for 1 token step on TinyGPT (d=64, ffn=256, 2 layers, vocab=128):
    - Layer analog: QKV (3*64*64=12288) + Out (64*64=4096) + Up (256*64=16384) + Down (64*256=16384) = 49152
    - 2 layers: 98304
    - Head: 128*64 = 8192
    - Total analog MACs: 98304 + 8192 = 106,496 MACs.
    """
    from analog_llm import TinyGPTConfig
    cfg = TinyGPTConfig(vocab_size=128, n_embd=64, n_layer=2, n_head=4, ffn_mult=4)

    step0 = trace_step(cfg, step_idx=0, token_id=115, prompt_len=4)
    assert step0.analog_macs == 106496
    assert step0.digital_macs == 256  # 2 * 2 * 64 * 1
    assert step0.total_macs == 106752
    assert step0.phase == "PREFILL"

    step5 = trace_step(cfg, step_idx=5, token_id=93, prompt_len=4)
    assert step5.analog_macs == 106496  # Constant
    assert step5.digital_macs == 256 * 6  # 1536
    assert step5.phase == "DECODE"


def test_sram_traffic_scaling() -> None:
    """Evaluates SRAM traffic growth as context grows."""
    from analog_llm import TinyGPTConfig
    cfg = TinyGPTConfig(vocab_size=128, n_embd=64, n_layer=2, n_head=4, ffn_mult=4)

    step0 = trace_step(cfg, step_idx=0, token_id=10, prompt_len=4)
    step5 = trace_step(cfg, step_idx=5, token_id=10, prompt_len=4)

    # Read traffic grows linearly with context length
    assert step5.sram_read_bytes > step0.sram_read_bytes
    # Write traffic is constant per token
    assert step5.sram_write_bytes == step0.sram_write_bytes


def test_kv_cache_savings_monotonicity() -> None:
    """Evaluates that KV cache provides significant computation, energy and speedup advantage."""
    prompt = np.array([1, 2, 3, 4], dtype=np.int64)
    trace = trace_autoregressive_generation(prompt, max_new_tokens=8, seed=0)

    comp = trace["comparison_with_no_cache"]
    assert comp["mac_reduction_ratio"] > 4.0
    assert comp["energy_savings_ratio"] > 4.0
    assert comp["speedup_ratio"] > 4.0
    assert comp["peak_kv_cache_bytes"] == 3072


def test_autoregressive_extract_is_reproducible() -> None:
    extract = generate_autoregressive_path_extract()
    assert _EXTRACT.is_file()
    committed = json.loads(_EXTRACT.read_text("utf-8"))
    assert extract == committed
    assert _DIAGRAM.is_file()
    diagram_dir = _DIAGRAM.parent
    assert (diagram_dir / "autoregressive-timeline-0034.svg").is_file()
    assert (diagram_dir / "autoregressive-kv-traffic-0034.svg").is_file()
    assert (diagram_dir / "autoregressive-hardware-mapping-0034.svg").is_file()
    assert extract["gate"] == "R7 — Transformer and LLM validation"
    assert extract["summary"]["total_tokens"] == 12
