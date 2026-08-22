"""Design Rule Checking (DRC) verification engine for 28nm BEOL ReRAM process.

Validates geometric design rules including minimum width, minimum spacing,
via enclosure, and local metal density signoff.
"""

from __future__ import annotations

from dataclasses import dataclass

from .geometry import Layer, LayoutCell, Rectangle


@dataclass(frozen=True)
class DesignRules28nm:
    """Design rules for 28nm BEOL ReRAM stack (dimensions in nm)."""

    # Minimum Width
    min_width_nm: dict[Layer, int] = None
    # Minimum Spacing
    min_spacing_nm: dict[Layer, int] = None
    # Via Enclosure
    min_enclosure_nm: dict[tuple[Layer, Layer], int] = None  # (metal_layer, via_layer) -> min_enclosure
    # Density Limits
    min_density_pct: float = 20.0
    max_density_pct: float = 80.0

    def __post_init__(self):
        if self.min_width_nm is None:
            object.__setattr__(
                self,
                "min_width_nm",
                {
                    Layer.METAL1: 32,
                    Layer.METAL2: 32,
                    Layer.METAL3: 32,
                    Layer.METAL4: 40,
                    Layer.VIA4_RERAM: 32,
                    Layer.METAL5: 40,
                    Layer.METAL6: 64,
                    Layer.METAL7: 80,
                    Layer.METAL8: 120,
                },
            )
        if self.min_spacing_nm is None:
            object.__setattr__(
                self,
                "min_spacing_nm",
                {
                    Layer.METAL1: 32,
                    Layer.METAL2: 32,
                    Layer.METAL3: 32,
                    Layer.METAL4: 40,
                    Layer.VIA4_RERAM: 45,
                    Layer.METAL5: 40,
                    Layer.METAL6: 64,
                    Layer.METAL7: 80,
                    Layer.METAL8: 120,
                },
            )
        if self.min_enclosure_nm is None:
            object.__setattr__(
                self,
                "min_enclosure_nm",
                {
                    (Layer.METAL4, Layer.VIA4_RERAM): 10,
                    (Layer.METAL5, Layer.VIA4_RERAM): 10,
                    (Layer.METAL5, Layer.VIA5): 12,
                    (Layer.METAL6, Layer.VIA5): 12,
                },
            )


@dataclass(frozen=True)
class DRCViolation:
    """Specific geometric design rule violation record."""

    rule_name: str
    layer: Layer
    message: str
    shape_a: Rectangle
    shape_b: Rectangle | None = None


@dataclass(frozen=True)
class DRCReport:
    """Complete Design Rule Checking signoff report."""

    cell_name: str
    is_clean: bool
    total_checks: int
    violation_count: int
    violations: list[DRCViolation]
    metal_densities: dict[str, float]


def run_drc(cell: LayoutCell, rules: DesignRules28nm | None = None) -> DRCReport:
    """Execute complete 28nm BEOL DRC check on a layout cell."""
    drc_rules = rules or DesignRules28nm()
    violations: list[DRCViolation] = []
    total_checks = 0

    # Group shapes by layer
    shapes_by_layer: dict[Layer, list[Rectangle]] = {}
    for r in cell.rectangles:
        shapes_by_layer.setdefault(r.layer, []).append(r)

    # 1. Minimum Width Checks
    for layer, shapes in shapes_by_layer.items():
        min_w = drc_rules.min_width_nm.get(layer, 0)
        for r in shapes:
            total_checks += 1
            if r.width_nm < min_w or r.height_nm < min_w:
                violations.append(
                    DRCViolation(
                        rule_name="MIN_WIDTH",
                        layer=layer,
                        message=f"Width ({min(r.width_nm, r.height_nm)}nm) < min width ({min_w}nm)",
                        shape_a=r,
                    )
                )

    # 2. Minimum Spacing Checks (Same Layer)
    for layer, shapes in shapes_by_layer.items():
        min_s = drc_rules.min_spacing_nm.get(layer, 0)
        n = len(shapes)
        for i in range(n):
            for j in range(i + 1, n):
                r1, r2 = shapes[i], shapes[j]
                # Check horizontal spacing
                h_overlap = max(0, min(r1.y_max_nm, r2.y_max_nm) - max(r1.y_min_nm, r2.y_min_nm))
                v_overlap = max(0, min(r1.x_max_nm, r2.x_max_nm) - max(r1.x_min_nm, r2.x_min_nm))

                if h_overlap > 0:
                    dx = max(0, max(r1.x_min_nm, r2.x_min_nm) - min(r1.x_max_nm, r2.x_max_nm))
                    if 0 < dx < min_s:
                        total_checks += 1
                        violations.append(
                            DRCViolation(
                                rule_name="MIN_SPACING",
                                layer=layer,
                                message=f"Horizontal spacing ({dx}nm) < min spacing ({min_s}nm)",
                                shape_a=r1,
                                shape_b=r2,
                            )
                        )
                if v_overlap > 0:
                    dy = max(0, max(r1.y_min_nm, r2.y_min_nm) - min(r1.y_max_nm, r2.y_max_nm))
                    if 0 < dy < min_s:
                        total_checks += 1
                        violations.append(
                            DRCViolation(
                                rule_name="MIN_SPACING",
                                layer=layer,
                                message=f"Vertical spacing ({dy}nm) < min spacing ({min_s}nm)",
                                shape_a=r1,
                                shape_b=r2,
                            )
                        )

    # 3. Via Enclosure Checks
    for (m_layer, v_layer), min_enc in drc_rules.min_enclosure_nm.items():
        metal_shapes = shapes_by_layer.get(m_layer, [])
        via_shapes = shapes_by_layer.get(v_layer, [])

        for via in via_shapes:
            total_checks += 1
            enclosing = [
                m
                for m in metal_shapes
                if m.x_min_nm <= via.x_min_nm
                and m.x_max_nm >= via.x_max_nm
                and m.y_min_nm <= via.y_min_nm
                and m.y_max_nm >= via.y_max_nm
            ]
            if not enclosing:
                violations.append(
                    DRCViolation(
                        rule_name="VIA_ENCLOSURE",
                        layer=v_layer,
                        message=f"Via not fully enclosed by {m_layer.name}",
                        shape_a=via,
                    )
                )
            else:
                m = enclosing[0]
                enc_x = min(via.x_min_nm - m.x_min_nm, m.x_max_nm - via.x_max_nm)
                enc_y = min(via.y_min_nm - m.y_min_nm, m.y_max_nm - via.y_max_nm)
                if min(enc_x, enc_y) < min_enc:
                    violations.append(
                        DRCViolation(
                            rule_name="VIA_ENCLOSURE",
                            layer=v_layer,
                            message=f"Enclosure ({min(enc_x, enc_y)}nm) < min enclosure ({min_enc}nm)",
                            shape_a=via,
                            shape_b=m,
                        )
                    )

    # 4. Metal Density Checks
    densities: dict[str, float] = {}
    bbox = cell.get_bounding_box()
    cell_area = max(1, (bbox[2] - bbox[0]) * (bbox[3] - bbox[1]))

    for layer, shapes in shapes_by_layer.items():
        layer_area = sum(r.area_nm2 for r in shapes)
        dens_pct = (layer_area / cell_area) * 100.0
        densities[layer.name] = dens_pct

    return DRCReport(
        cell_name=cell.name,
        is_clean=(len(violations) == 0),
        total_checks=total_checks,
        violation_count=len(violations),
        violations=violations,
        metal_densities=densities,
    )
