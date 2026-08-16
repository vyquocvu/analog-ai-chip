"""Tests for Chapter 0031 Key-Value (KV) Cache Capacity and Traffic Model."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parent.parent
_MODULE = _REPO / "book" / "0031-kv-cache" / "kv_cache.py"
_EXTRACT = _REPO / "verification" / "circuit" / "results" / "kv-cache-0031-extract.json"
_DIAGRAM = _REPO / "book" / "0031-kv-cache" / "diagrams" / "kv-cache-0031.svg"


def _load_module():
    spec = importlib.util.spec_from_file_location("kv_cache_0031", _MODULE)
    if spec is None or spec.loader is None:
        return None
    mod = importlib.util.module_from_spec(spec)
    sys.modules["kv_cache_0031"] = mod
    spec.loader.exec_module(mod)
    return mod


mod = _load_module()
KVCacheConfig = mod.KVCacheConfig
KVCacheSimulator = mod.KVCacheSimulator
generate_kv_cache_extract = mod.generate_kv_cache_extract


def test_hand_computable_kv_capacity() -> None:
    """Hand-check: 4 layers, d_model=64, 4-bit act, 128 context:
    S_KV = 2 * 4 * 128 * 64 * 0.5 B = 32,768 bytes = 32 KB.
    """
    cfg = KVCacheConfig(num_layers=4, d_model=64, num_heads=4, act_bits=4, max_context_len=128)
    sim = KVCacheSimulator(cfg)

    cap = sim.capacity_bytes(128)
    assert cap == 32768
    assert cfg.bytes_per_token_all_layers == 256.0


def test_precision_scaling() -> None:
    """Evaluates footprint across 4-bit, 8-bit, 16-bit, and 32-bit precisions."""
    cfg = KVCacheConfig(num_layers=4, d_model=64, num_heads=4, max_context_len=128)
    sim = KVCacheSimulator(cfg)

    cap_4b = sim.capacity_bytes(128, act_bits=4)
    cap_8b = sim.capacity_bytes(128, act_bits=8)
    cap_16b = sim.capacity_bytes(128, act_bits=16)
    cap_32b = sim.capacity_bytes(128, act_bits=32)

    assert cap_8b == 2 * cap_4b
    assert cap_16b == 4 * cap_4b
    assert cap_32b == 8 * cap_4b


def test_autoregressive_traffic_scaling() -> None:
    """Evaluates that cumulative read traffic scales quadratically with generation length."""
    cfg = KVCacheConfig(num_layers=4, d_model=64, num_heads=4, act_bits=4, max_context_len=128)
    sim = KVCacheSimulator(cfg)

    # Prompt=16, Gen=16 -> Context=32
    run1 = sim.simulate_generation(prompt_len=16, gen_tokens=16)
    # Prompt=16, Gen=48 -> Context=64
    run2 = sim.simulate_generation(prompt_len=16, gen_tokens=48)

    assert run1.total_write_bytes == 32 * 256
    assert run2.total_write_bytes == 64 * 256
    assert run2.total_read_bytes > run1.total_read_bytes * 4.0
    assert run1.sram_total_energy_nj < run1.dram_total_energy_nj


def test_paged_kv_cache_fragmentation() -> None:
    """Evaluates that paged allocation with block size 16 eliminates external fragmentation."""
    cfg = KVCacheConfig(num_layers=4, d_model=64, num_heads=4, act_bits=4, max_context_len=128, block_size_tokens=16)
    sim = KVCacheSimulator(cfg)

    # Context length 40 is not a multiple of 16 -> 3 blocks allocated (48 tokens)
    run = sim.simulate_generation(prompt_len=16, gen_tokens=24)
    assert run.paged_allocated_bytes == 3 * sim.capacity_bytes(16)
    assert run.paged_fragmentation_pct > 0.0
    assert run.paged_fragmentation_pct < run.contiguous_fragmentation_pct


def test_invalid_kv_cache_inputs_fail_closed() -> None:
    with pytest.raises(ValueError, match="positive"):
        KVCacheConfig(num_layers=0)
    with pytest.raises(ValueError, match="act_bits"):
        KVCacheConfig(act_bits=5)

    cfg = KVCacheConfig(max_context_len=128)
    sim = KVCacheSimulator(cfg)

    # Sequence length exceeds max context
    with pytest.raises(ValueError, match="exceeds max_context_len"):
        sim.simulate_generation(prompt_len=64, gen_tokens=100)


def test_kv_cache_extract_is_reproducible() -> None:
    extract = generate_kv_cache_extract()
    assert _EXTRACT.is_file()
    committed = json.loads(_EXTRACT.read_text("utf-8"))
    assert extract == committed
    assert _DIAGRAM.is_file()
    assert extract["gate"] == "R7 — Transformer and LLM validation"
