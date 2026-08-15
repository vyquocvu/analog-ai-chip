"""Generate Chapter 0017 IR drop scaling & voltage deficit plot SVG.

Stdlib-only and deterministic: reads
``verification/circuit/results/ir-drop-0017-extract.json`` and renders

  panel 1: Relative MVM Error (%) vs Array Size N across wire resistances (0.5 Ohm, 1.0 Ohm, 2.0 Ohm).
  panel 2: Far-corner cell voltage deficit (%) vs Array Size N.

Run:  python book/0017-ir-drop/diagrams/make_plots.py
"""

from __future__ import annotations

import json
from pathlib import Path

_OUT = Path(__file__).with_name("ir_drop_scaling.svg")
_EXTRACT = Path(__file__).resolve().parents[3] / "verification" / "circuit" / "results" / "ir-drop-0017-extract.json"

W, H = 960, 620
M = 90
PLOT_W, PLOT_H = W - 2 * M, 210
TOP1, TOP2 = 80, 360

d = json.loads(_EXTRACT.read_text("utf-8"))
results = d["scaling_results"]
n_points = len(results)

def px(idx: int) -> float:
    return M + (idx / (n_points - 1)) * PLOT_W

def py1(err_pct: float) -> float:
    # 0 to 50%
    return TOP1 + PLOT_H - (err_pct / 50.0) * PLOT_H

def py2(def_pct: float) -> float:
    # 0 to 50%
    return TOP2 + PLOT_H - (def_pct / 50.0) * PLOT_H

elements = []

# Series for Panel 1
series_p1 = [
    ("r_0.5ohm", "#10b981", "R_wire = 0.5 Ohm"),
    ("r_1.0ohm", "#2563eb", "R_wire = 1.0 Ohm"),
    ("r_2.0ohm", "#ea580c", "R_wire = 2.0 Ohm"),
]

for key, color, _ in series_p1:
    pts = []
    for i, r in enumerate(results):
        x = px(i)
        err = r["r_wire_sweeps"][key]["rel_error_pct"]
        y = py1(err)
        pts.append(f"{x:.1f},{y:.1f}")
        elements.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="4" fill="{color}"/>')
    elements.append(f'<polyline points="{" ".join(pts)}" fill="none" stroke="{color}" stroke-width="2"/>')

# Panel 1 X-labels & 10% budget line
y_budget = py1(10.0)
elements.append(
    f'<line x1="{M}" y1="{y_budget}" x2="{M + PLOT_W}" y2="{y_budget}" stroke="#dc2626" stroke-width="1.5" stroke-dasharray="4"/>'
)
elements.append(
    f'<text x="{M + PLOT_W - 10}" y="{y_budget - 6}" text-anchor="end" font-size="10" font-weight="bold" fill="#dc2626">10% Error Budget Limit</text>'
)

for i, r in enumerate(results):
    x = px(i)
    elements.append(
        f'<text x="{x:.1f}" y="{TOP1 + PLOT_H + 18:.1f}" text-anchor="middle" font-size="10" fill="#475569">'
        f'{r["size"]}x{r["size"]}</text>'
    )

# Panel 2: Far Corner Voltage Deficit (%)
for key, color, _ in series_p1:
    pts2 = []
    for i, r in enumerate(results):
        x = px(i)
        v_def = r["r_wire_sweeps"][key]["voltage_deficit_pct"]
        y = py2(v_def)
        pts2.append(f"{x:.1f},{y:.1f}")
        elements.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="4" fill="{color}"/>')
    elements.append(f'<polyline points="{" ".join(pts2)}" fill="none" stroke="{color}" stroke-width="2"/>')

for i, r in enumerate(results):
    x = px(i)
    elements.append(
        f'<text x="{x:.1f}" y="{TOP2 + PLOT_H + 18:.1f}" text-anchor="middle" font-size="10" fill="#475569">'
        f'{r["size"]}x{r["size"]}</text>'
    )

# Grid generator
def grid(top: float, title: str, y_label: str) -> str:
    return f"""
    <text x="{W/2:.0f}" y="{top - 20}" text-anchor="middle" font-size="14" font-weight="bold" fill="#0f172a">{title}</text>
    <line x1="{M}" y1="{top}" x2="{M + PLOT_W}" y2="{top}" stroke="#e2e8f0" stroke-dasharray="4"/>
    <line x1="{M}" y1="{top + PLOT_H/2}" x2="{M + PLOT_W}" y2="{top + PLOT_H/2}" stroke="#e2e8f0" stroke-dasharray="4"/>
    <line x1="{M}" y1="{top + PLOT_H}" x2="{M + PLOT_W}" y2="{top + PLOT_H}" stroke="#334155" stroke-width="1.5"/>
    <line x1="{M}" y1="{top}" x2="{M}" y2="{top + PLOT_H}" stroke="#334155" stroke-width="1.5"/>
    <text x="{M - 15}" y="{top + PLOT_H/2}" text-anchor="middle" transform="rotate(-90 {M - 15} {top + PLOT_H/2})" font-size="11" fill="#64748b">{y_label}</text>
    """

p1_grid = grid(TOP1, "Panel 1: Relative MVM Output Error (%) vs Array Size N", "MVM Error (%)")
p2_grid = grid(TOP2, "Panel 2: Far-Corner Cell Voltage Deficit (%) vs Array Size N", "Voltage Deficit (%)")

# Legend items
legend_items = []
for k, (_, color, label) in enumerate(series_p1):
    lx = W - 220
    ly = TOP1 + 10 + k * 18
    legend_items.append(f'<line x1="{lx}" y1="{ly}" x2="{lx + 20}" y2="{ly}" stroke="{color}" stroke-width="2"/>')
    legend_items.append(f'<circle cx="{lx + 10}" cy="{ly}" r="3" fill="{color}"/>')
    legend_items.append(f'<text x="{lx + 28}" y="{ly + 4}" font-size="10" fill="#0f172a">{label}</text>')

svg_content = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" font-family="-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif">
  <rect width="{W}" height="{H}" fill="#ffffff"/>
  <text x="{W/2:.0f}" y="30" text-anchor="middle" font-size="18" font-weight="bold" fill="#0f172a">Crossbar IR Drop &amp; Wire Resistance Scaling (0017)</text>
  <text x="{W/2:.0f}" y="50" text-anchor="middle" font-size="12" fill="#64748b">Worst-case all-LRS conductance (G_max = 100 uS), V_read = 0.25 V, array size N = 2 .. 64</text>

  {p1_grid}
  {p2_grid}

  {' '.join(legend_items)}
  {' '.join(elements)}
</svg>
"""

_OUT.write_text(svg_content, "utf-8")
print(f"Generated IR drop scaling SVG: {_OUT}")
