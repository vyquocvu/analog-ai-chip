"""28nm BEOL ReRAM Macro Cell Layout Generator.

Generates GDSII-compatible physical layout for NxM ReRAM crossbar arrays
with 160nm cell pitch, Via4-M5 integration, and boundary dummy cells.
"""

from __future__ import annotations

from dataclasses import dataclass

from .geometry import Layer, LayoutCell


@dataclass(frozen=True)
class ReRAMArrayConfig:
    """Design parameters for physical ReRAM macro array layout."""

    rows: int = 16
    cols: int = 16
    cell_pitch_nm: int = 160
    wordline_width_nm: int = 60  # Metal 4 width
    bitline_width_nm: int = 60  # Metal 5 width
    reram_via_size_nm: int = 32  # Via4 switching cell size
    dummy_rings: int = 1  # Boundary dummy cells to guarantee lithographic uniformity


def generate_reram_macro_cell(config: ReRAMArrayConfig | None = None) -> LayoutCell:
    """Synthesize complete physical layout for ReRAM macro array."""
    cfg = config or ReRAMArrayConfig()
    cell = LayoutCell(name=f"reram_macro_{cfg.rows}x{cfg.cols}")

    total_rows = cfg.rows + 2 * cfg.dummy_rings
    total_cols = cfg.cols + 2 * cfg.dummy_rings

    array_width_nm = total_cols * cfg.cell_pitch_nm
    array_height_nm = total_rows * cfg.cell_pitch_nm

    half_m4 = cfg.wordline_width_nm // 2
    half_m5 = cfg.bitline_width_nm // 2
    half_via = cfg.reram_via_size_nm // 2

    # 1. Horizontal Wordlines (Metal 4)
    for r in range(total_rows):
        y_center = r * cfg.cell_pitch_nm + (cfg.cell_pitch_nm // 2)
        y_min = y_center - half_m4
        y_max = y_center + half_m4
        is_dummy = (r < cfg.dummy_rings) or (r >= cfg.rows + cfg.dummy_rings)
        net = "DUMMY_WL" if is_dummy else f"WL_{r - cfg.dummy_rings}"

        cell.add_rect(
            Layer.METAL4,
            x_min=0,
            y_min=y_min,
            x_max=array_width_nm,
            y_max=y_max,
            net_name=net,
        )
        if not is_dummy:
            cell.add_port(
                name=net,
                layer=Layer.METAL4,
                x=0,
                y=y_center,
                width=cfg.wordline_width_nm,
                direction="input",
            )

    # 2. Vertical Bitlines (Metal 5)
    for c in range(total_cols):
        x_center = c * cfg.cell_pitch_nm + (cfg.cell_pitch_nm // 2)
        x_min = x_center - half_m5
        x_max = x_center + half_m5
        is_dummy = (c < cfg.dummy_rings) or (c >= cfg.cols + cfg.dummy_rings)
        net = "DUMMY_BL" if is_dummy else f"BL_{c - cfg.dummy_rings}"

        cell.add_rect(
            Layer.METAL5,
            x_min=x_min,
            y_min=0,
            x_max=x_max,
            y_max=array_height_nm,
            net_name=net,
        )
        if not is_dummy:
            cell.add_port(
                name=net,
                layer=Layer.METAL5,
                x=x_center,
                y=array_height_nm,
                width=cfg.bitline_width_nm,
                direction="output",
            )

    # 3. Active ReRAM Crosspoints (Via4 Switching Oxide Layer)
    for r in range(total_rows):
        y_center = r * cfg.cell_pitch_nm + (cfg.cell_pitch_nm // 2)
        for c in range(total_cols):
            x_center = c * cfg.cell_pitch_nm + (cfg.cell_pitch_nm // 2)
            is_dummy = (
                (r < cfg.dummy_rings)
                or (r >= cfg.rows + cfg.dummy_rings)
                or (c < cfg.dummy_rings)
                or (c >= cfg.cols + cfg.dummy_rings)
            )
            net = "DUMMY_CELL" if is_dummy else f"CELL_{r - cfg.dummy_rings}_{c - cfg.dummy_rings}"

            cell.add_rect(
                Layer.VIA4_RERAM,
                x_min=x_center - half_via,
                y_min=y_center - half_via,
                x_max=x_center + half_via,
                y_max=y_center + half_via,
                net_name=net,
            )

    cell.metadata = {
        "rows": cfg.rows,
        "cols": cfg.cols,
        "cell_pitch_nm": cfg.cell_pitch_nm,
        "array_width_um": array_width_nm / 1000.0,
        "array_height_um": array_height_nm / 1000.0,
        "macro_area_um2": (array_width_nm * array_height_nm) / 1e6,
        "total_active_crosspoints": cfg.rows * cfg.cols,
    }

    return cell
