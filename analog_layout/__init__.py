"""Analog Layout & Physical Verification Engine for 28nm BEOL ReRAM Accelerators."""

from .converter_layout import (
    CDACArrayConfig,
    SARADCLayoutConfig,
    generate_cdac_layout,
    generate_sar_adc_layout,
)
from .drc import (
    DesignRules28nm,
    DRCReport,
    DRCViolation,
    run_drc,
)
from .export_svg import export_layout_to_svg
from .geometry import (
    Layer,
    LayoutCell,
    Point,
    Port,
    Rectangle,
)
from .lvs import (
    LVSReport,
    SchematicDevice,
    SchematicNetlist,
    build_golden_sar_adc_schematic,
    run_lvs,
)
from .power_grid import (
    PowerGridConfig,
    PowerGridReport,
    simulate_power_grid_ir_drop,
)
from .reram_macro import (
    ReRAMArrayConfig,
    generate_reram_macro_cell,
)
from .tile_floorplan import (
    TileFloorplanConfig,
    generate_tile_floorplan,
)

__all__ = [
    "CDACArrayConfig",
    "DRCReport",
    "DRCViolation",
    "DesignRules28nm",
    "LVSReport",
    "Layer",
    "LayoutCell",
    "Point",
    "Port",
    "PowerGridConfig",
    "PowerGridReport",
    "ReRAMArrayConfig",
    "Rectangle",
    "SARADCLayoutConfig",
    "SchematicDevice",
    "SchematicNetlist",
    "TileFloorplanConfig",
    "build_golden_sar_adc_schematic",
    "export_layout_to_svg",
    "generate_cdac_layout",
    "generate_reram_macro_cell",
    "generate_sar_adc_layout",
    "generate_tile_floorplan",
    "run_drc",
    "run_lvs",
    "simulate_power_grid_ir_drop",
]
