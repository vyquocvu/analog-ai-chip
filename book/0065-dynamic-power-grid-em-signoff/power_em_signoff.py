r"""Chapter 0065 — Dynamic Power Grid Resonance & Electromigration Signoff (Gate R16 Closure).

Evaluates RLC power distribution network (PDN) impedance profiling, simultaneous switching noise (SSN),
and copper electromigration reliability via Black's equation, closing Gate R16.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

_REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO))

from analog_layout.dynamic_power_em import (
    ElectromigrationParameters,
    PDNParameters,
    run_dynamic_power_em_signoff,
)

RESULTS_DIR = _REPO / "verification" / "layout" / "results"
RESULT_PATH = RESULTS_DIR / "dynamic-power-em-0065-extract.json"


def run_power_em_signoff_extract() -> dict[str, Any]:
    """Execute dynamic PDN resonance and EM signoff extraction."""
    pdn = PDNParameters()
    em = ElectromigrationParameters()

    report = run_dynamic_power_em_signoff(pdn, em)

    payload: dict[str, Any] = {
        "chapter": "0065-dynamic-power-grid-em-signoff",
        "gate": "R16",
        "work_package": "WP16.3",
        "status": "PASSED" if (report.is_pdn_clean and report.is_em_clean) else "FAILED",
        "claim_level": "physical/pdn-em-signoff",
        "pdn_resonance_signoff": {
            "is_pdn_clean": report.is_pdn_clean,
            "resonance_frequency_ghz": report.resonance_frequency_ghz,
            "clock_frequency_ghz": pdn.clock_frequency_ghz,
            "frequency_margin_ratio": report.frequency_margin_ratio,
            "peak_anti_resonance_impedance_mohm": report.peak_anti_resonance_impedance_mohm,
            "target_impedance_mohm": pdn.target_impedance_mohm,
            "on_chip_decap_pf_per_cluster": pdn.decap_per_cluster_pf,
            "mesh_loop_inductance_ph": pdn.grid_loop_inductance_ph,
        },
        "ssn_noise_signoff": {
            "inductive_bounce_mv": report.inductive_bounce_mv,
            "static_ir_drop_mv": report.metadata["static_ir_drop_mv"],
            "total_dynamic_voltage_drop_mv": report.total_dynamic_voltage_drop_mv,
            "dynamic_drop_pct_of_vdd": report.dynamic_drop_pct_of_vdd,
            "voltage_noise_budget_mv": 50.0,
            "is_ssn_safe": report.total_dynamic_voltage_drop_mv <= 50.0,
        },
        "electromigration_signoff": {
            "is_em_clean": report.is_em_clean,
            "max_current_density_ma_per_um": report.max_current_density_ma_per_um,
            "foundry_em_limit_ma_per_um": em.current_density_limit_ma_per_um,
            "em_safety_margin_ratio": report.em_safety_margin_ratio,
            "junction_temperature_c": report.metadata["junction_temperature_c"],
            "projected_mttf_years": report.projected_mttf_years,
            "target_lifetime_years": em.target_lifetime_years,
            "activation_energy_ev": report.metadata["copper_activation_energy_ev"],
        },
    }

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    with open(RESULT_PATH, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)

    return payload


def main() -> None:
    results = run_power_em_signoff_extract()
    print("=" * 95)
    print("CHAPTER 0065: DYNAMIC POWER GRID RESONANCE & EM SIGNOFF (GATE R16 CLOSURE)")
    print("=" * 95)
    print(f"Status: {results['status']} | Claim Level: {results['claim_level']}\n")
    p = results["pdn_resonance_signoff"]
    print("1. RLC Power Grid Resonance Signoff:")
    print(f"  • Resonance Frequency: {p['resonance_frequency_ghz']:.2f} GHz (Margin: {p['frequency_margin_ratio']:.2f}x above {p['clock_frequency_ghz']:.1f} GHz NoC Clock)")
    print(f"  • Peak Anti-Resonance Impedance: {p['peak_anti_resonance_impedance_mohm']:.1f} mΩ (Target: ≤ {p['target_impedance_mohm']:.1f} mΩ)")
    print(f"  • On-Chip Decap: {p['on_chip_decap_pf_per_cluster']:.1f} pF/cluster | Mesh Loop Inductance: {p['mesh_loop_inductance_ph']:.1f} pH\n")
    s = results["ssn_noise_signoff"]
    print("2. Simultaneous Switching Noise (SSN) Signoff:")
    print(f"  • Inductive Bounce (L*di/dt): {s['inductive_bounce_mv']:.2f} mV | Static IR Drop: {s['static_ir_drop_mv']:.2f} mV")
    print(f"  • Total Dynamic Voltage Drop: {s['total_dynamic_voltage_drop_mv']:.2f} mV ({s['dynamic_drop_pct_of_vdd']:.2f}% of VDD <= {s['voltage_noise_budget_mv']:.1f} mV budget)\n")
    e = results["electromigration_signoff"]
    print("3. Electromigration (EM) Lifetime Signoff (Black's Equation):")
    print(f"  • Peak Current Density: {e['max_current_density_ma_per_um']:.2f} mA/µm (Foundry Limit: {e['foundry_em_limit_ma_per_um']:.2f} mA/µm | Margin: {e['em_safety_margin_ratio']:.2f}x)")
    print(f"  • Projected MTTF: {e['projected_mttf_years']:.1f} Years at Tj = {e['junction_temperature_c']:.0f}°C (Target: ≥ {e['target_lifetime_years']:.1f} Years)")
    print("=" * 95)
    print(f"Extracted artifact saved to: {RESULT_PATH}\n")


if __name__ == "__main__":
    main()
