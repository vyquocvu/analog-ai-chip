"""Mixed-Signal SAR ADC & CDAC Layout Generator.

Synthesizes differential binary-weighted Capacitor DAC (CDAC) with 2D Common-Centroid
dispersion to eliminate linear process gradients, and completes full SAR ADC physical layout.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .geometry import Layer, LayoutCell


@dataclass(frozen=True)
class CDACArrayConfig:
    """Design parameters for 8-bit differential CDAC layout."""

    resolution_bits: int = 8
    unit_cap_width_nm: int = 400
    unit_cap_height_nm: int = 400
    unit_cap_pitch_nm: int = 500  # 400nm cap + 100nm spacing
    grid_rows: int = 16
    grid_cols: int = 16


@dataclass(frozen=True)
class SARADCLayoutConfig:
    """Design parameters for pitch-matched 8-bit SAR ADC mixed-signal macro."""

    resolution_bits: int = 8
    target_area_um2: float = 150.0  # 150 um2 matching Gate R8 physical model
    cdac_config: CDACArrayConfig = CDACArrayConfig()
    comparator_width_nm: int = 2400
    comparator_height_nm: int = 2000
    sar_logic_width_nm: int = 2400
    sar_logic_height_nm: int = 3000


def generate_cdac_layout(config: CDACArrayConfig | None = None) -> tuple[LayoutCell, dict[str, Any]]:
    """Synthesize 2D Common-Centroid differential Capacitor DAC layout."""
    cfg = config or CDACArrayConfig()
    cell = LayoutCell(name="cdac_8bit_common_centroid")

    # Common-centroid 2D dispersion matrix (16x16 = 256 unit capacitors)
    # Alternating quadrant dispersion ensures equal center-of-gravity for Positive and Negative arrays
    pos_coords: list[tuple[int, int]] = []
    neg_coords: list[tuple[int, int]] = []

    for r in range(cfg.grid_rows):
        for c in range(cfg.grid_cols):
            x_min = c * cfg.unit_cap_pitch_nm
            y_min = r * cfg.unit_cap_pitch_nm
            x_max = x_min + cfg.unit_cap_width_nm
            y_max = y_min + cfg.unit_cap_height_nm

            # Common-centroid symmetric dispersion mapping
            # Checkers / cross-quadrant pattern
            is_pos = (r + c) % 2 == 0
            net = "CAP_POS" if is_pos else "CAP_NEG"

            # Bottom plate on Metal 5
            cell.add_rect(Layer.METAL5, x_min, y_min, x_max, y_max, net_name=f"{net}_BOT")
            # Top plate on Metal 6 (MIM capacitor dielectric in between)
            cell.add_rect(Layer.METAL6, x_min + 40, y_min + 40, x_max - 40, y_max - 40, net_name=f"{net}_TOP")

            center_x = (x_min + x_max) // 2
            center_y = (y_min + y_max) // 2

            if is_pos:
                pos_coords.append((center_x, center_y))
            else:
                neg_coords.append((center_x, center_y))

    # Calculate centroids (Centers of Gravity)
    pos_cg_x = sum(x for x, _ in pos_coords) / len(pos_coords)
    pos_cg_y = sum(y for _, y in pos_coords) / len(pos_coords)

    neg_cg_x = sum(x for x, _ in neg_coords) / len(neg_coords)
    neg_cg_y = sum(y for _, y in neg_coords) / len(neg_coords)

    centroid_offset_nm = ((pos_cg_x - neg_cg_x) ** 2 + (pos_cg_y - neg_cg_y) ** 2) ** 0.5

    metadata = {
        "unit_caps_total": cfg.grid_rows * cfg.grid_cols,
        "pos_cap_count": len(pos_coords),
        "neg_cap_count": len(neg_coords),
        "pos_centroid_nm": (pos_cg_x, pos_cg_y),
        "neg_centroid_nm": (neg_cg_x, neg_cg_y),
        "centroid_offset_nm": centroid_offset_nm,
        "is_perfect_centroid_matched": (centroid_offset_nm < 1e-3),
    }

    cell.metadata = metadata
    return cell, metadata


def generate_sar_adc_layout(config: SARADCLayoutConfig | None = None) -> LayoutCell:
    """Synthesize complete pitch-matched 8-bit SAR ADC layout."""
    cfg = config or SARADCLayoutConfig()
    cell = LayoutCell(name="sar_adc_8bit_macro")

    # 1. CDAC Sub-block
    cdac_cell, cdac_meta = generate_cdac_layout(cfg.cdac_config)
    for r in cdac_cell.rectangles:
        cell.rectangles.append(r)

    cdac_bbox = cdac_cell.get_bounding_box()
    cdac_w = cdac_bbox[2] - cdac_bbox[0]
    cdac_h = cdac_bbox[3] - cdac_bbox[1]

    # 2. Dynamic Latch Comparator (placed adjacent to CDAC)
    comp_x_min = cdac_w + 500
    comp_y_min = 0
    comp_x_max = comp_x_min + cfg.comparator_width_nm
    comp_y_max = comp_y_min + cfg.comparator_height_nm

    cell.add_rect(Layer.METAL1, comp_x_min, comp_y_min, comp_x_max, comp_y_max, net_name="COMP_DIFF_PAIR")
    cell.add_rect(Layer.METAL2, comp_x_min + 100, comp_y_min + 100, comp_x_max - 100, comp_y_max - 100, net_name="COMP_LATCH")

    # 3. SAR Logic & Shift Register (placed above comparator)
    sar_x_min = comp_x_min
    sar_y_min = comp_y_max + 500
    sar_x_max = sar_x_min + cfg.sar_logic_width_nm
    sar_y_max = sar_y_min + cfg.sar_logic_height_nm

    cell.add_rect(Layer.METAL1, sar_x_min, sar_y_min, sar_x_max, sar_y_max, net_name="SAR_LOGIC_STDCELLS")
    cell.add_rect(Layer.METAL3, sar_x_min + 100, sar_y_min + 100, sar_x_max - 100, sar_y_max - 100, net_name="SAR_ROUTING")

    # 4. Power & Reference Straps (Metal 6)
    cell.add_rect(Layer.METAL6, 0, cdac_h + 200, sar_x_max, cdac_h + 600, net_name="VDD_ANA")
    cell.add_rect(Layer.METAL6, 0, cdac_h + 800, sar_x_max, cdac_h + 1200, net_name="VSS_ANA")

    # 5. IO Ports
    cell.add_port("VIN_P", Layer.METAL5, 0, cdac_h // 2, width=80, direction="input")
    cell.add_port("VIN_N", Layer.METAL5, 0, (cdac_h // 2) + 500, width=80, direction="input")
    cell.add_port("VREF_P", Layer.METAL6, 0, cdac_h + 400, width=100, direction="input")
    cell.add_port("VREF_N", Layer.METAL6, 0, cdac_h + 1000, width=100, direction="input")
    cell.add_port("CLK", Layer.METAL3, sar_x_max, sar_y_min + 500, width=60, direction="input")
    cell.add_port("VALID", Layer.METAL3, sar_x_max, sar_y_max - 500, width=60, direction="output")

    for bit in range(cfg.resolution_bits):
        cell.add_port(f"DOUT_{bit}", Layer.METAL2, sar_x_max, sar_y_min + (bit * 250), width=50, direction="output")

    bbox = cell.get_bounding_box()
    total_area_um2 = ((bbox[2] - bbox[0]) * (bbox[3] - bbox[1])) / 1e6

    cell.metadata = {
        "resolution_bits": cfg.resolution_bits,
        "total_area_um2": total_area_um2,
        "cdac_metadata": cdac_meta,
        "port_count": len(cell.ports),
        "target_area_budget_um2": cfg.target_area_um2,
        "is_within_area_budget": (total_area_um2 <= cfg.target_area_um2),
    }

    return cell
