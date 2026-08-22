r"""Chapter 0064 — Multi-Corner PVT Static Timing Analysis (STA) Signoff (Gate R16).

Performs gate-level and interconnect static timing analysis across PVT corners (TT/SS/FF,
-40°C to 125°C), evaluates setup/hold slacks on NoC and IMC domains, and signs off timing margins.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

_REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO))

from analog_layout.sta import (
    get_critical_timing_paths,
    get_standard_clock_domains,
    get_standard_pvt_corners,
    run_static_timing_analysis,
)

RESULTS_DIR = _REPO / "verification" / "layout" / "results"
RESULT_PATH = RESULTS_DIR / "sta-signoff-0064-extract.json"


def run_sta_signoff_extract() -> dict[str, Any]:
    """Execute multi-corner STA signoff extraction."""
    corners = get_standard_pvt_corners()
    clks = get_standard_clock_domains()
    paths = get_critical_timing_paths()

    sta_report = run_static_timing_analysis(corners, clks, paths)

    payload: dict[str, Any] = {
        "chapter": "0064-multi-corner-sta-signoff",
        "gate": "R16",
        "work_package": "WP16.2",
        "status": "PASSED" if sta_report.is_timing_clean else "FAILED",
        "claim_level": "physical/sta-signoff",
        "timing_signoff_summary": {
            "is_timing_clean": sta_report.is_timing_clean,
            "total_paths_analyzed": sta_report.total_paths_checked,
            "total_timing_checks": sta_report.total_checks_executed,
            "corners_evaluated": sta_report.corners_evaluated,
            "worst_setup_slack_ps": sta_report.worst_setup_slack_ps,
            "worst_hold_slack_ps": sta_report.worst_hold_slack_ps,
            "wns_setup_ps": sta_report.wns_setup_ps,
            "wns_hold_ps": sta_report.wns_hold_ps,
            "tns_setup_ps": sta_report.tns_setup_ps,
            "tns_hold_ps": sta_report.tns_hold_ps,
            "cdc_synchronizer_mtbf_years": sta_report.metadata["cdc_synchronizer_mtbf_years"],
        },
        "clock_domains": [
            {
                "name": clk.name,
                "frequency_mhz": clk.frequency_mhz,
                "period_ps": clk.period_ps,
                "clock_skew_ps": clk.clock_skew_ps,
            }
            for clk in clks.values()
        ],
        "critical_path_results": [
            {
                "path_name": r.path_name,
                "corner": r.corner_name,
                "clock_domain": r.clock_domain,
                "data_delay_ps": r.data_delay_ps,
                "setup_slack_ps": r.setup_slack_ps,
                "hold_slack_ps": r.hold_slack_ps,
                "setup_pass": r.is_setup_passed,
                "hold_pass": r.is_hold_passed,
            }
            for r in sta_report.critical_paths
        ],
    }

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    with open(RESULT_PATH, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)

    return payload


def main() -> None:
    results = run_sta_signoff_extract()
    print("=" * 95)
    print("CHAPTER 0064: MULTI-CORNER PVT STATIC TIMING ANALYSIS (STA) SIGNOFF (GATE R16)")
    print("=" * 95)
    print(f"Status: {results['status']} | Claim Level: {results['claim_level']}\n")
    s = results["timing_signoff_summary"]
    print("STA Signoff Summary:")
    print(f"  • Timing Clean: {s['is_timing_clean']} | Corners Evaluated: {', '.join(s['corners_evaluated'])}")
    print(f"  • Paths Checked: {s['total_paths_analyzed']} | Total Checks: {s['total_timing_checks']}")
    print(f"  • Worst Setup Slack: +{s['worst_setup_slack_ps']:.1f} ps (WNS: {s['wns_setup_ps']:.1f} ps | TNS: {s['tns_setup_ps']:.1f} ps)")
    print(f"  • Worst Hold Slack: +{s['worst_hold_slack_ps']:.1f} ps (WNS: {s['wns_hold_ps']:.1f} ps | TNS: {s['tns_hold_ps']:.1f} ps)")
    print(f"  • Clock Domain Crossing (CDC) MTBF: {s['cdc_synchronizer_mtbf_years']:.2e} Years (>10^8 yr signoff threshold)\n")
    print("Clock Domain Allocations:")
    for c in results["clock_domains"]:
        print(f"  • {c['name']:<14}: {c['frequency_mhz']:>7.1f} MHz (T = {c['period_ps']:>7.1f} ps | Skew: {c['clock_skew_ps']:.1f} ps)")
    print("=" * 95)
    print(f"Extracted artifact saved to: {RESULT_PATH}\n")


if __name__ == "__main__":
    main()
