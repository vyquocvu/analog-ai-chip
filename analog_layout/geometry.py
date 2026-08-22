"""Physical layout geometric primitives, layers, and hierarchical cell representations.

Provides lightweight GDSII/OASIS-compatible geometric structures for physical IC synthesis
and Design Rule Checking (DRC) signoff without heavy external C++ dependencies.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import IntEnum
from typing import Any


class Layer(IntEnum):
    """Standard 28nm BEOL process layer map."""

    SUBSTRATE = 0
    DIFFUSION = 1
    POLY_GATE = 2
    CONTACT = 3
    METAL1 = 4
    VIA1 = 5
    METAL2 = 6
    VIA2 = 7
    METAL3 = 8
    VIA3 = 9
    METAL4 = 10  # Wordlines / Bottom Electrode (BE)
    VIA4_RERAM = 11  # ReRAM Dielectric Active Switching Layer
    METAL5 = 12  # Bitlines / Top Electrode (TE)
    VIA5 = 13
    METAL6 = 14  # Local Power Distribution Grid
    VIA6 = 15
    METAL7 = 16  # Intermediate Global Power Straps
    VIA7 = 17
    METAL8 = 18  # Top Metal Power Grid & I/O Pads
    PASSIVATION_OPEN = 19


@dataclass(frozen=True)
class Point:
    """2D coordinate in nanometers."""

    x_nm: int
    y_nm: int


@dataclass(frozen=True)
class Rectangle:
    """Rectangular shape defined by bottom-left and top-right coordinates."""

    layer: Layer
    x_min_nm: int
    y_min_nm: int
    x_max_nm: int
    y_max_nm: int
    net_name: str = ""

    @property
    def width_nm(self) -> int:
        return self.x_max_nm - self.x_min_nm

    @property
    def height_nm(self) -> int:
        return self.y_max_nm - self.y_min_nm

    @property
    def area_nm2(self) -> int:
        return self.width_nm * self.height_nm


@dataclass(frozen=True)
class Port:
    """External electrical terminal or pin for routing and LVS matching."""

    name: str
    layer: Layer
    x_nm: int
    y_nm: int
    width_nm: int = 40
    direction: str = "inout"  # "input", "output", "inout"


@dataclass
class LayoutCell:
    """Hierarchical IC layout cell containing shapes, ports, and sub-cell instances."""

    name: str
    rectangles: list[Rectangle] = field(default_factory=list)
    ports: list[Port] = field(default_factory=list)
    instances: list[tuple[str, str, int, int]] = field(default_factory=list)  # (instance_name, cell_name, offset_x, offset_y)
    metadata: dict[str, Any] = field(default_factory=dict)

    def add_rect(self, layer: Layer, x_min: int, y_min: int, x_max: int, y_max: int, net_name: str = "") -> Rectangle:
        r = Rectangle(layer, x_min, y_min, x_max, y_max, net_name)
        self.rectangles.append(r)
        return r

    def add_port(self, name: str, layer: Layer, x: int, y: int, width: int = 40, direction: str = "inout") -> Port:
        p = Port(name, layer, x, y, width, direction)
        self.ports.append(p)
        return p

    def get_bounding_box(self) -> tuple[int, int, int, int]:
        """Compute [x_min, y_min, x_max, y_max] bounding box in nanometers."""
        if not self.rectangles:
            return (0, 0, 0, 0)
        x_min = min(r.x_min_nm for r in self.rectangles)
        y_min = min(r.y_min_nm for r in self.rectangles)
        x_max = max(r.x_max_nm for r in self.rectangles)
        y_max = max(r.y_max_nm for r in self.rectangles)
        return (x_min, y_min, x_max, y_max)
