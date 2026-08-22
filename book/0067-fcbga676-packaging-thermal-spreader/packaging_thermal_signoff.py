r"""Chapter 0067 — FCBGA-676 Packaging, 4-2-4 Organic Substrate & Thermal Spreader (Gate R17).

Synthesizes FCBGA-676 ball maps, validates 4-2-4 organic substrate differential impedance,
and extracts junction temperatures under passive/forced nickel-plated copper heat spreaders.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

_REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO))

from analog_layout.packaging import (
    FCBGA676PackageConfig,
    SubstrateStackupConfig,
    ThermalSpreaderConfig,
    run_package_thermal_signoff,
)

RESULTS_DIR = _REPO / "verification" / "layout" / "results"
RESULT_PATH = RESULTS_DIR / "packaging-0067-extract.json"


def run_packaging_signoff_extract() -> dict[str, Any]:
    """Execute FCBGA-676 packaging and thermal junction extraction."""
    pkg = FCBGA676PackageConfig()
    sub = SubstrateStackupConfig()
    thm = ThermalSpreaderConfig()

    report = run_package_thermal_signoff(pkg, sub, thm)

    payload: dict[str, Any] = {
        "chapter": "0067-fcbga676-packaging-thermal-spreader",
        "gate": "R17",
        "work_package": "WP17.2",
        "status": "PASSED" if (report.is_package_compliant and report.is_thermal_compliant) else "FAILED",
        "claim_level": "physical/packaging-thermal",
        "fcbga676_package": {
            "body_width_mm": pkg.body_width_mm,
            "body_height_mm": pkg.body_height_mm,
            "ball_pitch_mm": pkg.ball_pitch_mm,
            "total_bga_balls": report.ball_map.total_balls,
            "c4_bump_pitch_um": pkg.c4_bump_pitch_um,
            "c4_bump_count": pkg.c4_bump_count,
            "die_area_mm2": pkg.die_area_mm2,
        },
        "ball_map_allocations": {
            "vss_ground_balls": report.ball_map.vss_ground_balls,
            "vdd_dig_core_balls": report.ball_map.vdd_dig_core_balls,
            "vdd_ana_analog_balls": report.ball_map.vdd_ana_analog_balls,
            "pcie_gen5_serdes_balls": report.ball_map.pcie_gen5_serdes_balls,
            "lpddr5_memory_if_balls": report.ball_map.lpddr5_memory_if_balls,
            "control_jtag_ref_balls": report.ball_map.control_jtag_ref_balls,
        },
        "substrate_stackup": {
            "buildup_structure": "4-2-4 Organic Buildup",
            "layer_count": sub.layer_count,
            "core_thickness_um": sub.core_thickness_um,
            "single_ended_impedance_ohm": sub.single_ended_impedance_ohm,
            "differential_pcie_impedance_ohm": sub.differential_impedance_pcie_ohm,
            "loss_tangent": sub.loss_tangent,
        },
        "thermal_signoff": {
            "chip_tdp_w": thm.chip_tdp_w,
            "ambient_temp_c": thm.ambient_temp_c,
            "theta_jc_c_per_w": report.theta_jc_c_per_w,
            "theta_ca_c_per_w": report.theta_ca_c_per_w,
            "theta_ja_c_per_w": report.theta_ja_c_per_w,
            "peak_junction_temp_c": report.peak_junction_temp_c,
            "max_junction_temp_budget_c": report.max_junction_temp_budget_c,
            "thermal_margin_c": report.thermal_margin_c,
            "is_thermal_compliant": report.is_thermal_compliant,
        },
    }

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    with open(RESULT_PATH, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)

    return payload


def main() -> None:
    results = run_packaging_signoff_extract()
    print("=" * 95)
    print("CHAPTER 0067: FCBGA-676 PACKAGING, 4-2-4 SUBSTRATE & THERMAL SPREADER (GATE R17)")
    print("=" * 95)
    print(f"Status: {results['status']} | Claim Level: {results['claim_level']}\n")
    p = results["fcbga676_package"]
    b = results["ball_map_allocations"]
    print("1. FCBGA-676 Package Architecture:")
    print(f"  • Package Size: {p['body_width_mm']:.1f} × {p['body_height_mm']:.1f} mm ({p['total_bga_balls']} BGA Balls @ {p['ball_pitch_mm']:.2f} mm pitch)")
    print(f"  • C4 Bump Grid: {p['c4_bump_count']} bumps @ {p['c4_bump_pitch_um']:.0f} µm pitch | Die Area: {p['die_area_mm2']:.2f} mm²")
    print(f"  • Ball Map: {b['vss_ground_balls']} VSS | {b['vdd_dig_core_balls']} VDD_DIG | {b['vdd_ana_analog_balls']} VDD_ANA | {b['pcie_gen5_serdes_balls']} PCIe Gen5\n")
    s = results["substrate_stackup"]
    print("2. 4-2-4 Organic Substrate Stackup:")
    print(f"  • Stackup: {s['buildup_structure']} ({s['layer_count']} Cu Layers | Core: {s['core_thickness_um']:.0f} µm)")
    print(f"  • Controlled Impedance: Zo = {s['single_ended_impedance_ohm']:.1f} Ω | Zdiff(PCIe) = {s['differential_pcie_impedance_ohm']:.1f} Ω (Loss Tan: {s['loss_tangent']})\n")
    t = results["thermal_signoff"]
    print("3. Thermal Resistance & Junction Temperature Signoff:")
    print(f"  • Thermal Resistances: θ_jc = {t['theta_jc_c_per_w']:.3f} °C/W | θ_ca = {t['theta_ca_c_per_w']:.3f} °C/W | θ_ja = {t['theta_ja_c_per_w']:.3f} °C/W")
    print(f"  • Peak Junction Temp: {t['peak_junction_temp_c']:.2f} °C (Budget: ≤ {t['max_junction_temp_budget_c']:.1f} °C under {t['chip_tdp_w']:.1f}W TDP @ Tamb = {t['ambient_temp_c']:.1f} °C)")
    print(f"  • Thermal Margin: +{t['thermal_margin_c']:.2f} °C Headroom | Compliant: {t['is_thermal_compliant']}")
    print("=" * 95)
    print(f"Extracted artifact saved to: {RESULT_PATH}\n")


if __name__ == "__main__":
    main()
