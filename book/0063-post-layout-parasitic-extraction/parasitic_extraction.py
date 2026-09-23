r"""Chapter 0063 — Post-Layout Parasitic Extraction (PEX/SPEF) & Crossbar Settling (Gate R16).

Estimates geometry-based RC totals and analytical single-pole settling using
assumed coefficients. Does not run ngspice or establish physical signoff.
"""

from __future__ import annotations

import json
import math
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
    """Write a deterministic assumed-model estimate, not physical signoff."""
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
        "claim_level": "analytical_single_pole",
        "evidence_class": "assumed",
        "physical_verified": False,
        "model_metadata": settling_report.metadata,
        "limitations": [
            "No ngspice run, distributed RC solve, or physical verification.",
            "PEX coefficients, 1.18 ns baseline and 0.40 ns increment are assumed.",
            "Averaged RC totals do not preserve bitline topology or worst-case paths.",
            "No PVT, noise, ringing or bit-error-rate verification.",
            "transient_settling_signoff is a legacy key for an analytical estimate only.",
        ],
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
            "target_accuracy_pct": settling_report.target_accuracy_pct,
            "target_settling_time_ns": settling_report.target_settling_time_ns,
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


def generate_figures(results: dict[str, Any]) -> None:
    """Render deterministic SVGs directly from the analytical extract."""
    directory = Path(__file__).resolve().parent / "diagrams"
    s = results["transient_settling_signoff"]
    p = results["pex_extraction_summary"]
    header = '<svg xmlns="http://www.w3.org/2000/svg" width="800" height="420" viewBox="0 0 800 420">'
    style = '<rect width="800" height="420" fill="white"/><g font-family="sans-serif" fill="#172b4d">'
    summary = [
        "Geometry-based RC estimate — assumed coefficients",
        f"Nets: {p['total_nets_extracted']} | R total: {p['total_parasitic_res_ohm']:.2f} ohm",
        f"C total: {p['total_parasitic_cap_ff']:.2f} fF",
        "Average RC totals → lumped single-pole estimate",
        f"tau = 1.18 ns + 0.40 ns + RC correction = {s['post_layout_tau_ns']:.5f} ns",
        f"99.9% settling: {s['settling_99_9_time_ns']:.2f} ns; aperture: {s['sampling_window_ns']:.2f} ns",
        f"Target margin: {s['timing_margin_ratio']:.3f}x — {results['status']}",
        "No ngspice, distributed transient solve, or physical signoff",
    ]
    text = ''.join(f'<text x="35" y="{45 + i * 45}" font-size="17">{line}</text>'
                   for i, line in enumerate(summary))
    (directory / "parasitic-extraction.svg").write_text(header + style + text + '</g></svg>')

    # Time 0–15 ns, normalized response 0–1; no simulated waveform samples.
    points = ' '.join(
        f'{70 + 660 * i / 300:.3f},{330 - 240 * (1 - math.exp(-(15 * i / 300) / s["post_layout_tau_ns"])):.3f}'
        for i in range(301)
    )
    waveform = [
        '<text x="35" y="35" font-size="20">Analytical single-pole response (assumed tau)</text>',
        '<text x="35" y="62" font-size="16">y(t) = 1 − exp(−t/tau); not a SPICE waveform</text>',
        '<path d="M70 90 V330 H730" fill="none" stroke="#172b4d"/>',
        f'<polyline points="{points}" fill="none" stroke="#007b83" stroke-width="3"/>',
        '<text x="35" y="95">1.0</text><text x="45" y="335">0</text>',
    ]
    for time in range(0, 16, 5):
        x = 70 + 44 * time
        waveform.append(f'<text x="{x}" y="355">{time} ns</text>')
    for time, label, y in [
        (s["sampling_window_ns"], f"Aperture {s['sampling_window_ns']:.2f} ns", 180),
        (s["settling_99_9_time_ns"], f"99.9%: {s['settling_99_9_time_ns']:.2f} ns", 220),
    ]:
        x = 70 + 44 * time
        waveform.append(f'<path d="M{x:.3f} 90 V330" stroke="#b34700" stroke-dasharray="5 5"/>')
        waveform.append(f'<text x="{x + 8:.3f}" y="{y}">{label}</text>')
    waveform.append('<text x="70" y="395">99.9% target fails the 5 ns aperture; no physical verification.</text>')
    (directory / "transient-settling-waveform.svg").write_text(header + style + ''.join(waveform) + '</g></svg>')


def main() -> None:
    results = run_parasitic_extraction_extract()
    generate_figures(results)
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
    print("Analytical Single-Pole Settling (assumed; not physical signoff):")
    print(f"  • Pre-Layout Time Constant (Tau): {s['pre_layout_tau_ns']:.2f} ns")
    print(f"  • Post-Layout Time Constant (Tau): {s['post_layout_tau_ns']:.2f} ns (+{s['settling_degradation_pct']:.1f}% degradation)")
    print(f"  • 99.9% Settling Time: {s['settling_99_9_time_ns']:.2f} ns (Budget: ≤ {s['sampling_window_ns']:.2f} ns @ {s['sampling_frequency_mhz']:.0f} MSPS)")
    print(f"  • Timing Margin Ratio: {s['timing_margin_ratio']:.2f}x | Settling Clean: {s['is_settling_clean']}")
    print("=" * 95)
    print(f"Extracted artifact saved to: {RESULT_PATH}\n")


if __name__ == "__main__":
    main()
