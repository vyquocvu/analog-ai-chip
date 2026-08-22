"""Power Grid Mesh Routing & IR Drop / Electromigration (EM) Analysis.

Models multi-layer metal power distribution grids (M1–M6), solves static/dynamic
resistive mesh IR drop, and evaluates electromigration current density compliance for 28nm BEOL.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class PowerGridConfig:
    """Design parameters for tile-level multi-layer power distribution grid."""

    supply_voltage_analog_v: float = 1.0
    supply_voltage_digital_v: float = 0.9
    max_allowed_ir_drop_mv: float = 30.0  # 3.0% of nominal 1.0V supply
    max_allowed_em_current_density_ma_um: float = 1.5  # Foundry EM limit in mA/um metal width
    m1_sheet_res_ohm_sq: float = 0.15
    m2_sheet_res_ohm_sq: float = 0.15
    m5_sheet_res_ohm_sq: float = 0.05
    m6_sheet_res_ohm_sq: float = 0.04
    via_resistance_ohm: float = 1.5
    m5_strap_width_nm: int = 400
    m6_strap_width_nm: int = 600
    mesh_pitch_um: float = 8.0  # Power strap spacing


@dataclass(frozen=True)
class PowerGridReport:
    """Complete Power Integrity, IR Drop, and Electromigration signoff report."""

    domain_name: str
    nominal_voltage_v: float
    worst_case_voltage_v: float
    max_ir_drop_mv: float
    ir_drop_pct: float
    peak_current_ma: float
    max_current_density_ma_um: float
    is_ir_drop_clean: bool
    is_em_clean: bool
    mesh_resistance_ohm: float
    metadata: dict[str, Any]


def simulate_power_grid_ir_drop(
    tile_size_um: float = 57.3,
    peak_current_ma: float = 1.2,
    config: PowerGridConfig | None = None,
    domain: str = "VDD_ANA",
) -> PowerGridReport:
    """Solve multi-layer resistive mesh network equations to determine peak IR drop and EM."""
    cfg = config or PowerGridConfig()
    v_nom = cfg.supply_voltage_analog_v if "ANA" in domain else cfg.supply_voltage_digital_v

    # Number of parallel global power straps across tile width/height
    num_straps = max(2, int(tile_size_um / cfg.mesh_pitch_um))

    # Resistance of one M6 strap across tile (length = tile_size_um)
    m6_len_um = tile_size_um
    m6_w_um = cfg.m6_strap_width_nm / 1000.0
    r_strap_m6 = (m6_len_um / m6_w_um) * cfg.m6_sheet_res_ohm_sq

    # Resistance of one M5 strap across tile
    m5_len_um = tile_size_um
    m5_w_um = cfg.m5_strap_width_nm / 1000.0
    r_strap_m5 = (m5_len_um / m5_w_um) * cfg.m5_sheet_res_ohm_sq

    # Equivalent multi-layer mesh resistance from top supply rail to center load node
    # Combining parallel M6 global straps, via stacks, and M5 orthogonal grid
    r_parallel_m6 = r_strap_m6 / num_straps
    r_parallel_m5 = r_strap_m5 / num_straps
    r_vias = (cfg.via_resistance_ohm / (num_straps * num_straps))

    # Equivalent Lumped Mesh Resistance to central worst-case point
    r_mesh_eff = (r_parallel_m6 * 0.25) + (r_parallel_m5 * 0.25) + r_vias

    # Worst-case IR Drop (Ohm's Law across grid)
    # Peak current distributed across tile with worst-case drop at geometric center
    max_ir_drop_mv = (peak_current_ma * 1e-3) * r_mesh_eff * 1e3
    worst_v = v_nom - (max_ir_drop_mv / 1000.0)
    ir_pct = (max_ir_drop_mv / (v_nom * 1000.0)) * 100.0

    # Current density through hottest M6 power strap
    current_per_strap_ma = peak_current_ma / num_straps
    j_current_density_ma_um = current_per_strap_ma / m6_w_um

    is_ir_clean = max_ir_drop_mv <= cfg.max_allowed_ir_drop_mv
    is_em_clean = j_current_density_ma_um <= cfg.max_allowed_em_current_density_ma_um

    return PowerGridReport(
        domain_name=domain,
        nominal_voltage_v=v_nom,
        worst_case_voltage_v=worst_v,
        max_ir_drop_mv=max_ir_drop_mv,
        ir_drop_pct=ir_pct,
        peak_current_ma=peak_current_ma,
        max_current_density_ma_um=j_current_density_ma_um,
        is_ir_drop_clean=is_ir_clean,
        is_em_clean=is_em_clean,
        mesh_resistance_ohm=r_mesh_eff,
        metadata={
            "num_global_straps": num_straps,
            "m6_strap_width_um": m6_w_um,
            "m5_strap_width_um": m5_w_um,
            "mesh_pitch_um": cfg.mesh_pitch_um,
            "tile_dimension_um": tile_size_um,
        },
    )
