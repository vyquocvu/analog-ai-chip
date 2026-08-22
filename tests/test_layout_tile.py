from analog_layout.drc import run_drc
from analog_layout.power_grid import PowerGridConfig, simulate_power_grid_ir_drop
from analog_layout.tile_floorplan import TileFloorplanConfig, generate_tile_floorplan


def test_tile_floorplan_dimensions_and_contract() -> None:
    cfg = TileFloorplanConfig(tile_width_um=57.3, tile_height_um=57.3)
    cell = generate_tile_floorplan(cfg)

    # 1. Area match with Gate R8 / Chapter 0040 physical model (3281.5 um2)
    assert 3280.0 <= cell.metadata["total_tile_area_um2"] <= 3290.0
    assert cell.metadata["port_count"] >= 7

    # 2. Bounding box check in nanometers (57300 nm x 57300 nm)
    bbox = cell.get_bounding_box()
    assert bbox == (0, 0, 57300, 57300)


def test_power_grid_ir_drop_and_em_signoff() -> None:
    cfg = PowerGridConfig()
    report = simulate_power_grid_ir_drop(tile_size_um=57.3, peak_current_ma=1.2, config=cfg)

    # 1. IR Drop Compliance (<= 30 mV, i.e. < 3%)
    assert report.is_ir_drop_clean is True
    assert report.max_ir_drop_mv < 10.0  # Dense M5/M6 mesh achieves very low IR drop (~1.5 mV)
    assert report.ir_drop_pct < 1.0

    # 2. Electromigration Compliance (<= 1.5 mA/um)
    assert report.is_em_clean is True
    assert report.max_current_density_ma_um < 1.0


def test_full_tile_drc_clean() -> None:
    cell = generate_tile_floorplan()
    report = run_drc(cell)

    assert report.is_clean is True
    assert report.violation_count == 0
    assert report.total_checks > 1000
