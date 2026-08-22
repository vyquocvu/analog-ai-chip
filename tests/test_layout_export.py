from pathlib import Path

from analog_layout.converter_layout import generate_sar_adc_layout
from analog_layout.export_svg import export_layout_to_svg
from analog_layout.reram_macro import generate_reram_macro_cell


def test_export_layout_to_svg(tmp_path: Path) -> None:
    cell = generate_reram_macro_cell()
    svg_path = tmp_path / "test_macro.svg"

    result = export_layout_to_svg(cell, svg_path)
    assert result.exists()

    content = result.read_text(encoding="utf-8")
    assert "<svg" in content
    assert "</svg>" in content
    assert cell.name in content
    assert "reram_macro_16x16" in content


def test_export_sar_adc_to_svg(tmp_path: Path) -> None:
    cell = generate_sar_adc_layout()
    svg_path = tmp_path / "test_adc.svg"

    result = export_layout_to_svg(cell, svg_path)
    assert result.exists()

    content = result.read_text(encoding="utf-8")
    assert "sar_adc_8bit_macro" in content
