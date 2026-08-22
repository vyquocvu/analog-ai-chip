r"""Chapter 0059 — 28nm BEOL ReRAM Macro Physical Layout & DRC Signoff (Gate R15).

Synthesizes the physical GDSII-compatible cell geometry for a 16x16 ReRAM macro
with 160nm pitch and performs Design Rule Checking (DRC) signoff.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

_REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO))

from analog_layout.drc import DesignRules28nm, run_drc
from analog_layout.reram_macro import ReRAMArrayConfig, generate_reram_macro_cell

RESULTS_DIR = _REPO / "verification" / "layout" / "results"
RESULT_PATH = RESULTS_DIR / "reram-macro-0059-extract.json"


def run_reram_macro_layout_extract() -> dict[str, Any]:
    """Execute ReRAM macro cell generation and DRC signoff extract."""
    cfg = ReRAMArrayConfig(
        rows=16,
        cols=16,
        cell_pitch_nm=160,
        wordline_width_nm=60,
        bitline_width_nm=60,
        reram_via_size_nm=32,
        dummy_rings=1,
    )
    cell = generate_reram_macro_cell(cfg)
    rules = DesignRules28nm()
    drc_report = run_drc(cell, rules)

    payload: dict[str, Any] = {
        "chapter": "0059-reram-macro-layout",
        "gate": "R15",
        "work_package": "WP15.1",
        "status": "PASSED" if drc_report.is_clean else "FAILED",
        "claim_level": "physical/layout-drc",
        "process_technology": "28nm BEOL Via4-M5 ReRAM",
        "macro_geometry": {
            "name": cell.name,
            "core_rows": cfg.rows,
            "core_cols": cfg.cols,
            "cell_pitch_nm": cfg.cell_pitch_nm,
            "wordline_width_nm": cfg.wordline_width_nm,
            "bitline_width_nm": cfg.bitline_width_nm,
            "reram_via_size_nm": cfg.reram_via_size_nm,
            "array_width_um": cell.metadata["array_width_um"],
            "array_height_um": cell.metadata["array_height_um"],
            "macro_area_um2": cell.metadata["macro_area_um2"],
            "total_rectangles": len(cell.rectangles),
            "total_ports": len(cell.ports),
            "total_active_crosspoints": cell.metadata["total_active_crosspoints"],
        },
        "drc_signoff": {
            "is_clean": drc_report.is_clean,
            "total_checks": drc_report.total_checks,
            "violation_count": drc_report.violation_count,
            "violations": [
                {
                    "rule": v.rule_name,
                    "layer": v.layer.name,
                    "message": v.message,
                }
                for v in drc_report.violations
            ],
            "metal_densities_pct": drc_report.metal_densities,
        },
    }

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    with open(RESULT_PATH, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)

    return payload


def main() -> None:
    results = run_reram_macro_layout_extract()
    print("=" * 95)
    print("CHAPTER 0059: 28NM BEOL RERAM MACRO PHYSICAL LAYOUT & DRC SIGNOFF (GATE R15)")
    print("=" * 95)
    print(f"Status: {results['status']} | Claim Level: {results['claim_level']}")
    print(f"Process Technology: {results['process_technology']}\n")
    g = results["macro_geometry"]
    print("Physical Macro Specifications:")
    print(f"  • Core Array: {g['core_rows']}x{g['core_cols']} ({g['total_active_crosspoints']} active memristor crosspoints)")
    print(f"  • Cell Pitch: {g['cell_pitch_nm']} nm | Dimensions: {g['array_width_um']:.2f} µm x {g['array_height_um']:.2f} µm")
    print(f"  • Total Area: {g['macro_area_um2']:.2f} µm² | Shape Count: {g['total_rectangles']}")
    print(f"  • Ports: {g['total_ports']} IO pins (16 Wordlines + 16 Bitlines)\n")
    drc = results["drc_signoff"]
    print("DRC Signoff Summary:")
    print(f"  • DRC Clean: {drc['is_clean']} | Checks Executed: {drc['total_checks']} | Violations: {drc['violation_count']}")
    print(f"  • Metal 4 Density: {drc['metal_densities_pct'].get('METAL4', 0):.1f}% | Metal 5 Density: {drc['metal_densities_pct'].get('METAL5', 0):.1f}%")
    print("=" * 95)
    print(f"Extracted artifact saved to: {RESULT_PATH}\n")


if __name__ == "__main__":
    main()
