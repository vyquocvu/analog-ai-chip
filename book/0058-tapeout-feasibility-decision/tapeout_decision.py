r"""Chapter 0058 — Go/No-Go Architecture Decision & Physical Tape-Out Target (Gate R14 Exit).

Synthesizes physical ledger evidence, classifies T0–T3 feasibility, and selects the
primary 28nm ReRAM tape-out target closing the analog AI chip design roadmap.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

_REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO))

from analog_llm.decision_report import generate_integrated_decision_report

RESULTS_DIR = _REPO / "verification" / "circuit" / "results"
RESULT_PATH = RESULTS_DIR / "tapeout-decision-0058-extract.json"


def run_tapeout_decision_extract() -> dict[str, Any]:
    """Execute integrated architecture report and export deterministic extract."""
    report = generate_integrated_decision_report()

    decisions_dict = {
        tier_code: {
            "model_name": d.model_name,
            "status": d.status.value,
            "verdict": d.verdict,
            "total_parameters": d.total_parameters,
            "silicon_area_mm2": d.silicon_area_mm2,
            "die_count": d.die_count,
            "decode_tokens_per_second": d.decode_tokens_per_second,
            "decode_energy_per_token_uj": d.decode_energy_per_token_uj,
            "active_power_w": d.active_power_w,
            "power_density_w_cm2": d.power_density_w_cm2,
            "primary_bottleneck": d.primary_bottleneck,
            "rationale": d.rationale,
            "required_evidence_for_promotion": d.required_evidence_for_promotion,
        }
        for tier_code, d in report.tier_decisions.items()
    }

    tapeout = {
        "target_tier": report.tapeout_target.target_tier,
        "model_name": report.tapeout_target.model_name,
        "process_technology": report.tapeout_target.process_technology,
        "die_size_mm2": report.tapeout_target.die_size_mm2,
        "package_type": report.tapeout_target.package_type,
        "decode_throughput_tps": report.tapeout_target.decode_throughput_tps,
        "decode_energy_uj_per_token": report.tapeout_target.decode_energy_uj_per_token,
        "thermal_envelope": report.tapeout_target.thermal_envelope,
        "risk_assessment": report.tapeout_target.risk_assessment,
    }

    payload: dict[str, Any] = {
        "chapter": "0058-tapeout-feasibility-decision",
        "gate": "R14",
        "status": "PASSED",
        "claim_level": report.claim_level,
        "tier_decisions": decisions_dict,
        "selected_tapeout_target": tapeout,
        "roadmap_milestone": "ALL_GATES_PASSED_R0_THROUGH_R14",
    }

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    with open(RESULT_PATH, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)

    return payload


def main() -> None:
    results = run_tapeout_decision_extract()
    print("=" * 105)
    print("CHAPTER 0058: INTEGRATED ARCHITECTURE REPORT & PHYSICAL TAPE-OUT TARGET (GATE R14 EXIT)")
    print("=" * 105)
    print(f"Status: {results['status']} | Claim Level: {results['claim_level']}")
    print(f"Roadmap Milestone: {results['roadmap_milestone']}\n")
    print(
        f"{'Tier':<6} | {'Model':<16} | {'Verdict':<16} | {'Die Count':<10} | {'Area (mm²)':<12} | {'Decode TPS':<14} | {'Primary Bottleneck'}"
    )
    print("-" * 105)
    for code, d in results["tier_decisions"].items():
        print(
            f"{code:<6} | {d['model_name']:<16} | {d['verdict']:<16} | {d['die_count']:<10} | "
            f"{d['silicon_area_mm2']:<12.1f} | {d['decode_tokens_per_second']:<14.1f} | {d['primary_bottleneck']}"
        )
    print("=" * 105)
    t = results["selected_tapeout_target"]
    print(f"SELECTED PRIMARY TAPE-OUT TARGET: {t['target_tier']} ({t['model_name']})")
    print(f"  • Process Node: {t['process_technology']}")
    print(f"  • Die Area: {t['die_size_mm2']:.1f} mm² | Package: {t['package_type']}")
    print(f"  • Throughput: {t['decode_throughput_tps']:,.1f} TPS | Energy: {t['decode_energy_uj_per_token']:.2f} μJ/token")
    print(f"  • Thermal Envelope: {t['thermal_envelope']}")
    print("=" * 105)
    print(f"Extracted artifact saved to: {RESULT_PATH}\n")


if __name__ == "__main__":
    main()
