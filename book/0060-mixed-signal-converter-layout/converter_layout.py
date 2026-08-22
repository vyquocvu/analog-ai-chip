r"""Chapter 0060 — Mixed-Signal SAR ADC / DAC Layout & LVS Signoff (Gate R15).

Generates the 2D common-centroid differential CDAC layout, builds the 8-bit SAR ADC
mixed-signal macro, and performs Design Rule Checking (DRC) and Layout-Versus-Schematic (LVS) signoff.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

_REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO))

from analog_layout.converter_layout import (
    CDACArrayConfig,
    SARADCLayoutConfig,
    generate_cdac_layout,
    generate_sar_adc_layout,
)
from analog_layout.drc import run_drc
from analog_layout.lvs import build_golden_sar_adc_schematic, run_lvs

RESULTS_DIR = _REPO / "verification" / "layout" / "results"
RESULT_PATH = RESULTS_DIR / "converter-layout-0060-extract.json"


def run_converter_layout_extract() -> dict[str, Any]:
    """Execute converter layout synthesis, DRC, and LVS signoff extraction."""
    cdac_cfg = CDACArrayConfig()
    _cdac_cell, cdac_meta = generate_cdac_layout(cdac_cfg)

    adc_cfg = SARADCLayoutConfig(cdac_config=cdac_cfg)
    adc_cell = generate_sar_adc_layout(adc_cfg)

    drc_report = run_drc(adc_cell)
    golden_sch = build_golden_sar_adc_schematic(adc_cfg.resolution_bits)
    lvs_report = run_lvs(adc_cell, schematic=golden_sch)

    payload: dict[str, Any] = {
        "chapter": "0060-mixed-signal-converter-layout",
        "gate": "R15",
        "work_package": "WP15.2",
        "status": "PASSED" if (drc_report.is_clean and lvs_report.is_matched) else "FAILED",
        "claim_level": "physical/layout-lvs",
        "converter_specifications": {
            "name": adc_cell.name,
            "resolution_bits": adc_cfg.resolution_bits,
            "total_silicon_area_um2": adc_cell.metadata["total_area_um2"],
            "target_area_budget_um2": adc_cfg.target_area_um2,
            "is_within_area_budget": adc_cell.metadata["is_within_area_budget"],
            "port_count": len(adc_cell.ports),
            "cdac_common_centroid": {
                "unit_caps_total": cdac_meta["unit_caps_total"],
                "pos_caps": cdac_meta["pos_cap_count"],
                "neg_caps": cdac_meta["neg_cap_count"],
                "pos_centroid_nm": cdac_meta["pos_centroid_nm"],
                "neg_centroid_nm": cdac_meta["neg_centroid_nm"],
                "centroid_offset_nm": cdac_meta["centroid_offset_nm"],
                "is_perfect_centroid_matched": cdac_meta["is_perfect_centroid_matched"],
            },
        },
        "drc_signoff": {
            "is_clean": drc_report.is_clean,
            "total_checks": drc_report.total_checks,
            "violation_count": drc_report.violation_count,
        },
        "lvs_signoff": {
            "is_matched": lvs_report.is_matched,
            "matched_devices": lvs_report.matched_devices,
            "matched_ports": lvs_report.matched_ports,
            "matched_nets": lvs_report.matched_nets,
            "discrepancy_count": lvs_report.discrepancy_count,
            "discrepancies": lvs_report.discrepancies,
        },
    }

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    with open(RESULT_PATH, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)

    return payload


def main() -> None:
    results = run_converter_layout_extract()
    print("=" * 95)
    print("CHAPTER 0060: MIXED-SIGNAL SAR ADC / DAC LAYOUT & LVS SIGNOFF (GATE R15)")
    print("=" * 95)
    print(f"Status: {results['status']} | Claim Level: {results['claim_level']}\n")
    c = results["converter_specifications"]
    print("Converter Physical Specifications:")
    print(f"  • Macro Name: {c['name']} ({c['resolution_bits']}-bit Mixed-Signal SAR ADC)")
    print(f"  • Total Area: {c['total_silicon_area_um2']:.1f} µm² (Budget: ≤ {c['target_area_budget_um2']:.1f} µm² | Within Budget: {c['is_within_area_budget']})")
    print(f"  • CDAC Grid: {c['cdac_common_centroid']['unit_caps_total']} unit MIM capacitors (128 C+ / 128 C-)")
    print(f"  • Centroid Offset: {c['cdac_common_centroid']['centroid_offset_nm']:.2f} nm (Common-Centroid Matched: {c['cdac_common_centroid']['is_perfect_centroid_matched']})\n")
    drc = results["drc_signoff"]
    lvs = results["lvs_signoff"]
    print("Verification Signoff Summary:")
    print(f"  • DRC Clean: {drc['is_clean']} (Checks: {drc['total_checks']} | Violations: {drc['violation_count']})")
    print(f"  • LVS Matched: {lvs['is_matched']} (Matched Devices: {lvs['matched_devices']} | Matched Ports: {lvs['matched_ports']} | Discrepancies: {lvs['discrepancy_count']})")
    print("=" * 95)
    print(f"Extracted artifact saved to: {RESULT_PATH}\n")


if __name__ == "__main__":
    main()
