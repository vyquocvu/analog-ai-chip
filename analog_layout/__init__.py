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
from .full_chip import (
    FullChipAssemblyConfig,
    generate_full_chip_assembly,
)
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
from .pex import (
    ParasiticNet,
    PEXTechnologyProfile,
    SPEFNetlist,
    extract_spef_from_cell,
)
from .post_layout_sim import (
    PostLayoutSettlingConfig,
    SettlingReport,
    simulate_crossbar_post_layout_settling,
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
    "FullChipAssemblyConfig",
    "LVSReport",
    "Layer",
    "LayoutCell",
    "PEXTechnologyProfile",
    "ParasiticNet",
    "Point",
    "Port",
    "PostLayoutSettlingConfig",
    "PowerGridConfig",
    "PowerGridReport",
    "ReRAMArrayConfig",
    "Rectangle",
    "SARADCLayoutConfig",
    "SPEFNetlist",
    "SchematicDevice",
    "SchematicNetlist",
    "SettlingReport",
    "TileFloorplanConfig",
    "build_golden_sar_adc_schematic",
    "export_layout_to_svg",
    "extract_spef_from_cell",
    "generate_cdac_layout",
    "generate_full_chip_assembly",
    "generate_reram_macro_cell",
    "generate_sar_adc_layout",
    "generate_tile_floorplan",
    "run_drc",
    "run_lvs",
    "simulate_crossbar_post_layout_settling",
    "simulate_power_grid_ir_drop",
]
