"""Physical Layout SVG Renderer & Exporter.

Converts hierarchical LayoutCell geometric rectangles, layers, and ports
into color-coded, labeled SVG layout drawings for visual inspection in browsers and CAD viewers.
"""

from __future__ import annotations

from pathlib import Path

from .geometry import Layer, LayoutCell

# Color palette for 28nm BEOL IC layers (matching standard KLayout / Cadence display color tables)
LAYER_STYLES: dict[Layer, dict[str, str]] = {
    Layer.SUBSTRATE: {"fill": "#e2e8f0", "stroke": "#94a3b8", "opacity": "0.3"},
    Layer.DIFFUSION: {"fill": "#86efac", "stroke": "#22c55e", "opacity": "0.6"},
    Layer.POLY_GATE: {"fill": "#fca5a5", "stroke": "#ef4444", "opacity": "0.7"},
    Layer.CONTACT: {"fill": "#0f172a", "stroke": "#000000", "opacity": "0.9"},
    Layer.METAL1: {"fill": "#93c5fd", "stroke": "#3b82f6", "opacity": "0.7"},
    Layer.VIA1: {"fill": "#1e3a8a", "stroke": "#172554", "opacity": "0.85"},
    Layer.METAL2: {"fill": "#c4b5fd", "stroke": "#8b5cf6", "opacity": "0.7"},
    Layer.VIA2: {"fill": "#581c87", "stroke": "#3b0764", "opacity": "0.85"},
    Layer.METAL3: {"fill": "#fed7aa", "stroke": "#f97316", "opacity": "0.7"},
    Layer.VIA3: {"fill": "#7c2d12", "stroke": "#431407", "opacity": "0.85"},
    Layer.METAL4: {"fill": "#fde047", "stroke": "#eab308", "opacity": "0.75"},  # Wordlines
    Layer.VIA4_RERAM: {"fill": "#dc2626", "stroke": "#991b1b", "opacity": "0.95"},  # ReRAM Cells
    Layer.METAL5: {"fill": "#67e8f9", "stroke": "#06b6d4", "opacity": "0.75"},  # Bitlines / CDAC bottom
    Layer.VIA5: {"fill": "#164e63", "stroke": "#083344", "opacity": "0.85"},
    Layer.METAL6: {"fill": "#d8b4fe", "stroke": "#a855f7", "opacity": "0.75"},  # Power grid / CDAC top
    Layer.VIA6: {"fill": "#581c87", "stroke": "#3b0764", "opacity": "0.85"},
    Layer.METAL7: {"fill": "#f472b6", "stroke": "#db2777", "opacity": "0.75"},
    Layer.VIA7: {"fill": "#831843", "stroke": "#500724", "opacity": "0.85"},
    Layer.METAL8: {"fill": "#fb923c", "stroke": "#ea580c", "opacity": "0.8"},  # Top metal pads
}


def export_layout_to_svg(
    cell: LayoutCell,
    output_path: Path | str,
    view_width: int = 800,
    view_height: int = 800,
    margin_px: int = 40,
    show_labels: bool = True,
) -> Path:
    """Render a physical LayoutCell to a standalone color-coded SVG file."""
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)

    bbox = cell.get_bounding_box()
    x_min, y_min, x_max, y_max = bbox
    layout_w = max(1, x_max - x_min)
    layout_h = max(1, y_max - y_min)

    # Scale factors from layout nanometers to SVG canvas pixels
    drawable_w = view_width - 2 * margin_px
    drawable_h = view_height - 2 * margin_px
    scale = min(drawable_w / layout_w, drawable_h / layout_h)

    def tx(x_nm: int) -> float:
        return margin_px + (x_nm - x_min) * scale

    def ty(y_nm: int) -> float:
        return (view_height - margin_px) - (y_nm - y_min) * scale

    grid_rect = (
        f'    <rect x="{tx(x_min)}" y="{ty(y_max)}" width="{layout_w * scale}" height="{layout_h * scale}" '
        'fill="none" stroke="#334155" stroke-width="1" stroke-dasharray="4,4"/>'
    )
    header = (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{view_width}" height="{view_height}" '
        f'viewBox="0 0 {view_width} {view_height}" role="img">'
    )

    svg_lines = [
        header,
        f"  <title>{cell.name} Physical IC Layout</title>",
        f'  <rect width="{view_width}" height="{view_height}" fill="#0f172a"/>',
        '  <g id="grid_border">',
        grid_rect,
        "  </g>",
        '  <g id="shapes">',
    ]

    # Render layout rectangles ordered by layer stack
    sorted_rects = sorted(cell.rectangles, key=lambda r: int(r.layer))
    for r in sorted_rects:
        style = LAYER_STYLES.get(r.layer, {"fill": "#94a3b8", "stroke": "#64748b", "opacity": "0.7"})
        rx = tx(r.x_min_nm)
        ry = ty(r.y_max_nm)
        rw = r.width_nm * scale
        rh = r.height_nm * scale
        fill = style["fill"]
        stroke = style["stroke"]
        op = style["opacity"]

        svg_lines.append(
            f'    <rect x="{rx:.2f}" y="{ry:.2f}" width="{rw:.2f}" height="{rh:.2f}" '
            f'fill="{fill}" fill-opacity="{op}" stroke="{stroke}" stroke-width="1">'
            f"<title>{r.layer.name}: {r.net_name} ({r.width_nm}x{r.height_nm}nm)</title></rect>"
        )

    svg_lines.append("  </g>")

    # Render IO Ports and labels
    if show_labels:
        svg_lines.append('  <g id="ports">')
        for p in cell.ports:
            px = tx(p.x_nm)
            py = ty(p.y_nm)
            svg_lines.append(
                f'    <circle cx="{px:.2f}" cy="{py:.2f}" r="3" fill="#ffffff" stroke="#ef4444" stroke-width="1"/>'
            )
        svg_lines.append("  </g>")

    # Title & Metadata Legend
    svg_lines.append(
        '  <text x="20" y="25" fill="#f8fafc" font-family="monospace" font-size="13" font-weight="bold">'
        f"CELL: {cell.name} | BBOX: {layout_w/1000:.2f}um x {layout_h/1000:.2f}um | SHAPES: {len(cell.rectangles)}"
        "</text>"
    )

    svg_lines.append("</svg>")

    out.write_text("\n".join(svg_lines), encoding="utf-8")
    return out
