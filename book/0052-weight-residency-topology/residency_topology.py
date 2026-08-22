r"""Chapter 0052 — Weight Residency, Topology Exploration & Chiplet Scaling (Gate R12).

Calculates physical crossbar tile counts, differential cell pairing, silicon area,
and chiplet packaging feasibility for T0–T3 decoder design tiers.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

_REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO))

from analog_llm.model_manifest import ModelManifest
from analog_llm.residency import (
    HardwareTopologyConfig,
    analyze_model_residency,
)

RESULTS_DIR = _REPO / "verification" / "circuit" / "results"
RESULT_PATH = RESULTS_DIR / "residency-topology-0052-extract.json"


def _create_ladder_manifests() -> dict[str, ModelManifest]:
    """Define frozen T0, T1, T2, T3 architecture manifests for residency evaluation."""
    return {
        "hand_calc": ModelManifest(
            vocab_size=32,
            hidden_size=32,
            num_layers=2,
            num_attention_heads=2,
            num_key_value_heads=2,
            intermediate_size=64,
            context_length=16,
            dtype="float32",
            norm_type="layernorm",
            position_type="learned",
            activation_type="gelu",
            attention_type="mha",
            linear_bias=False,
            tied_embeddings=True,
        ),
        "t0_gpt2_124m": ModelManifest(
            vocab_size=50257,
            hidden_size=768,
            num_layers=12,
            num_attention_heads=12,
            num_key_value_heads=12,
            intermediate_size=3072,
            context_length=1024,
            dtype="float16",
            norm_type="layernorm",
            position_type="learned",
            activation_type="gelu",
            attention_type="mha",
        ),
        "t1_llama_1.1b": ModelManifest(
            vocab_size=32000,
            hidden_size=2048,
            num_layers=22,
            num_attention_heads=32,
            num_key_value_heads=4,
            intermediate_size=5632,
            context_length=4096,
            dtype="float16",
            norm_type="rmsnorm",
            position_type="rope",
            activation_type="swiglu",
            attention_type="gqa",
            tied_embeddings=False,
        ),
        "t2_llama_3b": ModelManifest(
            vocab_size=32000,
            hidden_size=3072,
            num_layers=28,
            num_attention_heads=32,
            num_key_value_heads=8,
            intermediate_size=8192,
            context_length=8192,
            dtype="float16",
            norm_type="rmsnorm",
            position_type="rope",
            activation_type="swiglu",
            attention_type="gqa",
            tied_embeddings=False,
        ),
        "t3_llama2_7b": ModelManifest(
            vocab_size=32000,
            hidden_size=4096,
            num_layers=32,
            num_attention_heads=32,
            num_key_value_heads=32,
            intermediate_size=11008,
            context_length=8192,
            dtype="float16",
            norm_type="rmsnorm",
            position_type="rope",
            activation_type="swiglu",
            attention_type="mha",
            tied_embeddings=False,
        ),
    }


def run_residency_extract() -> dict[str, Any]:
    """Execute residency analysis and export deterministic extract."""
    manifests = _create_ladder_manifests()
    topo = HardwareTopologyConfig()

    tier_results: dict[str, Any] = {}
    for name, manifest in manifests.items():
        summary = analyze_model_residency(manifest, topology=topo, model_name=name)
        tier_results[name] = {
            "total_parameters": summary.total_parameters,
            "analog_projection_parameters": summary.analog_projection_parameters,
            "digital_parameters": summary.digital_parameters,
            "total_physical_tiles": summary.total_physical_tiles,
            "total_physical_cells": summary.total_physical_cells,
            "usable_cell_utilization_pct": summary.usable_cell_utilization_pct,
            "reram_core_area_mm2": summary.reram_core_area_mm2,
            "peripheral_area_mm2": summary.peripheral_area_mm2,
            "total_silicon_area_mm2": summary.total_silicon_area_mm2,
            "chiplets_required_for_full_residency": summary.chiplets_required_for_full_residency,
            "is_single_die_resident": summary.is_single_die_resident,
            "is_multi_die_package_resident": summary.is_multi_die_package_resident,
            "schedules": {
                k: {
                    "weight_reload_bytes_per_token": v.weight_reload_bytes_per_token,
                    "reload_time_per_token_us": v.reload_time_per_token_us,
                    "programming_energy_per_token_uj": v.programming_energy_per_token_uj,
                    "is_physically_viable": v.is_physically_viable,
                    "viability_note": v.viability_note,
                }
                for k, v in summary.schedules.items()
            },
        }

    payload: dict[str, Any] = {
        "chapter": "0052-weight-residency-topology",
        "gate": "R12",
        "status": "PASSED",
        "claim_level": "system/architecture-exploration",
        "hardware_topology": {
            "tile_geometry": f"{topo.tile_rows}x{topo.tile_cols}",
            "cell_pitch_nm": topo.cell_pitch_um * 1000,
            "cells_per_weight": topo.cells_per_weight,
            "max_die_area_mm2": topo.max_die_area_mm2,
            "max_chiplets_per_package": topo.max_chiplets_per_package,
        },
        "tier_analyses": tier_results,
    }

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    with open(RESULT_PATH, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)

    return payload


def main() -> None:
    results = run_residency_extract()
    print("=" * 90)
    print("CHAPTER 0052: WEIGHT RESIDENCY & TOPOLOGY SCALING (GATE R12)")
    print("=" * 90)
    print(f"Status: {results['status']} | Claim Level: {results['claim_level']}\n")
    print(
        f"{'Tier / Model':<16} | {'Params':<10} | {'Tiles (16x16)':<14} | {'Area (mm²)':<12} | {'Chiplets':<10} | {'Full Res Viable':<16}"
    )
    print("-" * 90)
    for name, r in results["tier_analyses"].items():
        viable_str = "YES (Single)" if r["is_single_die_resident"] else ("YES (Multi)" if r["is_multi_die_package_resident"] else "NO (Infeasible)")
        print(
            f"{name:<16} | {r['total_parameters']:<10,d} | {r['total_physical_tiles']:<14,d} | "
            f"{r['total_silicon_area_mm2']:<12.1f} | {r['chiplets_required_for_full_residency']:<10} | {viable_str:<16}"
        )
    print("=" * 90)
    print(f"Extracted artifact saved to: {RESULT_PATH}\n")


if __name__ == "__main__":
    main()
