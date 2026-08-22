from analog_layout.converter_layout import (
    CDACArrayConfig,
    SARADCLayoutConfig,
    generate_cdac_layout,
    generate_sar_adc_layout,
)
from analog_layout.drc import run_drc
from analog_layout.lvs import build_golden_sar_adc_schematic, run_lvs


def test_cdac_common_centroid_symmetry() -> None:
    cfg = CDACArrayConfig()
    _cell, meta = generate_cdac_layout(cfg)

    assert meta["unit_caps_total"] == 256
    assert meta["pos_cap_count"] == 128
    assert meta["neg_cap_count"] == 128
    assert meta["is_perfect_centroid_matched"] is True
    assert meta["centroid_offset_nm"] < 1e-3  # Perfect center-of-gravity alignment


def test_sar_adc_layout_drc_and_lvs_clean() -> None:
    cfg = SARADCLayoutConfig()
    cell = generate_sar_adc_layout(cfg)

    # 1. Area budget check
    assert cell.metadata["is_within_area_budget"] is True
    assert cell.metadata["total_area_um2"] <= 150.0

    # 2. DRC Signoff
    drc = run_drc(cell)
    assert drc.is_clean is True
    assert drc.violation_count == 0

    # 3. LVS Signoff
    lvs = run_lvs(cell)
    assert lvs.is_matched is True
    assert lvs.discrepancy_count == 0
    assert lvs.matched_devices >= 258  # 256 caps + comparator + SAR logic


def test_lvs_catches_discrepancies() -> None:
    cell = generate_sar_adc_layout()
    golden_sch = build_golden_sar_adc_schematic()

    # Inject discrepancy 1: Remove an IO port from layout
    cell.ports = [p for p in cell.ports if p.name != "CLK"]

    report = run_lvs(cell, schematic=golden_sch)
    assert report.is_matched is False
    assert report.discrepancy_count >= 1
    assert any("CLK" in d for d in report.discrepancies)
