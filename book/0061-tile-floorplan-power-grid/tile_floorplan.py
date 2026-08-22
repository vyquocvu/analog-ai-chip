r"""Chapter 0061 — Core Tile Physical Floorplan & Power Grid IR Drop Signoff (Gate R15).

Synthesizes the complete physical layout of a 28nm BEOL core IMC tile,
routes the multi-layer power distribution grid (M1–M6), and performs DRC and IR drop signoff.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

_REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO))

from analog_layout.drc import run_drc
from analog_layout.export_svg import export_layout_to_svg
from analog_layout.power_grid import PowerGridConfig, simulate_power_grid_ir_drop
from analog_layout.tile_floorplan import TileFloorplanConfig, generate_tile_floorplan

RESULTS_DIR = _REPO / "verification" / "layout" / "results"
PLOTS_DIR = _REPO / "verification" / "layout" / "plots"
RESULT_PATH = RESULTS_DIR / "tile-floorplan-0061-extract.json"


def run_tile_floorplan_extract() -> dict[str, Any]:
    """Execute tile physical floorplan generation, DRC, and power grid signoff."""
    cfg = TileFloorplanConfig()
    cell = generate_tile_floorplan(cfg)

    # 1. DRC Verification
    drc_report = run_drc(cell)

    # 2. Power Grid IR Drop & EM Simulation
    power_cfg = PowerGridConfig()
    ir_report = simulate_power_grid_ir_drop(
        tile_size_um=cfg.tile_width_um,
        peak_current_ma=1.2,
        config=power_cfg,
    )

    # 3. Export Visual Layout Drawing
    PLOTS_DIR.mkdir(parents=True, exist_ok=True)
    export_layout_to_svg(cell, PLOTS_DIR / "core_tile_28nm_layout.svg")

    payload: dict[str, Any] = {
        "chapter": "0061-tile-floorplan-power-grid",
        "gate": "R15",
        "work_package": "WP15.3",
        "status": "PASSED" if (drc_report.is_clean and ir_report.is_ir_drop_clean and ir_report.is_em_clean) else "FAILED",
        "claim_level": "physical/tile-floorplan-power",
        "tile_specifications": {
            "name": cell.name,
            "width_um": cfg.tile_width_um,
            "height_um": cfg.tile_height_um,
            "total_area_um2": cell.metadata["total_tile_area_um2"],
            "derived_model_area_um2": cell.metadata["derived_model_area_um2"],
            "area_match_ratio": cell.metadata["total_tile_area_um2"] / cell.metadata["derived_model_area_um2"],
            "total_shapes": len(cell.rectangles),
            "port_count": len(cell.ports),
            "reram_quadrants": 4,
            "sar_adc_count": cfg.adc_bank_count,
            "sram_buffer_kb": cfg.sram_buffer_size_kb,
        },
        "drc_signoff": {
            "is_clean": drc_report.is_clean,
            "total_checks": drc_report.total_checks,
            "violation_count": drc_report.violation_count,
        },
        "power_grid_ir_drop": {
            "domain": ir_report.domain_name,
            "nominal_voltage_v": ir_report.nominal_voltage_v,
            "worst_case_voltage_v": ir_report.worst_case_voltage_v,
            "max_ir_drop_mv": ir_report.max_ir_drop_mv,
            "ir_drop_pct": ir_report.ir_drop_pct,
            "max_allowed_ir_drop_mv": power_cfg.max_allowed_ir_drop_mv,
            "peak_current_ma": ir_report.peak_current_ma,
            "mesh_resistance_ohm": ir_report.mesh_resistance_ohm,
            "max_current_density_ma_um": ir_report.max_current_density_ma_um,
            "max_allowed_em_limit_ma_um": power_cfg.max_allowed_em_current_density_ma_um,
            "is_ir_drop_clean": ir_report.is_ir_drop_clean,
            "is_em_clean": ir_report.is_em_clean,
        },
    }

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    with open(RESULT_PATH, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)

    return payload


def main() -> None:
    results = run_tile_floorplan_extract()
    print("=" * 95)
    print("CHAPTER 0061: CORE TILE PHYSICAL FLOORPLAN & POWER GRID IR DROP SIGNOFF (GATE R15)")
    print("=" * 95)
    print(f"Status: {results['status']} | Claim Level: {results['claim_level']}\n")
    t = results["tile_specifications"]
    print("Core Tile Physical Specifications:")
    print(f"  • Macro Name: {t['name']} ({t['width_um']:.1f} µm x {t['height_um']:.1f} µm)")
    print(f"  • Total Physical Area: {t['total_area_um2']:.1f} µm² (Derived Model: {t['derived_model_area_um2']:.1f} µm² | Match: {t['area_match_ratio']*100:.1f}%)")
    print(f"  • Integrated Blocks: 4x ReRAM Sub-Arrays, {t['sar_adc_count']}x SAR ADCs, {t['sram_buffer_kb']} KB SRAM Buffer")
    print(f"  • Physical Shapes: {t['total_shapes']} geometric rectangles | IO Ports: {t['port_count']} pins\n")
    p = results["power_grid_ir_drop"]
    print("Power Grid & IR Drop Signoff:")
    print(f"  • Nominal Supply: {p['nominal_voltage_v']:.2f} V | Worst-Case Voltage: {p['worst_case_voltage_v']:.4f} V")
    print(f"  • Max IR Drop: {p['max_ir_drop_mv']:.2f} mV ({p['ir_drop_pct']:.2f}% | Budget Limit: ≤ {p['max_allowed_ir_drop_mv']:.1f} mV)")
    print(f"  • Effective Mesh Resistance: {p['mesh_resistance_ohm']:.2f} Ω | Peak Current: {p['peak_current_ma']:.2f} mA")
    print(f"  • Max Current Density: {p['max_current_density_ma_um']:.2f} mA/µm (EM Limit: ≤ {p['max_allowed_em_limit_ma_um']:.1f} mA/µm)")
    print(f"  • IR Drop Clean: {p['is_ir_drop_clean']} | Electromigration Clean: {p['is_em_clean']}\n")
    drc = results["drc_signoff"]
    print(f"DRC Signoff: Clean = {drc['is_clean']} (Checks: {drc['total_checks']} | Violations: {drc['violation_count']})")
    print("=" * 95)
    print(f"Extracted artifact saved to: {RESULT_PATH}\n")


if __name__ == "__main__":
    main()
