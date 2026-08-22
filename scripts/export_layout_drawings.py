#!/usr/bin/env python3
"""Export all physical IC layout drawings to high-resolution color-coded SVG files."""

from __future__ import annotations

import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_REPO))

from analog_layout.converter_layout import (
    CDACArrayConfig,
    SARADCLayoutConfig,
    generate_cdac_layout,
    generate_sar_adc_layout,
)
from analog_layout.export_svg import export_layout_to_svg
from analog_layout.reram_macro import ReRAMArrayConfig, generate_reram_macro_cell

PLOTS_DIR = _REPO / "verification" / "layout" / "plots"


def main() -> None:
    PLOTS_DIR.mkdir(parents=True, exist_ok=True)

    print("=" * 85)
    print("PHYSICAL IC LAYOUT DRAWINGS EXPORTER (28nm BEOL ReRAM ACCELERATOR)")
    print("=" * 85)
    print(f"Output Directory: {PLOTS_DIR}\n")

    designs = []

    # 1. 16x16 ReRAM Macro
    reram_16 = generate_reram_macro_cell(ReRAMArrayConfig(rows=16, cols=16))
    p1 = export_layout_to_svg(reram_16, PLOTS_DIR / "reram_macro_16x16_layout.svg")
    bbox1 = reram_16.get_bounding_box()
    designs.append(("16x16 ReRAM Macro", reram_16.name, p1, f"{(bbox1[2]-bbox1[0])/1000:.2f} x {(bbox1[3]-bbox1[1])/1000:.2f} µm", len(reram_16.rectangles)))

    # 2. 32x32 ReRAM Macro
    reram_32 = generate_reram_macro_cell(ReRAMArrayConfig(rows=32, cols=32))
    p2 = export_layout_to_svg(reram_32, PLOTS_DIR / "reram_macro_32x32_layout.svg")
    bbox2 = reram_32.get_bounding_box()
    designs.append(("32x32 ReRAM Macro", reram_32.name, p2, f"{(bbox2[2]-bbox2[0])/1000:.2f} x {(bbox2[3]-bbox2[1])/1000:.2f} µm", len(reram_32.rectangles)))

    # 3. 2D Common-Centroid CDAC Matrix
    cdac_cell, _meta = generate_cdac_layout(CDACArrayConfig())
    p3 = export_layout_to_svg(cdac_cell, PLOTS_DIR / "cdac_common_centroid_layout.svg")
    bbox3 = cdac_cell.get_bounding_box()
    designs.append(("Common-Centroid CDAC", cdac_cell.name, p3, f"{(bbox3[2]-bbox3[0])/1000:.2f} x {(bbox3[3]-bbox3[1])/1000:.2f} µm", len(cdac_cell.rectangles)))

    # 4. 8-bit Mixed-Signal SAR ADC Macro
    adc_cell = generate_sar_adc_layout(SARADCLayoutConfig())
    p4 = export_layout_to_svg(adc_cell, PLOTS_DIR / "sar_adc_8bit_layout.svg")
    bbox4 = adc_cell.get_bounding_box()
    designs.append(("8-bit SAR ADC Macro", adc_cell.name, p4, f"{(bbox4[2]-bbox4[0])/1000:.2f} x {(bbox4[3]-bbox4[1])/1000:.2f} µm", len(adc_cell.rectangles)))

    print(f"{'Design Block':<24} | {'Cell Name':<28} | {'Dimensions':<16} | {'Shapes':<8} | {'Status'}")
    print("-" * 95)
    for title, cell_name, path, dims, shapes in designs:
        print(f"{title:<24} | {cell_name:<28} | {dims:<16} | {shapes:<8} | EXPORTED")

    print("=" * 95)
    print("All physical IC layout SVG files successfully exported and ready for viewing!\n")


if __name__ == "__main__":
    main()
