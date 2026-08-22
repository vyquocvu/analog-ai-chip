"""Parasitic Extraction (PEX) & SPEF Netlist Synthesis Engine.

Extracts distributed wire resistance, area/substrate capacitance, lateral coupling
capacitance, and via contact resistance for 28nm BEOL ReRAM accelerators in standard SPEF format.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .geometry import Layer, LayoutCell


@dataclass(frozen=True)
class PEXTechnologyProfile:
    """Parasitic extraction technological parameters for 28nm BEOL."""

    res_per_um: dict[Layer, float] = None  # Ohm / um
    cap_area_per_um: dict[Layer, float] = None  # fF / um
    cap_coupling_per_um: dict[Layer, float] = None  # fF / um at nominal spacing
    via_resistance_ohm: dict[Layer, float] = None  # Ohm / via

    def __post_init__(self):
        if self.res_per_um is None:
            object.__setattr__(
                self,
                "res_per_um",
                {
                    Layer.METAL1: 1.80,
                    Layer.METAL2: 1.80,
                    Layer.METAL3: 1.50,
                    Layer.METAL4: 1.20,  # Wordlines
                    Layer.METAL5: 1.20,  # Bitlines
                    Layer.METAL6: 0.50,  # Power straps
                    Layer.METAL7: 0.30,
                    Layer.METAL8: 0.10,  # Top metal
                },
            )
        if self.cap_area_per_um is None:
            object.__setattr__(
                self,
                "cap_area_per_um",
                {
                    Layer.METAL1: 0.12,
                    Layer.METAL2: 0.10,
                    Layer.METAL3: 0.09,
                    Layer.METAL4: 0.08,
                    Layer.METAL5: 0.08,
                    Layer.METAL6: 0.06,
                    Layer.METAL7: 0.05,
                    Layer.METAL8: 0.03,
                },
            )
        if self.cap_coupling_per_um is None:
            object.__setattr__(
                self,
                "cap_coupling_per_um",
                {
                    Layer.METAL1: 0.18,
                    Layer.METAL2: 0.16,
                    Layer.METAL3: 0.14,
                    Layer.METAL4: 0.12,
                    Layer.METAL5: 0.12,
                    Layer.METAL6: 0.08,
                    Layer.METAL7: 0.06,
                    Layer.METAL8: 0.04,
                },
            )
        if self.via_resistance_ohm is None:
            object.__setattr__(
                self,
                "via_resistance_ohm",
                {
                    Layer.VIA1: 2.50,
                    Layer.VIA2: 2.20,
                    Layer.VIA3: 2.00,
                    Layer.VIA4_RERAM: 1.50,
                    Layer.VIA5: 1.20,
                    Layer.VIA6: 0.80,
                    Layer.VIA7: 0.50,
                },
            )


@dataclass(frozen=True)
class ParasiticNet:
    """Extracted electrical net with lumped and distributed RC parasitics."""

    name: str
    total_wire_length_um: float
    total_res_ohm: float
    total_cap_ff: float
    segment_count: int
    via_count: int


@dataclass
class SPEFNetlist:
    """Standard Parasitic Exchange Format (SPEF) container."""

    cell_name: str
    nets: dict[str, ParasiticNet] = field(default_factory=dict)
    total_parasitic_cap_ff: float = 0.0
    total_parasitic_res_ohm: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_spef_string(self) -> str:
        """Serialize extracted parasitics to standard IEEE SPEF format text."""
        lines = [
            "*SPEF \"IEEE 1481-1999\"",
            f"*DESIGN \"{self.cell_name}\"",
            "*DATE \"2026-08-22\"",
            "*VENDOR \"Analog AI EDA\"",
            "*PROGRAM \"PEX-Extractor-v1.0\"",
            "*VERSION \"1.0\"",
            "*DESIGN_FLOW \"POST_LAYOUT_RC\"",
            "*DIVIDER /",
            "*DELIMITER :",
            "*BUS_DELIMITER []",
            "*T_UNIT 1.0 PS",
            "*C_UNIT 1.0 FF",
            "*R_UNIT 1.0 OHM",
            "*L_UNIT 1.0 NH",
            "",
        ]

        for net_name, pnet in sorted(self.nets.items()):
            lines.append(f"*D_NET {net_name} {pnet.total_cap_ff:.4f}")
            lines.append("*CONN")
            lines.append(f"*P {net_name}:1 I")
            lines.append(f"*P {net_name}:2 O")
            lines.append("*CAP")
            lines.append(f"1 {net_name}:1 {pnet.total_cap_ff:.4f}")
            lines.append("*RES")
            lines.append(f"1 {net_name}:1 {net_name}:2 {pnet.total_res_ohm:.4f}")
            lines.append("*END")
            lines.append("")

        return "\n".join(lines)


def extract_spef_from_cell(cell: LayoutCell, profile: PEXTechnologyProfile | None = None) -> SPEFNetlist:
    """Perform parasitic RC extraction on layout cell geometries."""
    p_profile = profile or PEXTechnologyProfile()
    nets: dict[str, ParasiticNet] = {}

    # Group shapes by net name
    shapes_by_net: dict[str, list[Any]] = {}
    for r in cell.rectangles:
        if r.net_name:
            shapes_by_net.setdefault(r.net_name, []).append(r)

    total_c = 0.0
    total_r = 0.0

    for net_name, shapes in shapes_by_net.items():
        net_len_um = 0.0
        net_r_ohm = 0.0
        net_c_ff = 0.0
        vias = 0

        for r in shapes:
            # Wire length and dimensions in um
            w_um = r.width_nm / 1000.0
            h_um = r.height_nm / 1000.0
            len_um = max(w_um, h_um)
            net_len_um += len_um

            if r.layer in (Layer.VIA1, Layer.VIA2, Layer.VIA3, Layer.VIA4_RERAM, Layer.VIA5, Layer.VIA6, Layer.VIA7):
                vias += 1
                v_res = p_profile.via_resistance_ohm.get(r.layer, 1.5)
                net_r_ohm += v_res
            else:
                r_unit = p_profile.res_per_um.get(r.layer, 1.2)
                c_area_unit = p_profile.cap_area_per_um.get(r.layer, 0.08)
                c_coup_unit = p_profile.cap_coupling_per_um.get(r.layer, 0.12)

                net_r_ohm += len_um * r_unit
                # Area cap + lateral fringe coupling cap on both wire edges
                net_c_ff += (len_um * c_area_unit) + (2 * len_um * c_coup_unit)

        pnet = ParasiticNet(
            name=net_name,
            total_wire_length_um=net_len_um,
            total_res_ohm=net_r_ohm,
            total_cap_ff=net_c_ff,
            segment_count=len(shapes),
            via_count=vias,
        )
        nets[net_name] = pnet
        total_c += net_c_ff
        total_r += net_r_ohm

    return SPEFNetlist(
        cell_name=cell.name,
        nets=nets,
        total_parasitic_cap_ff=total_c,
        total_parasitic_res_ohm=total_r,
        metadata={
            "extracted_nets_count": len(nets),
            "total_shapes_extracted": len(cell.rectangles),
        },
    )
