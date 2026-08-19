"""Tests for Chapter 0023 — Scheduler & Temporal Reuse."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parent.parent
_MODULE = _REPO / "book" / "0023-scheduler" / "scheduler.py"
_EXTRACT = _REPO / "verification" / "circuit" / "results" / "scheduler-0023-extract.json"


def _load_module():
    spec = importlib.util.spec_from_file_location("scheduler_0023", _MODULE)
    if spec is None or spec.loader is None:
        return None
    mod = importlib.util.module_from_spec(spec)
    sys.modules["scheduler_0023"] = mod
    spec.loader.exec_module(mod)
    return mod


mod = _load_module()


def test_module_loaded() -> None:
    assert mod is not None, "Failed to load book/0023-scheduler/scheduler.py"


def test_layer_spec_calculations() -> None:
    """Validate LayerSpec block and MAC counting."""
    assert mod is not None
    layer = mod.LayerSpec("test_proj", m_out=64, m_in=128)
    assert layer.macs() == 64 * 128
    assert layer.num_blocks(16, 16) == (64 // 16) * (128 // 16)  # 4 * 8 = 32 blocks
    assert layer.num_blocks(32, 32) == (64 // 32) * (128 // 32)  # 2 * 4 = 8 blocks


def test_tiny_hand_computable_schedule() -> None:
    """Five blocks on two tiles require ceil(5/2)=3 cycles and three rewrites."""
    assert mod is not None
    sched = mod.AcceleratorScheduler(tile_rows=2, tile_cols=2, tile_count=2)
    layer = mod.LayerSpec("tiny", m_out=2, m_in=10)

    rep = sched.schedule_workload([layer], mod.SchedulingStrategy.TEMPORAL_MULTIPLEXED)

    assert layer.num_blocks(2, 2) == 5
    assert rep.total_cycles == 3
    assert rep.total_programs == 5
    assert rep.total_rewrites == 3
    assert rep.utilization_efficiency == pytest.approx(5 / 6)


@pytest.mark.parametrize(
    "kwargs",
    [
        {"tile_rows": 0},
        {"tile_cols": 0},
        {"tile_count": 0},
        {"tile_count": -1},
    ],
)
def test_scheduler_rejects_invalid_hardware_dimensions(kwargs: dict[str, int]) -> None:
    assert mod is not None
    with pytest.raises(ValueError, match="positive"):
        mod.AcceleratorScheduler(**kwargs)


def test_layer_rejects_invalid_shape() -> None:
    assert mod is not None
    with pytest.raises(ValueError, match="positive"):
        mod.LayerSpec("invalid", m_out=0, m_in=4)


def test_transformer_workload_layer_counts() -> None:
    """Validate transformer layer workload decomposition."""
    assert mod is not None
    sched = mod.AcceleratorScheduler(tile_rows=16, tile_cols=16, tile_count=16)
    layers = sched.create_transformer_layer_workload(d_model=128, d_ffn=512)

    assert len(layers) == 4
    total_blocks = sum(layer.num_blocks(16, 16) for layer in layers)
    assert total_blocks == 768
    assert sum(layer.macs() for layer in layers) == 196608


def test_temporal_multiplexing_schedule() -> None:
    """Validate temporal multiplexing cycle and rewrite formulas."""
    assert mod is not None
    sched = mod.AcceleratorScheduler(tile_rows=16, tile_cols=16, tile_count=16)
    layers = sched.create_transformer_layer_workload(d_model=128, d_ffn=512)

    rep = sched.schedule_workload(layers, mod.SchedulingStrategy.TEMPORAL_MULTIPLEXED)
    assert rep.total_programs == 768
    assert rep.total_rewrites == (192 - 16) + (64 - 16) + (256 - 16) + (256 - 16)
    assert rep.total_cycles == (192 // 16) + (64 // 16) + (256 // 16) + (
        256 // 16
    )  # 12 + 4 + 16 + 16 = 48


def test_weight_stationary_speedup() -> None:
    """Weight-stationary must provide massive latency speedup over temporal reuse on streaming tokens."""
    assert mod is not None
    sched_resident = mod.AcceleratorScheduler(tile_rows=16, tile_cols=16, tile_count=1024)
    layers = sched_resident.create_transformer_layer_workload(d_model=128, d_ffn=512)

    rep_stat = sched_resident.schedule_workload(layers, mod.SchedulingStrategy.WEIGHT_STATIONARY)
    rep_temp = sched_resident.schedule_workload(layers, mod.SchedulingStrategy.TEMPORAL_MULTIPLEXED)

    assert rep_stat.total_rewrites == 0
    assert rep_stat.total_time_us_100tokens < rep_temp.total_time_us_100tokens
    assert rep_temp.total_time_us_100tokens / rep_stat.total_time_us_100tokens > 50.0


def test_committed_extract_integrity() -> None:
    """Validate structure and metrics of committed extract JSON."""
    assert _EXTRACT.exists(), f"Missing extract artifact at {_EXTRACT}"
    with open(_EXTRACT, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert data["schema_version"] == "0.1.0"
    assert data["chapter"] == "0023-scheduler"
    assert data["summary"]["total_workload_blocks"] == 768
    assert data["summary"]["temporal_16tiles_cycles"] == 48
    assert data["summary"]["temporal_16tiles_rewrites"] == 704
    assert data["summary"]["speedup_100tok_stationary_vs_temporal"] > 90.0
    assert data["timing_assumptions"]["t_mvm_ns"]["evidence_class"] == "assumed"
    assert data["timing_assumptions"]["t_prog_us"]["evidence_class"] == "assumed"
    assert mod.run_scheduler_extract() == data


def test_diagram_svgs_exist() -> None:
    """Verify presence of Chapter 0023 SVG diagrams."""
    diag_dir = _REPO / "book" / "0023-scheduler" / "diagrams"
    assert (diag_dir / "scheduler_architecture.svg").is_file(), "Missing scheduler_architecture.svg"
    assert (diag_dir / "scheduler_scaling.svg").is_file(), "Missing scheduler_scaling.svg"
