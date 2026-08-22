r"""Chapter 0066 — GDSII / OASIS Stream-Out & 28nm Foundry Tape-Out Signoff (Gate R17).

Executes CMP dummy metal fill synthesis, evaluates spatial density gradients, validates
GDSII layer mapping, and formally signs off the 10-point 28nm foundry tape-out checklist.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

_REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO))

from analog_layout.full_chip import generate_full_chip_assembly
from analog_layout.tapeout import run_tapeout_signoff

RESULTS_DIR = _REPO / "verification" / "layout" / "results"
RESULT_PATH = RESULTS_DIR / "tapeout-0066-extract.json"


def run_tapeout_signoff_extract() -> dict[str, Any]:
    """Execute GDSII streamout synthesis and master tapeout signoff."""
    chip_cell = generate_full_chip_assembly()
    report = run_tapeout_signoff(chip_cell)

    payload: dict[str, Any] = {
        "chapter": "0066-gdsii-streamout-tapeout-signoff",
        "gate": "R17",
        "work_package": "WP17.1",
        "status": "PASSED" if report.is_tapeout_ready else "FAILED",
        "claim_level": "physical/tapeout-signoff",
        "tapeout_overview": {
            "is_tapeout_ready": report.is_tapeout_ready,
            "chip_target": report.chip_target,
            "process_node": report.process_node,
            "die_area_mm2": report.die_area_mm2,
            "shuttle_type": report.metadata["shuttle_type"],
            "reticle_limit_mm2": report.metadata["reticle_limit_mm2"],
        },
        "gdsii_streamout_package": {
            "format": report.streamout_summary.format,
            "total_structures": report.streamout_summary.total_structures,
            "total_polygons": report.streamout_summary.total_polygons,
            "total_ports": report.streamout_summary.total_ports,
            "layer_count": report.streamout_summary.layer_count,
            "file_size_mb": report.streamout_summary.file_size_mb,
            "checksum_sha256": report.streamout_summary.checksum_sha256,
        },
        "cmp_density_summary": [
            {
                "layer": rep.layer.name,
                "pre_fill_density_pct": rep.pre_fill_density_pct,
                "post_fill_density_pct": rep.post_fill_density_pct,
                "max_spatial_gradient_pct": rep.max_spatial_gradient_pct,
                "density_compliant": rep.is_density_compliant,
                "gradient_compliant": rep.is_gradient_compliant,
            }
            for rep in report.density_reports.values()
        ],
        "foundry_checklist": [
            {
                "index": item.index,
                "name": item.name,
                "category": item.category,
                "specification": item.specification,
                "actual_value": item.actual_value,
                "passed": item.is_passed,
            }
            for item in report.checklist
        ],
    }

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    with open(RESULT_PATH, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)

    return payload


def main() -> None:
    results = run_tapeout_signoff_extract()
    print("=" * 95)
    print("CHAPTER 0066: GDSII STREAM-OUT & 28NM FOUNDRY TAPE-OUT SIGNOFF (GATE R17)")
    print("=" * 95)
    print(f"Status: {results['status']} | Claim Level: {results['claim_level']}\n")
    t = results["tapeout_overview"]
    print("Tape-Out Overview:")
    print(f"  • Chip Target: {t['chip_target']} | Process Node: {t['process_node']}")
    print(f"  • Die Area: {t['die_area_mm2']:.2f} mm² (Reticle Limit: ≤ {t['reticle_limit_mm2']:.1f} mm²)")
    print(f"  • Shuttle Type: {t['shuttle_type']} | Tapeout Ready: {t['is_tapeout_ready']}\n")
    g = results["gdsii_streamout_package"]
    print("GDSII / OASIS Stream-Out Package:")
    print(f"  • Format: {g['format']} | Total Polygons: {g['total_polygons']} | Layers: {g['layer_count']}")
    print(f"  • Estimated Package Size: {g['file_size_mb']:.1f} MB | SHA-256: {g['checksum_sha256'][:16]}...\n")
    print("10-Point Foundry Signoff Checklist:")
    for item in results["foundry_checklist"]:
        mark = "✓ PASS" if item["passed"] else "✗ FAIL"
        print(f"  [{item['index']:>2}] {item['name']:<42}: {mark} ({item['actual_value']})")
    print("=" * 95)
    print(f"Extracted artifact saved to: {RESULT_PATH}\n")


if __name__ == "__main__":
    main()
