from analog_layout.reram_macro import ReRAMArrayConfig, generate_reram_macro_cell
from analog_layout.tapeout import (
    DummyMetalFillConfig,
    build_foundry_tapeout_checklist,
    insert_dummy_metal_fill,
    run_tapeout_signoff,
)


def test_dummy_metal_fill_insertion_and_density() -> None:
    cell = generate_reram_macro_cell(ReRAMArrayConfig(rows=16, cols=16))
    cfg = DummyMetalFillConfig()
    filled_cell, density_reports = insert_dummy_metal_fill(cell, cfg)

    assert len(filled_cell.rectangles) > len(cell.rectangles)
    assert len(density_reports) > 0

    for rep in density_reports.values():
        assert rep.is_density_compliant is True
        assert 20.0 <= rep.post_fill_density_pct <= 80.0
        assert rep.is_gradient_compliant is True
        assert rep.max_spatial_gradient_pct <= 15.0


def test_foundry_tapeout_checklist_and_gdsii_streamout() -> None:
    cell = generate_reram_macro_cell(ReRAMArrayConfig(rows=16, cols=16))
    report = run_tapeout_signoff(cell)

    # 1. Master Tapeout Readiness
    assert report.is_tapeout_ready is True
    assert report.chip_target == "T0_GPT2_124M"
    assert report.process_node == "28nm BEOL Via4-M5 ReRAM"

    # 2. 10-Point Checklist Verification
    assert len(report.checklist) == 10
    assert all(item.is_passed for item in report.checklist)

    # 3. GDSII / OASIS Stream-out Summary
    streamout = report.streamout_summary
    assert streamout.format == "GDSII v6.0 / OASIS v1.0"
    assert streamout.total_polygons > 0
    assert streamout.layer_count > 0
    assert len(streamout.checksum_sha256) == 64


def test_checklist_structure() -> None:
    checklist = build_foundry_tapeout_checklist()
    assert len(checklist) == 10
    names = [c.name for c in checklist]
    assert "Design Rule Checking (DRC)" in names
    assert "Layout-Versus-Schematic (LVS)" in names
    assert "Multi-Corner Static Timing Analysis (STA)" in names
    assert "Dynamic Power Grid & SSN Noise" in names
