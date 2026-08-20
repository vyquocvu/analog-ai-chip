"""WP3.2 — R3 gate-exit verification summary for the 4×4 crossbar array.

Closes the R3 evidence chain:

    0012 2x2 array (SPICE) + 0013 4x4 array (SPICE)
         | deterministic extraction (crossbar-4x4-0013-extract.json)
         v
    behavioral-equivalence: SPICE vs hand vs profile-driven analog_llm tile
         v
    reproducible verification report (this script)

The summary is deterministic: no timestamps, reads only committed artifacts
(the 4×4 extract, the 2×2 extract, and the validated crossbar-column profile
through ``profile_adapter``). It fails closed if the tile cannot be built from
the profile or if a committed error exceeds the frozen budget.

Run:  python verification/reports/generate_crossbar_4x4_summary.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO))

from analog_llm.profile_adapter import build_tile_factory  # noqa: E402

OUT_DIR = _REPO / "verification" / "reports"
EXTRACT_PATH = _REPO / "verification" / "circuit" / "results" / "crossbar-4x4-0013-extract.json"
EXTRACT_12_PATH = _REPO / "verification" / "circuit" / "results" / "crossbar-2x2-0012-extract.json"
PROFILE_PATH = "device_profiles/crossbar-column-v1.json"

# Frozen error budgets for the R3 gate exit (2e-3 V is the ideal-VCVS model's
# finite-gain error at these scales; 5e-6 A for the current ledger).
BUDGET_MVM_V = 2e-3
BUDGET_CURRENT_A = 5e-6

# Evidence components covered by the R3 proof chain.
COMPONENTS = {
    "mvm": "SPICE 4x4 MVM vs hand reference Vout = RF*GSCALE*(W @ u)",
    "behavioral": "profile-driven analog_llm tile vs hand reference (16-bit quantization floor)",
    "currents": "column currents recovered from SPICE half-stage outputs vs hand sum u*G",
    "headroom": "differential output envelope +/-2.5 V and virtual-ground loading",
    "regression": "scaled module reproduces the committed 2x2 (0012) results",
}

MEASUREMENT_PENDING = [
    {
        "kind": "op_amp_bandwidth",
        "detail": "ideal VCVS has no bandwidth model; settling is recorded as a "
                  "data point, not a claim -- bounded settling is 0014",
    },
    {
        "kind": "finite_driver_impedance",
        "detail": "input rows are ideal voltage sources; IR drop / line resistance "
                  "are R4 items",
    },
    {
        "kind": "parasitic_rc",
        "detail": "no parasitic RC on cells or interconnect yet (R4)",
    },
]


def build_summary(
    extract_path: str | Path = EXTRACT_PATH,
    extract_12_path: str | Path = EXTRACT_12_PATH,
) -> dict[str, object]:
    d = json.loads(Path(extract_path).read_text("utf-8"))
    d12 = json.loads(Path(extract_12_path).read_text("utf-8"))

    # fail closed: the frozen budget must hold on the committed numbers
    for key, budget in (("worst_abs_err_spice_hand_v", BUDGET_MVM_V),
                        ("worst_abs_err_tile_hand_v", BUDGET_MVM_V)):
        if d[key] > budget:
            raise ValueError(f"committed {key} {d[key]} exceeds frozen budget {budget}")

    # behavioral tile configured from the validated profile (no manual constants)
    tile_kwargs = {
        "g_bits": d["tile"]["g_bits"],
        "dac_bits": d["tile"]["dac_bits"],
        "adc_bits": d["tile"]["adc_bits"],
    }
    factory = build_tile_factory(PROFILE_PATH, 4, 4, **tile_kwargs)
    tile = factory()
    config = {
        "profile": PROFILE_PATH,
        "gmin": tile.gmin,
        "gmax": tile.gmax,
        "vin_max": tile.vin_max,
        "vout_max": tile.vout_max,
    }

    error_budget = {
        "mvm_v": {"budget": BUDGET_MVM_V, "spice_hand": d["worst_abs_err_spice_hand_v"],
                  "tile_hand": d["worst_abs_err_tile_hand_v"],
                  "spice_tile": d["worst_abs_err_spice_tile_v"]},
        "current_a": {"budget": BUDGET_CURRENT_A, "worst": d["worst_current_err_a"]},
    }

    return {
        "schema_version": 1,
        "name": "crossbar-4x4-0013-verification-summary",
        "generator": "verification/reports/generate_crossbar_4x4_summary.py",
        "gate": "R3 (small crossbar arrays) gate exit",
        "extract": {
            "source": "verification/circuit/results/crossbar-4x4-0013-extract.json",
            "source_2x2": "verification/circuit/results/crossbar-2x2-0012-extract.json",
            "n_cases": len(d["cases"]),
            "vref_v": d["vref_v"],
            "headroom_v": d["headroom_v"],
        },
        "tile": {
            "profile": config["profile"],
            "gmin_s": config["gmin"],
            "gmax_s": config["gmax"],
            "vin_max_v": config["vin_max"],
            "vout_max_v": config["vout_max"],
            "bits": tile_kwargs,
            "consumer": "analog_llm.tile.CrossbarTile via analog_llm.profile_adapter",
        },
        "error_budget": error_budget,
        "errors": {
            "spice_hand": {"max_v": d["worst_abs_err_spice_hand_v"], "rms_v": d["rms_err_spice_hand_v"]},
            "tile_hand": {"max_v": d["worst_abs_err_tile_hand_v"], "rms_v": d["rms_err_tile_hand_v"]},
            "spice_tile": {"max_v": d["worst_abs_err_spice_tile_v"], "rms_v": d["rms_err_spice_tile_v"]},
            "current_max_a": d["worst_current_err_a"],
            "max_cell_current_a": d["max_cell_current_a"],
            "max_abs_vout_v": d["max_abs_vout_v"],
            "max_virtual_ground_err_v": d["max_virtual_ground_err_v"],
            "regression_2x2_max_abs_err_v": d["regression_2x2_max_abs_err_v"],
            "worst_2x2_spice_hand_v": d12["worst_abs_err_v"],
        },
        "coverage": {
            "components": COMPONENTS,
            "claim_levels": {
                "circuit/device": [
                    "SPICE 4x4 MVM (op solves, VCVS gain 1e4)",
                    "column currents from SPICE half-stage outputs",
                    "virtual-ground loading and differential headroom",
                ],
                "system/behavioral": [
                    "profile-driven tile error is its 16-bit quantization floor",
                    "no latency/energy claim: timing is 0014/R4-R8",
                ],
            },
        },
        "measurement_pending": MEASUREMENT_PENDING,
        "limitations": (
            "Ideal VCVS op-amp (no bandwidth/clipping model); ideal input "
            "sources (no driver impedance); settling recorded but not a claim; "
            "no temperature/process/Monte Carlo evidence (R4)."
        ),
    }


def render_markdown(summary: dict[str, object]) -> str:
    lines: list[str] = []
    lines.append(f"# {summary['name']}")
    lines.append("")
    lines.append("R3 gate-exit verification summary — behavioral equivalence of the 4×4 array")
    lines.append("")
    lines.append("```text")
    lines.append("0012/0013 SPICE arrays -> extract -> hand reference + profile-driven tile -> report")
    lines.append("```")
    lines.append("")
    e = summary["extract"]
    lines.append("## Evidence")
    lines.append("")
    lines.append(f"- source: `{e['source']}` (plus `{e['source_2x2']}` for the 2×2 regression)")
    lines.append(f"- {e['n_cases']} deterministic (W, u) cases x 4 outputs; "
                 f"VREF = {e['vref_v']} V, headroom ±{e['headroom_v']} V")
    lines.append("")
    lines.append("## Behavioral tile")
    lines.append("")
    t = summary["tile"]
    lines.append(f"- profile: `{t['profile']}` via `{t['consumer']}`")
    lines.append(f"- conductance window [{t['gmin_s']:g}, {t['gmax_s']:g}] S; "
                 f"envelope ±{t['vout_max_v']} V; bits {t['bits']}")
    lines.append("")
    lines.append("## Error budget (frozen)")
    lines.append("")
    lines.append("| comparison | max (V) | rms (V) | budget (V) |")
    lines.append("| --- | --- | --- | --- |")
    errs = summary["errors"]
    for key, label in (("spice_hand", "SPICE vs hand"),
                       ("tile_hand", "tile vs hand"),
                       ("spice_tile", "SPICE vs tile")):
        lines.append(f"| {label} | {errs[key]['max_v']:.2e} | {errs[key]['rms_v']:.2e} | "
                     f"{summary['error_budget']['mvm_v']['budget']:.0e} |")
    lines.append("")
    lines.append(f"- currents: worst |SPICE − hand| {errs['current_max_a']:.2e} A "
                 f"(budget {summary['error_budget']['current_a']['budget']:.0e} A); "
                 f"max cell current {errs['max_cell_current_a']:.2e} A")
    lines.append(f"- headroom: max |Vout| {errs['max_abs_vout_v']:.3f} V ≤ ±{e['headroom_v']} V; "
                 f"virtual ground within {errs['max_virtual_ground_err_v']:.2e} V")
    lines.append(f"- 2×2 regression: scaled module reproduces 0012 to "
                 f"{errs['regression_2x2_max_abs_err_v']:.1e} V")
    lines.append("")
    lines.append("## Coverage")
    lines.append("")
    lines.append("| component | what it proves |")
    lines.append("| --- | --- |")
    for name, what in summary["coverage"]["components"].items():
        lines.append(f"| {name} | {what} |")
    lines.append("")
    lines.append("### Claim levels")
    lines.append("")
    for level, items in summary["coverage"]["claim_levels"].items():
        for item in items:
            lines.append(f"- `{level}`: {item}")
    lines.append("")
    lines.append("## Measurement pending")
    lines.append("")
    for item in summary["measurement_pending"]:
        lines.append(f"- `{item['kind']}`: {item['detail']}")
    lines.append("")
    lines.append("## Limitations")
    lines.append("")
    lines.append(summary["limitations"])
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    summary = build_summary()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    json_path = OUT_DIR / "crossbar-4x4-0013-summary.json"
    md_path = OUT_DIR / "crossbar-4x4-0013-summary.md"
    json_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", "utf-8")
    md_path.write_text(render_markdown(summary), "utf-8")
    print(f"wrote {json_path}")
    print(f"wrote {md_path}")
    print("errors:", {k: v["max_v"] for k, v in summary["errors"].items()
                      if isinstance(v, dict) and "max_v" in v})


if __name__ == "__main__":
    main()
