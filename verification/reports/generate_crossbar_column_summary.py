"""WP1.3 — machine-readable verification summary for crossbar-column-v1.

Closes the R1 proof chain:

    0007 SPICE evidence
         | extraction (crossbar-column-v1-extract.json)
         v
    validated profile (crossbar-column-v1.json)
         | profile_adapter
         v
    analog_llm tile/system configuration
         v
    reproducible verification report (this script)

The summary is deterministic: it contains no timestamps and reads only
committed artifacts (the raw extract results, the validated profile and the
adapter). It fails closed if the profile cannot support a physical claim or if
any committed profile value disagrees with the raw extract result (i.e. the
profile is not traceable to the SPICE measurement it claims to encode).

Run:  python verification/reports/generate_crossbar_column_summary.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

_REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO))

from analog_llm.device_profile import load_device_profile
from analog_llm.profile_adapter import tile_config_from_profile

OUT_DIR = _REPO / "verification" / "reports"
PROFILE_PATH = _REPO / "device_profiles" / "crossbar-column-v1.json"
EXTRACT_PATH = _REPO / "verification" / "circuit" / "results" / "crossbar-column-v1-extract.json"

# Explicit programming/converter bits used by the physical simulator run
# (run_llm_sim.py). These are design choices, not device-profile fields; they
# are the only values in the summary with `assumed` provenance until a
# converter profile (R2) exists.
G_BITS, DAC_BITS, ADC_BITS = 6, 8, 8

# Circuit/device components covered by the crossbar-column proof chain.
COMPONENTS: dict[str, set[str]] = {
    "readout": {"transimpedance_gain_ohm", "gain_v_per_v_per_unit_weight", "rf_nominal_ohm"},
    "differential_mapping": {"dc_error_v_max", "differential_mapping_error_s_max"},
    "conductance_cell": {"g0_s", "gscale_s_per_w"},
    "rail_headroom": {"vref_v", "output_headroom_up_v", "output_headroom_down_v"},
}

# Engineering items that lack evidence today; listed so coverage is explicit.
MEASUREMENT_PENDING = [
    {
        "kind": "hardware_readout",
        "detail": "physical measurement of the 0007 column readout (breadboard workflow)",
    },
    {
        "kind": "transient_settling",
        "detail": "DC operating-point solves only; no transient/settling evidence",
    },
    {
        "kind": "noise_temperature_variation",
        "detail": "no noise, temperature corner or Monte Carlo evidence yet",
    },
]

BUCKET_LABELS = {"spice": "VERIFIED_BY_SPICE", "derived": "DERIVED", "assumed": "ASSUMED"}

FIELD_ORDER = [
    "transimpedance_gain_ohm",
    "gain_v_per_v_per_unit_weight",
    "rf_nominal_ohm",
    "dc_error_v_max",
    "differential_mapping_error_s_max",
    "g0_s",
    "gscale_s_per_w",
    "vref_v",
    "output_headroom_up_v",
    "output_headroom_down_v",
]


def _field_links() -> dict[str, str]:
    return {
        name: f"device_profiles/crossbar-column-v1.json#/fields/{name}"
        for name in FIELD_ORDER
    }


def _crosscheck(profile: dict[str, Any], extract: dict[str, Any]) -> None:
    """Fail closed when a committed profile value is not backed by the extract."""
    for name, field in profile["fields"].items():
        if name not in extract:
            raise ValueError(f"profile field {name!r} not present in extract results")
        claimed = float(field["value"])
        measured = float(extract[name])
        if not abs(claimed - measured) <= 1e-12 * (1.0 + abs(claimed)):
            raise ValueError(
                f"profile field {name!r} value {claimed} != extracted {measured}; "
                "profile is not traceable to the SPICE measurement"
            )


def build_summary(
    profile_path: str | Path = PROFILE_PATH,
    extract_path: str | Path = EXTRACT_PATH,
    *,
    g_bits: int = G_BITS,
    dac_bits: int = DAC_BITS,
    adc_bits: int = ADC_BITS,
) -> dict[str, Any]:
    """Assemble the deterministic verification summary for crossbar-column-v1."""
    profile = load_device_profile(profile_path, physical_claim=True)
    extract = json.loads(Path(extract_path).read_text("utf-8"))
    _crosscheck(profile, extract)

    links = _field_links()
    buckets: dict[str, list[dict[str, Any]]] = {label: [] for label in BUCKET_LABELS.values()}
    by_component: dict[str, dict[str, int]] = {}
    for name in FIELD_ORDER:
        field = profile["fields"][name]
        evidence_class = field["evidence_class"]
        label = BUCKET_LABELS.get(evidence_class)
        if label is None:  # validator already rejects invalid classes; guard anyway
            raise ValueError(f"field {name!r} has unclassifiable evidence {evidence_class!r}")
        component = next(c for c, names in COMPONENTS.items() if name in names)
        entry = {
            "field": name,
            "value": float(field["value"]),
            "unit": field["unit"],
            "evidence_class": evidence_class,
            "component": component,
            "source": links[name],
        }
        buckets[label].append(entry)
        by_component.setdefault(component, {})
        by_component[component][label] = by_component[component].get(label, 0) + 1

    tile_config = tile_config_from_profile(
        profile,
        g_bits=g_bits,
        dac_bits=dac_bits,
        adc_bits=adc_bits,
        physical_claim=True,
    )

    return {
        "schema_version": 1,
        "name": "crossbar-column-v1-verification-summary",
        "generator": "verification/reports/generate_crossbar_column_summary.py",
        "profile": {
            "name": profile["name"],
            "version": profile["version"],
            "evidence_class": profile["evidence_class"],
            "status": profile["status"],
            "source": "device_profiles/crossbar-column-v1.json",
            "spice_tool": profile["provenance"]["tool"],
            "analysis": profile["provenance"]["analysis"],
            "validation": "passed (physical_claim=True, fail-closed)",
        },
        "extract": {
            "source": "verification/circuit/results/crossbar-column-v1-extract.json",
            "crosscheck": "all profile fields match extracted values within 1e-12 rel",
            "source_solves": profile["provenance"]["sources"],
        },
        "coverage": {
            "counts": {label: len(items) for label, items in buckets.items()},
            "by_component": by_component,
            "claim_levels": {
                "circuit/device": {
                    label: len(items) for label, items in buckets.items() if items
                },
                "system": {"ASSUMED": 3, "DERIVED": 0, "VERIFIED_BY_SPICE": 0},
            },
        },
        "evidence": buckets,
        "tile_config": {
            "kwargs": {
                k: tile_config[k]
                for k in ("g_bits", "dac_bits", "adc_bits", "gmin", "gmax", "vin_max", "vout_max")
            },
            "derivation": {
                "gmin": {"expression": "g0_s", "from_fields": ["g0_s"]},
                "gmax": {"expression": "g0_s + gscale_s_per_w", "from_fields": ["g0_s", "gscale_s_per_w"]},
                "vin_max": {
                    "expression": "min(headroom_up, headroom_down)",
                    "from_fields": ["output_headroom_up_v", "output_headroom_down_v"],
                },
                "vout_max": {
                    "expression": "min(headroom_up, headroom_down)",
                    "from_fields": ["output_headroom_up_v", "output_headroom_down_v"],
                },
                "bits": {
                    "expression": "explicit programming choices",
                    "evidence_class": "assumed",
                },
            },
            "consumer": "analog_llm.crossbar.CrossbarTile via analog_llm.profile_adapter",
            "source_adapter": "analog_llm/profile_adapter.py",
        },
        "measurement_pending": MEASUREMENT_PENDING,
        "limitations": profile["provenance"]["limitations"],
    }


def render_markdown(summary: dict[str, Any]) -> str:
    """Render a readable report from the machine-readable summary."""
    lines: list[str] = []
    lines.append(f"# {summary['name']}")
    lines.append("")
    lines.append("R1 gate-exit verification summary — closes the proof chain")
    lines.append("")
    lines.append("```text")
    lines.append("0007 SPICE evidence -> extraction -> validated profile -> adapter -> tile config")
    lines.append("```")
    lines.append("")
    p = summary["profile"]
    lines.append("## Profile")
    lines.append("")
    lines.append(f"- name/version: `{p['name']}` `{p['version']}`")
    lines.append(f"- status: `{p['status']}` (evidence class `{p['evidence_class']}`)")
    lines.append(f"- source: `{p['source']}`")
    lines.append(f"- spice tool/analysis: `{p['spice_tool']}` / `{p['analysis']}`")
    lines.append(f"- validation: `{p['validation']}`")
    lines.append("")
    lines.append("## Coverage")
    lines.append("")
    counts = summary["coverage"]["counts"]
    lines.append("| bucket | count |")
    lines.append("| --- | --- |")
    for label in ("VERIFIED_BY_SPICE", "DERIVED", "ASSUMED"):
        lines.append(f"| {label} | {counts[label]} |")
    lines.append("")
    lines.append("### By component (circuit/device)")
    lines.append("")
    lines.append("| component | VERIFIED_BY_SPICE | DERIVED |")
    lines.append("| --- | --- | --- |")
    for component, tallies in summary["coverage"]["by_component"].items():
        lines.append(
            f"| {component} | {tallies.get('VERIFIED_BY_SPICE', 0)} | {tallies.get('DERIVED', 0)} |"
        )
    lines.append("")
    lines.append("### Claim levels")
    lines.append("")
    lines.append("- circuit/device: evidence-backed profile fields")
    lines.append(
        "- system: tile configuration derived from the profile; "
        "`assumed` bits are explicit programming choices pending a converter profile"
    )
    lines.append("")
    lines.append("## Evidence")
    lines.append("")
    lines.append("| field | value | unit | bucket | source |")
    lines.append("| --- | --- | --- | --- | --- |")
    for label in ("VERIFIED_BY_SPICE", "DERIVED", "ASSUMED"):
        for entry in summary["evidence"][label]:
            lines.append(
                f"| {entry['field']} | {entry['value']:g} | {entry['unit']} | "
                f"{label} | {entry['source']} |"
            )
    lines.append("")
    lines.append("## Adapter-derived tile configuration")
    lines.append("")
    tile = summary["tile_config"]
    lines.append("- consumer: `" + tile["consumer"] + "`")
    lines.append("- source adapter: `" + tile["source_adapter"] + "`")
    lines.append("")
    lines.append("| kwarg | value | derivation |")
    lines.append("| --- | --- | --- |")
    for key in ("g_bits", "dac_bits", "adc_bits", "gmin", "gmax", "vin_max", "vout_max"):
        if key in tile["derivation"]:
            expr = tile["derivation"][key]["expression"]
        else:
            expr = tile["derivation"]["bits"]["expression"]
        lines.append(f"| {key} | {tile['kwargs'][key]:g} | {expr} |")
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
    json_path = OUT_DIR / "crossbar-column-v1-summary.json"
    md_path = OUT_DIR / "crossbar-column-v1-summary.md"
    json_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", "utf-8")
    md_path.write_text(render_markdown(summary), "utf-8")
    print(f"wrote {json_path}")
    print(f"wrote {md_path}")
    print("coverage:", summary["coverage"]["counts"])


if __name__ == "__main__":
    main()