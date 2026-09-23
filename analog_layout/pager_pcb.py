"""Manifest- and KiCad-evidence-backed Pager-1 carrier verification."""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

_REPO = Path(__file__).resolve().parents[1]
_PROJECT = _REPO / "kicad" / "pager-carrier-rev-a"
_MANIFEST = _PROJECT / "hardware-manifest.json"
_EVIDENCE = _REPO / "verification" / "layout" / "results" / "pager-carrier-rev-a-kicad.json"


@dataclass(frozen=True)
class PagerPCBStackupConfig:
    """Four-layer carrier constraints mirrored by the hardware manifest."""

    layer_count: int = 4
    board_width_mm: float = 70.0
    board_height_mm: float = 52.0
    total_thickness_mm: float = 1.20
    substrate_material: str = "High-Tg FR4; final fabricator material not selected"
    dielectric_constant_dk: float = 4.20
    loss_tangent_df: float = 0.015
    outer_copper_weight_oz: float = 1.0
    inner_copper_weight_oz: float = 0.5
    single_ended_impedance_ohm: float = 50.0
    min_trace_width_mm: float = 0.127
    min_clearance_mm: float = 0.127
    min_via_drill_mm: float = 0.20


@dataclass(frozen=True)
class PagerMezzanineConnectorConfig:
    """Manifest contract for the 40-pin accelerator connector."""

    connector_model: str = "Hirose DF40C-40DP-0.4V(51)"
    pin_count: int = 40
    pin_pitch_mm: float = 0.40
    current_rating_a_per_pin: float = 0.30
    contact_resistance_mohm: float = 30.0
    mating_cycles: int = 100
    signals_allocated: int = 24
    power_pins_allocated: int = 8
    ground_pins_allocated: int = 8


@dataclass(frozen=True)
class PagerPCBSignoffReport:
    """KiCad design verification, separate from fabrication evidence."""

    is_pcb_drc_clean: bool
    is_impedance_compliant: bool
    trace_width_50ohm_mm: float
    ground_plane_coverage_pct: float
    max_mezzanine_voltage_drop_mv: float
    impedance_evidence_class: str = "assumed"
    metadata: dict[str, Any] = field(default_factory=dict)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load_verified_evidence(path: Path) -> tuple[bool, dict[str, Any]]:
    if not path.is_file():
        return False, {"evidence_error": f"missing evidence file: {path}"}
    try:
        evidence = json.loads(path.read_text(encoding="utf-8"))
        expected_hashes = evidence["source_sha256"]
        required_sources = {
            source.relative_to(_PROJECT).as_posix()
            for source in _PROJECT.rglob("*")
            if source.is_file() and (
                source.suffix in {".kicad_sch", ".kicad_pcb", ".kicad_pro", ".kicad_dru", ".kicad_sym", ".kicad_mod"}
                or source.name in {"hardware-manifest.json", "fp-lib-table", "sym-lib-table"}
            )
        }
        hash_match = (
            isinstance(expected_hashes, dict)
            and bool(required_sources)
            and set(expected_hashes) == required_sources
            and all(
                _sha256(_PROJECT / name) == digest
                for name, digest in expected_hashes.items()
            )
        )
        drc = evidence["pcb_drc"]
        clean = (
            evidence["claim"] == "KICAD_DESIGN_ERC_DRC_VERIFIED"
            and evidence["erc"]["violations"] == 0
            and drc["violations"] == 0
            and drc["unconnected_items"] == 0
            and drc["schematic_parity_issues"] == 0
            and drc["zones_refilled"] is True
            and hash_match
        )
    except (KeyError, TypeError, ValueError, json.JSONDecodeError) as error:
        return False, {"evidence_error": str(error)}
    return clean, {
        "evidence_path": str(path),
        "kicad_version": evidence.get("kicad_version"),
        "source_hashes_match": hash_match,
        "claim": evidence.get("claim"),
    }


def verify_pager_pcb(
    stackup: PagerPCBStackupConfig | None = None,
    mezz: PagerMezzanineConnectorConfig | None = None,
    peak_crossbar_current_ma: float = 50.0,
    evidence_path: Path | None = None,
) -> PagerPCBSignoffReport:
    """Verify the design from its manifest and source-hash-bound CLI evidence.

    The impedance calculation is retained as a sensitivity estimate only. It
    cannot become compliant without a fabricator stackup or coupon measurement.
    """

    stack = stackup or PagerPCBStackupConfig()
    connector = mezz or PagerMezzanineConnectorConfig()
    manifest = json.loads(_MANIFEST.read_text(encoding="utf-8"))
    board = manifest["board"]
    contract_matches = (
        stack.layer_count == board["layer_count"]
        and stack.board_width_mm == board["width_mm"]
        and stack.board_height_mm == board["height_mm"]
        and stack.total_thickness_mm == board["thickness_mm"]
        and stack.min_trace_width_mm == board["minimum_trace_width_mm"]
        and stack.min_clearance_mm == board["minimum_clearance_mm"]
        and stack.min_via_drill_mm == board["minimum_via_drill_mm"]
        and connector.pin_count == manifest["mezzanine"]["pin_count"]
    )
    cli_clean, evidence_metadata = _load_verified_evidence(evidence_path or _EVIDENCE)

    estimate = board["preliminary_impedance"]
    width_mm = float(estimate["trace_width_mm"])
    estimated_ohms = (87.0 / math.sqrt(stack.dielectric_constant_dk + 1.41)) * math.log(
        5.98 * 0.20 / (0.8 * width_mm + 0.035)
    )
    parallel_pins = max(connector.power_pins_allocated // 2, 1)
    drop_mv = (peak_crossbar_current_ma / 1000.0) * (
        connector.contact_resistance_mohm / parallel_pins / 1000.0
    ) * 1000.0
    nominal_plane_coverage = (69.5 * 51.5) / (70.0 * 52.0) * 100.0

    return PagerPCBSignoffReport(
        is_pcb_drc_clean=bool(cli_clean and contract_matches),
        is_impedance_compliant=False,
        trace_width_50ohm_mm=width_mm,
        ground_plane_coverage_pct=round(nominal_plane_coverage, 1),
        max_mezzanine_voltage_drop_mv=round(drop_mv, 3),
        impedance_evidence_class=str(estimate["evidence_class"]),
        metadata={
            "board_size_mm": f"{board['width_mm']:.1f} x {board['height_mm']:.1f}",
            "stackup": f"{board['layer_count']}-layer ({board['thickness_mm']:.1f} mm)",
            "connector": connector.connector_model,
            "manifest_contract_matches": contract_matches,
            "estimated_impedance_ohm": round(estimated_ohms, 2),
            "ground_coverage_basis": "nominal zone polygon before clearance cutouts",
            **evidence_metadata,
        },
    )
