"""Tests for Chapter 0026 End-to-End Architecture & Calibration Ledger."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parent.parent
_MODULE = _REPO / "book" / "0026-calibration" / "architecture_ledger.py"
_EXTRACT = _REPO / "verification" / "circuit" / "results" / "architecture-ledger-0026-extract.json"
_DIAGRAM = _REPO / "book" / "0026-calibration" / "diagrams" / "architecture-ledger-0026.svg"


def _load_module():
    spec = importlib.util.spec_from_file_location("architecture_ledger_0026", _MODULE)
    if spec is None or spec.loader is None:
        return None
    mod = importlib.util.module_from_spec(spec)
    sys.modules["architecture_ledger_0026"] = mod
    spec.loader.exec_module(mod)
    return mod


mod = _load_module()
ExecutionMode = mod.ExecutionMode
TileHardwareSpec = mod.TileHardwareSpec
LayerArchitectureLedger = mod.LayerArchitectureLedger
compute_layer_architecture_ledger = mod.compute_layer_architecture_ledger
generate_architecture_ledger_extract = mod.generate_architecture_ledger_extract


def test_tiny_hand_computable_single_tile_ledger() -> None:
    """Hand-check: 16x16 layer on 1 physical 16x16 tile:
    - Kr=1, Kc=1, total_layer_tiles=1
    - Cycles=1, Rewrites=0
    - Timing: t_mvm_step = 5.0 + 0.05 + 5.0 + 10.0 = 20.05 ns
    - Reduction: tree_levels=0 -> 0 ns
    - Programming: 0 us
    - Total latency: 20.05 ns = 0.02005 us
    - Analog energy: 256 MACs * 50 fJ = 12,800 fJ = 0.0128 nJ
    - Output calibration gain: 0.9795135
    """
    hw = TileHardwareSpec(tile_rows=16, tile_cols=16, num_physical_tiles=1)
    ledger = compute_layer_architecture_ledger(
        "single_tile_test", 16, 16, hw, ExecutionMode.WEIGHT_STATIONARY
    )
    assert ledger.kr == 1
    assert ledger.kc == 1
    assert ledger.total_layer_tiles == 1
    assert ledger.num_mvm_cycles == 1
    assert ledger.num_tile_rewrites == 0
    assert ledger.timing.t_mvm_step_ns == pytest.approx(20.05)
    assert ledger.timing.t_reduction_ns == 0.0
    assert ledger.timing.t_programming_us == 0.0
    assert ledger.timing.total_latency_us == pytest.approx(0.02005)
    assert ledger.energy.analog_mvm_nj == pytest.approx(0.0128)
    assert ledger.calibration_gain == pytest.approx(0.9795135)


def test_weight_stationary_vs_temporal_trade_off() -> None:
    """TinyGPT QKV (192x64 -> 48 tiles):
    - Stationary (64 physical tiles): 1 cycle, 0 rewrites, low latency, low energy.
    - Temporal (16 physical tiles): 3 cycles, 32 rewrites, high latency due to programming.
    """
    hw_stat = TileHardwareSpec(tile_rows=16, tile_cols=16, num_physical_tiles=64)
    hw_temp = TileHardwareSpec(tile_rows=16, tile_cols=16, num_physical_tiles=16)

    stat = compute_layer_architecture_ledger("qkv_stat", 192, 64, hw_stat, ExecutionMode.WEIGHT_STATIONARY)
    temp = compute_layer_architecture_ledger("qkv_temp", 192, 64, hw_temp, ExecutionMode.TEMPORAL_MULTIPLEXED)

    assert stat.num_mvm_cycles == 1
    assert stat.num_tile_rewrites == 0
    assert temp.num_mvm_cycles == 3
    assert temp.num_tile_rewrites == 32

    # Stationary has significantly lower latency and energy
    assert stat.timing.total_latency_us < temp.timing.total_latency_us
    assert stat.energy.total_energy_nj < temp.energy.total_energy_nj
    assert temp.timing.t_programming_us == 32 * (16 * 500.0) / 1000.0  # 256 us


def test_provenance_ledger_integrity() -> None:
    extract = generate_architecture_ledger_extract()
    provenance = extract["provenance_ledger"]
    for category in ["timing_parameters", "energy_parameters"]:
        assert category in provenance
        for param_data in provenance[category].values():
            assert "value" in param_data
            assert "evidence_class" in param_data
            assert param_data["evidence_class"] in ["derived", "spice", "assumed", "measured"]
            assert "source" in param_data


def test_invalid_parameters_fail_closed() -> None:
    hw = TileHardwareSpec(tile_rows=16, tile_cols=16, num_physical_tiles=16)
    with pytest.raises(ValueError, match="positive"):
        compute_layer_architecture_ledger("invalid", 0, 64, hw)
    with pytest.raises(ValueError, match="positive"):
        compute_layer_architecture_ledger("invalid", 64, -1, hw)
    with pytest.raises(ValueError, match="positive"):
        TileHardwareSpec(tile_rows=0)


def test_architecture_ledger_extract_is_reproducible() -> None:
    extract = generate_architecture_ledger_extract()
    assert _EXTRACT.is_file()
    committed = json.loads(_EXTRACT.read_text("utf-8"))
    assert extract == committed
    assert _DIAGRAM.is_file()
    assert extract["gate_status"] == "MET"
    assert extract["claim_level"] == "SYSTEM_SIMULATED"
