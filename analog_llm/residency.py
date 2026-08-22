"""Large-model accelerator weight residency, topology exploration, and chiplet scaling.

Analyzes physical crossbar tile counts, differential cell pairing, silicon area,
usable cell utilization, and multi-die chiplet packaging feasibility for T0–T3
decoder design tiers.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum
from typing import Any

from .model_manifest import ModelManifest


class ResidencySchedule(str, Enum):
    """Weight residency and reload schedules."""

    FULLY_RESIDENT = "fully_resident"
    LAYER_RESIDENT = "layer_resident"
    STREAMED_WEIGHT = "streamed_weight"


@dataclass(frozen=True)
class HardwareTopologyConfig:
    """Physical hardware architecture and silicon constraints."""

    tile_rows: int = 16
    tile_cols: int = 16
    cells_per_weight: int = 2  # Differential G+ and G- pair
    cell_pitch_um: float = 0.160  # 160 nm BEOL pitch (28nm node)
    peripheral_area_um2_per_tile: float = 1000.0  # SAR ADC, DAC, TIA, local logic (1000 um2 per 16x16 tile)
    max_die_area_mm2: float = 400.0  # Standard single-die reticle limit (400 mm2)
    max_chiplets_per_package: int = 12  # Advanced 2.5D/3D interposer limit (up to 12 chiplets)
    sram_bandwidth_tb_s: float = 8.0
    inter_die_ucie_bandwidth_gb_s: float = 512.0
    hbm3e_bandwidth_tb_s: float = 1.2
    pcie_bandwidth_gb_s: float = 64.0
    reram_write_energy_pj_per_cell: float = 5.0  # 5 pJ per programming pulse
    reram_write_time_ns: float = 50.0  # 50 ns pulse width


@dataclass(frozen=True)
class ScheduleMetrics:
    """Metrics for one weight residency schedule."""

    schedule_name: str
    weight_reload_bytes_per_token: int
    reload_time_per_token_us: float
    programming_energy_per_token_uj: float
    is_physically_viable: bool
    viability_note: str


@dataclass(frozen=True)
class ModelResidencySummary:
    """Complete physical layout, area, and residency analysis for a model."""

    model_name: str
    total_parameters: int
    analog_projection_parameters: int
    digital_parameters: int
    total_physical_tiles: int
    total_physical_cells: int
    usable_cell_utilization_pct: float
    reram_core_area_mm2: float
    peripheral_area_mm2: float
    total_silicon_area_mm2: float
    chiplets_required_for_full_residency: int
    is_single_die_resident: bool
    is_multi_die_package_resident: bool
    schedules: dict[str, ScheduleMetrics]
    metadata: dict[str, Any]


def analyze_model_residency(
    manifest: ModelManifest,
    topology: HardwareTopologyConfig | None = None,
    model_name: str = "custom",
) -> ModelResidencySummary:
    """Analyze physical crossbar capacity, area, and residency schedules for a ModelManifest."""
    topo = topology or HardwareTopologyConfig()
    specs = manifest.tensor_specs()

    total_params = sum(spec.parameters for spec in specs.values())
    analog_params = sum(spec.parameters for spec in specs.values() if spec.analog_eligible)
    digital_params = total_params - analog_params

    # Calculate exact physical tile pairs needed
    total_tiles = 0
    total_occupied_cells = 0

    for spec in specs.values():
        if not spec.analog_eligible:
            continue
        out_dim, in_dim = spec.shape
        row_blocks = math.ceil(in_dim / topo.tile_rows)
        col_blocks = math.ceil(out_dim / topo.tile_cols)
        tiles_for_tensor = row_blocks * col_blocks
        total_tiles += tiles_for_tensor
        total_occupied_cells += (out_dim * in_dim) * topo.cells_per_weight

    total_physical_cells = total_tiles * (topo.tile_rows * topo.tile_cols) * topo.cells_per_weight
    utilization_pct = (
        (total_occupied_cells / max(1, total_physical_cells)) * 100.0
        if total_physical_cells > 0
        else 0.0
    )

    # Physical Area Calculation
    cell_area_um2 = (topo.cell_pitch_um**2) * total_physical_cells
    reram_core_area_mm2 = cell_area_um2 / 1e6
    peripheral_area_mm2 = (total_tiles * topo.peripheral_area_um2_per_tile) / 1e6
    total_silicon_area_mm2 = reram_core_area_mm2 + peripheral_area_mm2

    chiplets_required = max(1, math.ceil(total_silicon_area_mm2 / topo.max_die_area_mm2))
    single_die = total_silicon_area_mm2 <= topo.max_die_area_mm2
    multi_die_package = chiplets_required <= topo.max_chiplets_per_package

    # Evaluate Residency Schedules
    schedules: dict[str, ScheduleMetrics] = {}

    # 1. Fully Resident Schedule
    schedules["fully_resident"] = ScheduleMetrics(
        schedule_name="fully_resident",
        weight_reload_bytes_per_token=0,
        reload_time_per_token_us=0.0,
        programming_energy_per_token_uj=0.0,
        is_physically_viable=multi_die_package,
        viability_note=(
            "Viable on single die"
            if single_die
            else (
                f"Viable across {chiplets_required} chiplets on interposer"
                if multi_die_package
                else f"Infeasible: requires {chiplets_required} dies (exceeds package limit {topo.max_chiplets_per_package})"
            )
        ),
    )

    # 2. Layer-by-Layer Resident Schedule (weights reloaded per layer)
    layer_bytes = (analog_params // max(1, manifest.num_layers)) * manifest.dtype_bytes
    reload_time_layer_us = (layer_bytes * manifest.num_layers) / (topo.hbm3e_bandwidth_tb_s * 1e6)
    layer_prog_energy_uj = (
        (analog_params * topo.cells_per_weight * topo.reram_write_energy_pj_per_cell) / 1e6
    )

    schedules["layer_resident"] = ScheduleMetrics(
        schedule_name="layer_resident",
        weight_reload_bytes_per_token=analog_params * manifest.dtype_bytes,
        reload_time_per_token_us=reload_time_layer_us,
        programming_energy_per_token_uj=layer_prog_energy_uj,
        is_physically_viable=True,
        viability_note="Requires active HBM3e streaming and ReRAM write endurance budget",
    )

    # 3. Off-chip Streamed Weight Schedule (weights streamed over PCIe)
    pcie_reload_time_us = (analog_params * manifest.dtype_bytes) / (topo.pcie_bandwidth_gb_s * 1e3)
    schedules["streamed_weight"] = ScheduleMetrics(
        schedule_name="streamed_weight",
        weight_reload_bytes_per_token=analog_params * manifest.dtype_bytes,
        reload_time_per_token_us=pcie_reload_time_us,
        programming_energy_per_token_uj=0.0,  # Computed in digital/SRAM buffer
        is_physically_viable=True,
        viability_note="High latency bottleneck on host PCIe link (bounded decode throughput)",
    )

    return ModelResidencySummary(
        model_name=model_name,
        total_parameters=total_params,
        analog_projection_parameters=analog_params,
        digital_parameters=digital_params,
        total_physical_tiles=total_tiles,
        total_physical_cells=total_physical_cells,
        usable_cell_utilization_pct=utilization_pct,
        reram_core_area_mm2=reram_core_area_mm2,
        peripheral_area_mm2=peripheral_area_mm2,
        total_silicon_area_mm2=total_silicon_area_mm2,
        chiplets_required_for_full_residency=chiplets_required,
        is_single_die_resident=single_die,
        is_multi_die_package_resident=multi_die_package,
        schedules=schedules,
        metadata={
            "cell_pitch_nm": topo.cell_pitch_um * 1000,
            "tile_geometry": f"{topo.tile_rows}x{topo.tile_cols}",
            "reticle_limit_mm2": topo.max_die_area_mm2,
        },
    )
