from analog_layout.drc import DesignRules28nm, run_drc
from analog_layout.geometry import Layer
from analog_layout.reram_macro import ReRAMArrayConfig, generate_reram_macro_cell


def test_reram_macro_generation() -> None:
    cfg = ReRAMArrayConfig(rows=16, cols=16, cell_pitch_nm=160, dummy_rings=1)
    cell = generate_reram_macro_cell(cfg)

    assert cell.name == "reram_macro_16x16"
    assert len(cell.ports) == 32  # 16 inputs (WL) + 16 outputs (BL)
    assert cell.metadata["total_active_crosspoints"] == 256

    # Array dimensions: 18 * 160nm = 2880nm (2.88 um)
    bbox = cell.get_bounding_box()
    assert bbox == (0, 0, 2880, 2880)


def test_reram_macro_drc_clean() -> None:
    cell = generate_reram_macro_cell()
    report = run_drc(cell)

    assert report.is_clean is True
    assert report.violation_count == 0
    assert len(report.violations) == 0
    assert report.total_checks > 100


def test_drc_catches_violations() -> None:
    cell = generate_reram_macro_cell()
    rules = DesignRules28nm()

    # Inject violation 1: Minimum width violation (10nm < 40nm)
    cell.add_rect(Layer.METAL4, x_min=0, y_min=0, x_max=10, y_max=10)

    # Inject violation 2: Spacing violation (spacing 10nm < 40nm)
    cell.add_rect(Layer.METAL4, x_min=20, y_min=0, x_max=60, y_max=50)

    report = run_drc(cell, rules=rules)
    assert report.is_clean is False
    assert report.violation_count >= 2
