r"""Chapter 0063 — Post-Layout Parasitic Extraction (PEX/SPEF) & Crossbar Settling (Gate R16).

Extracts distributed RC parasitics from 28nm BEOL physical layout into standard SPEF format,
simulates analog post-layout settling dynamics, and validates SAR ADC sampling margin.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

_REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO))

from analog_layout.pex import PEXTechnologyProfile, extract_spef_from_cell
from analog_layout.post_layout_sim import (
    PostLayoutSettlingConfig,
    simulate_crossbar_post_layout_settling,
)
from analog_layout.reram_macro import ReRAMArrayConfig, generate_reram_macro_cell

RESULTS_DIR = _REPO / "verification" / "layout" / "results"
RESULT_PATH = RESULTS_DIR / "parasitic-extraction-0063-extract.json"


def run_parasitic_extraction_extract() -> dict[str, Any]:
    """Execute SPEF extraction and post-layout settling signoff extraction."""
    reram_cfg = ReRAMArrayConfig(rows=16, cols=16)
    cell = generate_reram_macro_cell(reram_cfg)

    # 1. PEX Extraction
    pex_profile = PEXTechnologyProfile()
    spef = extract_spef_from_cell(cell, pex_profile)

    # 2. Post-Layout Transient Settling Simulation
    sim_cfg = PostLayoutSettlingConfig(sampling_window_ns=5.0)
    settling_report = simulate_crossbar_post_layout_settling(spef, sim_cfg)

    payload: dict[str, Any] = {
        "chapter": "0063-post-layout-parasitic-extraction",
        "gate": "R16",
        "work_package": "WP16.1",
        "status": "PASSED" if settling_report.is_settling_clean else "FAILED",
        "claim_level": "physical/pex-settling",
        "cell_name": cell.name,
        "pex_extraction_summary": {
            "total_nets_extracted": len(spef.nets),
            "total_parasitic_cap_ff": spef.total_parasitic_cap_ff,
            "total_parasitic_res_ohm": spef.total_parasitic_res_ohm,
            "avg_net_capacitance_ff": spef.metadata.get("avg_wire_capacitance_ff", spef.total_parasitic_cap_ff / max(1, len(spef.nets))),
            "avg_net_resistance_ohm": spef.metadata.get("avg_wire_resistance_ohm", spef.total_parasitic_res_ohm / max(1, len(spef.nets))),
            "technology_node": "28nm BEOL Via4-M5 ReRAM",
        },
        "transient_settling_signoff": {
            "pre_layout_tau_ns": settling_report.pre_layout_tau_ns,
            "post_layout_tau_ns": settling_report.post_layout_tau_ns,
            "settling_degradation_pct": settling_report.settling_degradation_pct,
            "settling_90_time_ns": settling_report.settling_90_time_ns,
            "settling_99_9_time_ns": settling_report.settling_99_9_time_ns,
            "sampling_window_ns": settling_report.sampling_window_ns,
            "timing_margin_ratio": settling_report.timing_margin_ratio,
            "is_settling_clean": settling_report.is_settling_clean,
            "sampling_frequency_mhz": settling_report.metadata["sampling_frequency_mhz"],
        },
    }

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    with open(RESULT_PATH, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)

    return payload


def main() -> None:
    results = run_parasitic_extraction_extract()
    print("=" * 95)
    print("CHAPTER 0063: POST-LAYOUT PARASITIC EXTRACTION (PEX/SPEF) & CROSSBAR SETTLING (GATE R16)")
    print("=" * 95)
    print(f"Status: {results['status']} | Claim Level: {results['claim_level']}\n")
    p = results["pex_extraction_summary"]
    print("PEX Extraction Summary:")
    print(f"  • Extracted Nets: {p['total_nets_extracted']} | Tech Node: {p['technology_node']}")
    print(f"  • Total Parasitic Capacitance: {p['total_parasitic_cap_ff']:.2f} fF (Avg: {p['avg_net_capacitance_ff']:.2f} fF/net)")
    print(f"  • Total Parasitic Resistance: {p['total_parasitic_res_ohm']:.2f} Ω (Avg: {p['avg_net_resistance_ohm']:.2f} Ω/net)\n")
    s = results["transient_settling_signoff"]
    print("Transient Settling & Timing Margin Signoff:")
    print(f"  • Pre-Layout Time Constant (Tau): {s['pre_layout_tau_ns']:.2f} ns")
    print(f"  • Post-Layout Time Constant (Tau): {s['post_layout_tau_ns']:.2f} ns (+{s['settling_degradation_pct']:.1f}% degradation)")
    print(f"  • 99.9% Settling Time: {s['settling_99_9_time_ns']:.2f} ns (Budget: ≤ {s['sampling_window_ns']:.2f} ns @ {s['sampling_frequency_mhz']:.0f} MSPS)")
    print(f"  • Timing Margin Ratio: {s['timing_margin_ratio']:.2f}x | Settling Clean: {s['is_settling_clean']}")
    print("=" * 95)
    print(f"Extracted artifact saved to: {RESULT_PATH}\n")


if __name__ == "__main__":
    main()
