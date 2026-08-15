"""Generate Chapter 0022 Partial Sums Scaling plot SVG.

Stdlib-only and deterministic: reads
``verification/circuit/results/partial-sums-0022-extract.json`` and renders

  panel 1: Monolithic IR-drop error vs Tiled (16x16 / 32x32) architecture across matrix size (16 .. 256).
  panel 2: Partial sum accumulation error (%) vs number of column blocks K_c (1 .. 32).

Run:  python book/0022-partial-sums/diagrams/make_plots.py
"""

from __future__ import annotations

import json
from pathlib import Path

_OUT = Path(__file__).with_name("partial_sums_scaling.svg")
_EXTRACT = Path(__file__).resolve().parents[3] / "verification" / "circuit" / "results" / "partial-sums-0022-extract.json"

W, H = 960, 560
M_LEFT, M_RIGHT, M_TOP, M_BOT = 70, 50, 90, 60
PANEL_W = 390
PANEL_H = 370
P1_X = M_LEFT
P2_X = M_LEFT + PANEL_W + 60

d = json.loads(_EXTRACT.read_text("utf-8"))

mono_vs_tiled = d["monolithic_vs_tiled_comparison"]
kc_data = d["partial_sum_scaling_kc"]

# Panel 1 coordinates: X = 0 .. 280 (matrix dim N), Y = 0 .. 100% (Error %)
def px1(dim: float) -> float:
    return P1_X + (dim / 280.0) * PANEL_W

def py1(err_pct: float) -> float:
    return M_TOP + PANEL_H - (min(err_pct, 100.0) / 100.0) * PANEL_H

# Panel 2 coordinates: X = 0 .. 35 (K_c), Y = 0 .. 30% (Error %)
def px2(kc: float) -> float:
    return P2_X + (kc / 35.0) * PANEL_W

def py2(err_pct: float) -> float:
    return M_TOP + PANEL_H - (err_pct / 30.0) * PANEL_H

elements = []

# --- Panel 1: Monolithic vs Tiled ---
t16_pts = []
t32_pts = []
mono_pts = []

for row in mono_vs_tiled:
    dim = row["dimension"]
    e16 = row["tiled_16x16_error_pct"]
    e32 = row["tiled_32x32_error_pct"]
    emono = row["monolithic_ir_error_pct"]

    x = px1(dim)
    y16 = py1(e16)
    y32 = py1(e32)
    ymono = py1(emono)

    t16_pts.append(f"{x:.1f},{y16:.1f}")
    t32_pts.append(f"{x:.1f},{y32:.1f}")
    mono_pts.append(f"{x:.1f},{ymono:.1f}")

    elements.append(f'<circle cx="{x:.1f}" cy="{y16:.1f}" r="4" fill="#10b981"/>')
    elements.append(f'<circle cx="{x:.1f}" cy="{y32:.1f}" r="4" fill="#3b82f6"/>')
    elements.append(f'<circle cx="{x:.1f}" cy="{ymono:.1f}" r="4" fill="#ef4444"/>')

elements.append(f'<polyline points="{" ".join(mono_pts)}" fill="none" stroke="#ef4444" stroke-width="2.5"/>')
elements.append(f'<polyline points="{" ".join(t32_pts)}" fill="none" stroke="#3b82f6" stroke-width="2"/>')
elements.append(f'<polyline points="{" ".join(t16_pts)}" fill="none" stroke="#10b981" stroke-width="2"/>')

# Panel 1 X-ticks
for dim in [16, 32, 64, 128, 256]:
    x = px1(dim)
    elements.append(f'<text x="{x:.1f}" y="{M_TOP + PANEL_H + 18:.1f}" text-anchor="middle" font-size="10" fill="#64748b">{dim}</text>')

# Panel 1 Y-ticks
for err in [0, 20, 40, 60, 80, 100]:
    y = py1(err)
    elements.append(f'<text x="{P1_X - 8:.1f}" y="{y + 4:.1f}" text-anchor="end" font-size="10" fill="#64748b">{err}%</text>')

