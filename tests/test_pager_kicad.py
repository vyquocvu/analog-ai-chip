"""Structural and evidence-contract tests for Pager-1 Carrier Rev A."""

from __future__ import annotations

import importlib.util
import json
import re
from pathlib import Path

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
    assert report.is_pcb_drc_clean is True
    assert report.metadata["source_hashes_match"] is True
    assert verify_pager_pcb(evidence_path=tmp_path / "missing.json").is_pcb_drc_clean is False
