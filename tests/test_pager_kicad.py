"""Structural and evidence-contract tests for Pager-1 Carrier Rev A."""

from __future__ import annotations

import csv
import hashlib
import importlib.util
import json
import re
from pathlib import Path

import pytest

from analog_layout.pager_pcb import verify_pager_pcb

REPO = Path(__file__).resolve().parents[1]
PROJECT = REPO / "kicad" / "pager-carrier-rev-a"


def _manifest() -> dict[str, object]:
    return json.loads((PROJECT / "hardware-manifest.json").read_text(encoding="utf-8"))


def test_complete_df40_contract_and_reserved_pin_isolation() -> None:
    manifest = _manifest()
    connector = manifest["mezzanine"]
    pins = connector["pins"]
    assert [pin["pin"] for pin in pins] == list(range(1, 41))
    assert sum(pin["role"] == "power" for pin in pins) == 8
    assert sum(pin["role"] == "ground" for pin in pins) == 8
    assert sum(pin["role"] in {"signal", "test_only", "reserved"} for pin in pins) == 24
    assert all(
        pin["net"].startswith(("NC_RESERVED", "TEST_ONLY"))
        for pin in pins
        if pin["role"] in {"reserved", "test_only"}
    )

    board = (PROJECT / "pager-carrier-rev-a.kicad_pcb").read_text(encoding="utf-8")
    net_ids = {name.removeprefix("/"): int(number) for number, name in re.findall(r'\(net (\d+) "([^"]*)"\)', board)}
    for pin in pins:
        assert pin["net"] in net_ids
        if pin["role"] == "reserved":
            assert not re.search(rf"\(segment .*\(net {net_ids[pin['net']]}\)", board)


def test_board_geometry_stack_rules_and_keepout() -> None:
    manifest = _manifest()
    board = manifest["board"]
    pcb = (PROJECT / "pager-carrier-rev-a.kicad_pcb").read_text(encoding="utf-8")
    assert board["width_mm"] == 70.0 and board["height_mm"] == 52.0
    assert board["thickness_mm"] == 1.2 and board["layer_count"] == 4
    assert board["minimum_trace_width_mm"] == 0.127
    assert board["minimum_clearance_mm"] == 0.127
    assert board["minimum_via_drill_mm"] == 0.2
    assert '(gr_rect (start 95 75) (end 165 127)' in pcb
    assert '(layer "In1.Cu")' in pcb and '(net_name "/GND")' in pcb
    assert "DISPLAY / FPC KEEPOUT" in pcb
    assert pcb.count('(footprint "MountingHole_2.5mm"') == 4


def test_bom_has_unique_manufacturer_metadata() -> None:
    items = _manifest()["bom"]
    references = [item["reference"] for item in items]
    assert len(references) == len(set(references))
    assert all(item["footprint"] and item["manufacturer"] and item["mpn"] for item in items)
    assert all("dnp" not in item or item["dnp"] is False for item in items)


def test_power_usb_display_and_safe_startup_contracts() -> None:
    manifest = _manifest()
    power = manifest["power"]
    checks = manifest["design_checks"]
    assert power["startup_sys_voltage_v"] == 1.8
    assert power["runtime_sys_voltage_v"] == 3.3
    assert set(power["safe_default_off_rails"]) == {"+2V5_SW", "+1V0_SW", "+5V_LCD"}
    assert checks["usb_input"]["esd_protection"].startswith("D1 ")
    assert checks["battery"]["pin_order"] == ["VBAT", "GND", "NTC"]
    assert checks["display"]["translator"].startswith("U8 ")
    assert checks["display"]["periodic_control"] == "LCD_EXTCOMIN"
    assert all(item["default"] == "off" for item in checks["rail_enables"].values())


def test_generated_primary_sources_are_deterministic() -> None:
    script = REPO / "scripts" / "generate_pager_kicad_sources.py"
    spec = importlib.util.spec_from_file_location("pager_kicad_generator", script)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    manifest = _manifest()
    assert module.build_board(manifest) == (PROJECT / "pager-carrier-rev-a.kicad_pcb").read_text()
    assert module.build_root_schematic(manifest) == (PROJECT / "pager-carrier-rev-a.kicad_sch").read_text()
    assert module.build_project() == (PROJECT / "pager-carrier-rev-a.kicad_pro").read_text()


def test_cli_evidence_is_hash_bound_and_fails_closed(tmp_path: Path) -> None:
    report = verify_pager_pcb()
    assert report.is_pcb_drc_clean is False
    assert report.metadata["source_hashes_match"] is False
    assert verify_pager_pcb(evidence_path=tmp_path / "missing.json").is_pcb_drc_clean is False


def test_complete_source_inventory_binds_subsheets_and_libraries(tmp_path: Path) -> None:
    evidence = json.loads((REPO / "verification/layout/results/pager-carrier-rev-a-kicad.json").read_text())
    sources = [path for path in PROJECT.rglob("*") if path.is_file() and (
        path.suffix in {".kicad_sch", ".kicad_pcb", ".kicad_pro", ".kicad_dru", ".kicad_sym", ".kicad_mod"}
        or path.name in {"hardware-manifest.json", "fp-lib-table", "sym-lib-table"}
    )]
    evidence["source_sha256"] = {
        path.relative_to(PROJECT).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sources
    }
    path = tmp_path / "complete.json"
    path.write_text(json.dumps(evidence))
    assert verify_pager_pcb(evidence_path=path).is_pcb_drc_clean is True
    del evidence["source_sha256"]["power.kicad_sch"]
    path.write_text(json.dumps(evidence))
    assert verify_pager_pcb(evidence_path=path).is_pcb_drc_clean is False


@pytest.mark.parametrize("hashes", [{}, {"hardware-manifest.json": "0" * 64}, [], None])
def test_evidence_rejects_incomplete_source_hashes(tmp_path: Path, hashes) -> None:
    evidence = json.loads((REPO / "verification/layout/results/pager-carrier-rev-a-kicad.json").read_text())
    evidence["source_sha256"] = hashes
    path = tmp_path / "invalid.json"
    path.write_text(json.dumps(evidence))
    assert verify_pager_pcb(evidence_path=path).is_pcb_drc_clean is False


@pytest.mark.parametrize("footprint", [None, "", "wrong:Footprint"])
def test_exported_bom_footprints_must_match_manifest(tmp_path: Path, footprint) -> None:
    spec = importlib.util.spec_from_file_location("pager_build", REPO / "scripts/build_pager_kicad.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    path = tmp_path / "bom.csv"
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["Reference", "Value", "Footprint", "Manufacturer", "MPN", "DNP"])
        writer.writeheader()
        for item in _manifest()["bom"]:
            writer.writerow({
                "Reference": item["reference"],
                "Value": item["value"],
                "Footprint": item["footprint"] if footprint is None else footprint,
                "Manufacturer": item["manufacturer"],
                "MPN": item["mpn"],
                "DNP": "",
            })
    if footprint is None:
        module.validate_bom(path)
    else:
        with pytest.raises(ValueError, match="footprint"):
            module.validate_bom(path)
