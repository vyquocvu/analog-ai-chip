from analog_layout.drc import run_drc
from analog_layout.full_chip import FullChipAssemblyConfig, generate_full_chip_assembly


def test_full_chip_assembly_geometry_and_area() -> None:
    cfg = FullChipAssemblyConfig()
    cell = generate_full_chip_assembly(cfg)

    # 1. Die Dimensions and Area Verification (matching T0_GPT2_124M target 336.1 mm2)
    assert 336.0 <= cell.metadata["die_area_mm2"] <= 336.5
    assert cell.metadata["die_area_mm2"] <= 400.0
    assert cell.metadata["die_width_mm"] == 18.334
    assert cell.metadata["die_height_mm"] == 18.334

    # 2. Package and I/O Bump Ring Verification
    assert cell.metadata["package_type"] == "FCBGA-676"
    assert cell.metadata["placed_bump_pads"] > 200
    assert cell.metadata["port_count"] == cell.metadata["placed_bump_pads"]

    # 3. ESD Protection Clamps Verification
    esd = cell.metadata["esd_protection"]
    assert esd["hbm_rating_kv"] >= 2.0
    assert esd["cdm_rating_v"] >= 500.0

    # 4. Global Balanced Clock H-Tree Signoff
    clk = cell.metadata["clock_tree"]
    assert clk["is_clock_skew_clean"] is True
    assert clk["global_skew_ps"] <= 15.0


def test_full_chip_drc_clean() -> None:
    cell = generate_full_chip_assembly()
    report = run_drc(cell)

    assert report.is_clean is True
    assert report.violation_count == 0
    assert report.total_checks > 100