# Panel 1 Legend
leg1_y = M_TOP + 15
elements.append(f'<line x1="{P1_X + 20}" y1="{leg1_y + 6}" x2="{P1_X + 45}" y2="{leg1_y + 6}" stroke="#ef4444" stroke-width="2.5"/>')
elements.append(f'<text x="{P1_X + 52}" y="{leg1_y + 10}" font-size="10" fill="#1e293b">Monolithic (IR Drop)</text>')
elements.append(f'<line x1="{P1_X + 20}" y1="{leg1_y + 26}" x2="{P1_X + 45}" y2="{leg1_y + 26}" stroke="#3b82f6" stroke-width="2"/>')
elements.append(f'<text x="{P1_X + 52}" y="{leg1_y + 30}" font-size="10" fill="#1e293b">Tiled 32×32</text>')
elements.append(f'<line x1="{P1_X + 20}" y1="{leg1_y + 46}" x2="{P1_X + 45}" y2="{leg1_y + 46}" stroke="#10b981" stroke-width="2"/>')
elements.append(f'<text x="{P1_X + 52}" y="{leg1_y + 50}" font-size="10" fill="#1e293b">Tiled 16×16</text>')

# --- Panel 2: Partial Sum Noise Scaling vs K_c ---
kc_pts = []
for row in kc_data:
    kc = row["num_partial_sums_kc"]
    err = row["mean_error_pct"]
    x = px2(kc)
    y = py2(err)
    kc_pts.append(f"{x:.1f},{y:.1f}")
    elements.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="4" fill="#8b5cf6"/>')
    elements.append(f'<text x="{x:.1f}" y="{y - 8:.1f}" text-anchor="middle" font-size="9" font-weight="bold" fill="#7c3aed">{err:.1f}%</text>')

elements.append(f'<polyline points="{" ".join(kc_pts)}" fill="none" stroke="#8b5cf6" stroke-width="2"/>')

# Panel 2 X-ticks
for kc in [1, 2, 4, 8, 16, 32]:
    x = px2(kc)
    elements.append(f'<text x="{x:.1f}" y="{M_TOP + PANEL_H + 18:.1f}" text-anchor="middle" font-size="10" fill="#64748b">{kc}</text>')

# Panel 2 Y-ticks
for err in [0, 5, 10, 15, 20, 25, 30]:
    y = py2(err)
    elements.append(f'<text x="{P2_X - 8:.1f}" y="{y + 4:.1f}" text-anchor="end" font-size="10" fill="#64748b">{err}%</text>')

# Helper grids
def make_grid(x_off: float, title: str, x_label: str, y_label: str) -> str:
    return f"""
    <text x="{x_off + PANEL_W/2:.0f}" y="{M_TOP - 18}" text-anchor="middle" font-size="13" font-weight="bold" fill="#0f172a">{title}</text>
    <rect x="{x_off}" y="{M_TOP}" width="{PANEL_W}" height="{PANEL_H}" fill="#f8fafc" stroke="#334155" stroke-width="1.5"/>
    <text x="{x_off + PANEL_W/2:.0f}" y="{M_TOP + PANEL_H + 36}" text-anchor="middle" font-size="10" fill="#64748b">{x_label}</text>
    <text x="{x_off - 35}" y="{M_TOP + PANEL_H/2}" text-anchor="middle" transform="rotate(-90 {x_off - 35} {M_TOP + PANEL_H/2})" font-size="10" fill="#64748b">{y_label}</text>
    """

g1 = make_grid(P1_X, "Panel 1: Monolithic IR Drop vs Tiled Scaling", "Matrix Dimension N (N×N)", "Relative MVM Error (%)")
g2 = make_grid(P2_X, "Panel 2: Partial Sum Noise Accumulation", "Number of Column Tiles K_c", "MVM Relative Error (%)")

svg_content = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" font-family="-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif">
  <rect width="{W}" height="{H}" fill="#ffffff"/>
  <text x="{W/2:.0f}" y="32" text-anchor="middle" font-size="18" font-weight="bold" fill="#0f172a">Partial Sums Scaling &amp; Tiling Architecture (0022)</text>
  <text x="{W/2:.0f}" y="52" text-anchor="middle" font-size="12" fill="#64748b">Spatial decomposition eliminates quadratic IR drop while bounding partial-sum quantization</text>

  {g1}
  {g2}

  {' '.join(elements)}
</svg>
"""

_OUT.write_text(svg_content, "utf-8")
print(f"Generated partial sums scaling SVG: {_OUT}")
