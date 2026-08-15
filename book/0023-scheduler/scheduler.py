r"""Chapter 0023 — Scheduler & Temporal Reuse (Gate R5/R6).

Models deterministic hardware tile scheduling, spatial parallelism vs temporal reuse,
and execution ledger accounting for analog crossbar accelerators:

1. **Spatial vs Temporal Scheduling**:
   - **Weight-Stationary (Spatial Dedication)**: All layer weights are permanently
     mapped to on-chip tiles. Zero rewrite overhead during token generation.
   - **Layer-by-Layer Temporal Multiplexing**: Physical tiles are dynamically
     reprogrammed across layers. Enables execution with a small physical tile footprint,
     but incurs cell programming latency.
   - **Hybrid Allocation**: High-frequency attention layers are kept stationary;
     large feed-forward (MLP) layers are time-multiplexed.

2. **Assumed Latency Sensitivity Point**:
   - MVM execution cycle: t_mvm = 20 ns (assumed; profile timing pending).
   - NVM cell programming: t_prog = 10 us (assumed; device evidence pending).
   - Their ratio is 500x. It is a sensitivity-study input, not verified performance.

3. **Deterministic Ledger & Metrics**:
   - Parallel execution cycles: T_cycles = ceil(K_blocks / N_tiles)
   - Rewrite events: N_rewrites = max(0, K_blocks - N_tiles)
   - Tile utilization efficiency: eta_util = K_blocks / (N_tiles * T_cycles)
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any

# Sensitivity-study assumptions only. These values are not extracted from the
# validated device profiles and therefore cannot support a physical claim.
ASSUMED_T_MVM_NS = 20.0
ASSUMED_T_PROG_US = 10.0


class SchedulingStrategy(str, Enum):
    WEIGHT_STATIONARY = "weight_stationary"
    TEMPORAL_MULTIPLEXED = "temporal_multiplexed"
    HYBRID = "hybrid"


@dataclass(frozen=True)
class LayerSpec:
    """Specification of a single linear projection in a Transformer layer."""

    name: str
    m_out: int
    m_in: int

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("layer name must be non-empty")
        if self.m_out <= 0 or self.m_in <= 0:
            raise ValueError("layer dimensions must be positive")

    def num_blocks(self, tile_rows: int = 16, tile_cols: int = 16) -> int:
        if tile_rows <= 0 or tile_cols <= 0:
            raise ValueError("tile dimensions must be positive")
        kr = math.ceil(self.m_out / tile_rows)
        kc = math.ceil(self.m_in / tile_cols)
        return kr * kc

    def macs(self) -> int:
        return self.m_out * self.m_in


@dataclass
class ScheduleReport:
    """Execution ledger for a scheduled workload."""

    strategy: SchedulingStrategy
    tile_count: int
    tile_dim: int
    total_macs: int
    total_cycles: int
    total_programs: int
    total_rewrites: int
    utilization_efficiency: float
    mvm_time_ns: float
    prog_time_us: float
    total_time_us_1token: float
    total_time_us_100tokens: float


class AcceleratorScheduler:
    """Simulates deterministic scheduling of Transformer workloads onto physical tiles."""

    def __init__(self, tile_rows: int = 16, tile_cols: int = 16, tile_count: int = 16) -> None:
        if tile_rows <= 0 or tile_cols <= 0 or tile_count <= 0:
            raise ValueError("tile dimensions and tile_count must be positive")
        self.tile_rows = tile_rows
        self.tile_cols = tile_cols
        self.tile_count = tile_count

    def create_transformer_layer_workload(
        self, d_model: int = 128, d_ffn: int = 512
    ) -> list[LayerSpec]:
        """Generate canonical linear projections for one Transformer layer."""
        return [
            LayerSpec("qkv_proj", 3 * d_model, d_model),
            LayerSpec("out_proj", d_model, d_model),
            LayerSpec("mlp_up", d_ffn, d_model),
            LayerSpec("mlp_down", d_model, d_ffn),
        ]

    def schedule_workload(
        self,
        layers: list[LayerSpec],
        strategy: SchedulingStrategy = SchedulingStrategy.TEMPORAL_MULTIPLEXED,
    ) -> ScheduleReport:
        """Schedule layers and compute deterministic execution metrics."""
        total_macs = sum(l.macs() for l in layers)
        layer_blocks = [l.num_blocks(self.tile_rows, self.tile_cols) for l in layers]
        total_blocks = sum(layer_blocks)

        if strategy == SchedulingStrategy.WEIGHT_STATIONARY:
            # All blocks resident on chip; requires tile_count >= total_blocks
            if self.tile_count < total_blocks:
                # Fallback to temporal multiplexing if insufficient tiles
                return self.schedule_workload(layers, SchedulingStrategy.TEMPORAL_MULTIPLEXED)

            cycles = 0
            for k in layer_blocks:
                cycles += math.ceil(k / self.tile_count) if k > 0 else 0

            programs = total_blocks  # Programmed once during initialization
            rewrites = 0
            utilization = total_blocks / (self.tile_count * max(cycles, 1))

        elif strategy == SchedulingStrategy.TEMPORAL_MULTIPLEXED:
            # Tiles are reused across layers
            cycles = 0
            programs = 0
            rewrites = 0

            for k in layer_blocks:
                layer_cycles = math.ceil(k / self.tile_count)
                cycles += layer_cycles
                programs += k
                rewrites += max(0, k - self.tile_count)

            utilization = total_blocks / (self.tile_count * max(cycles, 1))

        else:  # HYBRID (stationary QKV, multiplexed MLP)
            qkv_blocks = layer_blocks[0]
            resident_tiles = min(qkv_blocks, self.tile_count // 2)
            avail_tiles = max(1, self.tile_count - resident_tiles)

            cycles = math.ceil(qkv_blocks / max(resident_tiles, 1))
            programs = qkv_blocks
            rewrites = 0

            for k in layer_blocks[1:]:
                layer_cycles = math.ceil(k / avail_tiles)
                cycles += layer_cycles
                programs += k
                rewrites += max(0, k - avail_tiles)

            utilization = total_blocks / (self.tile_count * max(cycles, 1))

        mvm_time_ns = cycles * ASSUMED_T_MVM_NS
        prog_time_us = programs * ASSUMED_T_PROG_US

        # Latency for 1 token: initial programming + MVM
        total_time_1token = (mvm_time_ns / 1000.0) + prog_time_us

        # Latency for 100 tokens:
        # In weight stationary: initial programming + 100 * MVM
        # In temporal multiplexing: 100 * (MVM + reprogramming per token)
        if strategy == SchedulingStrategy.WEIGHT_STATIONARY and self.tile_count >= total_blocks:
            total_time_100tokens = prog_time_us + (100 * mvm_time_ns / 1000.0)
        else:
            total_time_100tokens = 100 * total_time_1token

        return ScheduleReport(
            strategy=strategy,
            tile_count=self.tile_count,
            tile_dim=self.tile_rows,
            total_macs=total_macs,
            total_cycles=cycles,
            total_programs=programs,
            total_rewrites=rewrites,
            utilization_efficiency=min(utilization, 1.0),
            mvm_time_ns=mvm_time_ns,
            prog_time_us=prog_time_us,
            total_time_us_1token=total_time_1token,
            total_time_us_100tokens=total_time_100tokens,
        )


def run_scheduler_extract() -> dict[str, Any]:
    """Run characterization sweeps across tile capacities and scheduling strategies."""
    scheduler_base = AcceleratorScheduler(tile_rows=16, tile_cols=16, tile_count=16)
    workload = scheduler_base.create_transformer_layer_workload(d_model=128, d_ffn=512)

    # 1. Sweep on-chip tile capacity (16 to 1024 tiles)
    tile_counts = [16, 32, 64, 128, 256, 512, 768, 1024]
    capacity_sweeps = []

    for tc in tile_counts:
        sched = AcceleratorScheduler(tile_rows=16, tile_cols=16, tile_count=tc)
        rep_temporal = sched.schedule_workload(workload, SchedulingStrategy.TEMPORAL_MULTIPLEXED)
        rep_stationary = sched.schedule_workload(workload, SchedulingStrategy.WEIGHT_STATIONARY)

        capacity_sweeps.append(
            {
                "tile_count": tc,
                "temporal_cycles": rep_temporal.total_cycles,
                "temporal_rewrites": rep_temporal.total_rewrites,
                "temporal_utilization": rep_temporal.utilization_efficiency,
                "temporal_latency_100tok_us": rep_temporal.total_time_us_100tokens,
                "stationary_cycles": rep_stationary.total_cycles,
                "stationary_rewrites": rep_stationary.total_rewrites,
                "stationary_latency_100tok_us": rep_stationary.total_time_us_100tokens,
            }
        )

    # 2. Layer breakdown for d_model=128, d_ffn=512 (16x16 tiles)
    layer_breakdown = []
    for l in workload:
        b = l.num_blocks(16, 16)
        m = l.macs()
        layer_breakdown.append(
            {
                "name": l.name,
                "shape": f"{l.m_out}x{l.m_in}",
                "blocks_16x16": b,
                "macs": m,
            }
        )

    extract = {
        "schema_version": "0.1.0",
        "chapter": "0023-scheduler",
        "title": "Hardware Tile Scheduling and Temporal Reuse",
        "workload": {
            "d_model": 128,
            "d_ffn": 512,
            "layers": layer_breakdown,
            "total_blocks_16x16": sum(l["blocks_16x16"] for l in layer_breakdown),
            "total_macs": sum(l["macs"] for l in layer_breakdown),
        },
        "timing_assumptions": {
            "t_mvm_ns": {
                "value": ASSUMED_T_MVM_NS,
                "unit": "ns/cycle",
                "evidence_class": "assumed",
                "provenance": "architecture sensitivity-study input; profile-derived timing is pending",
            },
            "t_prog_us": {
                "value": ASSUMED_T_PROG_US,
                "unit": "us/program",
                "evidence_class": "assumed",
                "provenance": "architecture sensitivity-study input; device programming evidence is pending",
            },
            "write_read_latency_ratio": {
                "value": ASSUMED_T_PROG_US * 1000.0 / ASSUMED_T_MVM_NS,
                "unit": "dimensionless",
                "evidence_class": "derived",
                "derived_from": ["timing_assumptions/t_mvm_ns", "timing_assumptions/t_prog_us"],
            },
        },
        "capacity_sweeps": capacity_sweeps,
        "summary": {
            "total_workload_blocks": sum(l["blocks_16x16"] for l in layer_breakdown),
            "min_tiles_for_weight_stationary": sum(l["blocks_16x16"] for l in layer_breakdown),
            "temporal_16tiles_cycles": capacity_sweeps[0]["temporal_cycles"],
            "temporal_16tiles_rewrites": capacity_sweeps[0]["temporal_rewrites"],
            "speedup_100tok_stationary_vs_temporal": capacity_sweeps[-1][
                "temporal_latency_100tok_us"
            ]
            / capacity_sweeps[-1]["stationary_latency_100tok_us"],
            "evidence_class": "derived",
            "provenance": "Deterministic hardware tile scheduler accounting for MVM cycles, reprogramming overhead, and spatial capacity",
            "claim_limit": "Timing results are an assumed sensitivity study, not verified physical performance.",
        },
    }
    return extract


def main() -> None:
    print("Running Chapter 0023 Scheduler & Temporal Reuse Extraction...")
    extract = run_scheduler_extract()
    out_dir = Path(__file__).resolve().parents[2] / "verification" / "circuit" / "results"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / "scheduler-0023-extract.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(extract, f, indent=2)
    print(f"Committed extract written to {out_file}")
    s = extract["summary"]
    print(f"  Total Layer Blocks (16x16):           {s['total_workload_blocks']}")
    print(f"  Min Tiles for Weight Stationary:      {s['min_tiles_for_weight_stationary']}")
    print(f"  Temporal Multiplexing Cycles @ 16 tiles: {s['temporal_16tiles_cycles']}")
    print(f"  Temporal Multiplexing Rewrites @ 16 tiles: {s['temporal_16tiles_rewrites']}")
    print(
        f"  Speedup (100 tok) Stationary vs Temporal: {s['speedup_100tok_stationary_vs_temporal']:.1f}x"
    )


if __name__ == "__main__":
    main()
