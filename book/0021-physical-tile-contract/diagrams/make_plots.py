"""Generate Chapter 0021 Physical Tile Linearity & Error plot SVG.

Stdlib-only and deterministic: reads
``verification/circuit/results/physical-tile-0021-extract.json`` and renders

  panel 1: Tile transfer characteristic (y_tile vs y_ideal) over scale sweep [-1, 1].
  panel 2: Relative MVM error (%) across canonical matrix classes (4-bit vs 6-bit cell).

Run:  python book/0021-physical-tile-contract/diagrams/make_plots.py
"""

from __future__ import annotations

import json
from pathlib import Path

_OUT = Path(__file__).with_name("physical_tile_linearity.svg")
_EXTRACT = Path(__file__).resolve().parents[3] / "verification" / "circuit" / "results" / "physical-tile-0021-extract.json"

W, H = 960, 560
M_LEFT, M_RIGHT, M_TOP, M_BOT = 70, 50, 90, 60
PANEL_W = 390
PANEL_H = 370
P1_X = M_LEFT
P2_X = M_LEFT + PANEL_W + 60

d = json.loads(_EXTRACT.read_text("utf-8"))

curve_data = d["transfer_curve_50pts"]
matrix_data = d["canonical_matrix_results_16x16"]

# Panel 1: X = -3.0 .. +3.0 (y_ideal), Y = -3.0 .. +3.0 (y_tile)
def px1(val: float) -> float:
    return P1_X + ((val + 3.0) / 6.0) * PANEL_W

def py1(val: float) -> float:
    return M_TOP + PANEL_H - ((val + 3.0) / 6.0) * PANEL_H

elements = []

# --- Panel 1: Linearity Curve ---
ideal_pts = []
actual_pts = []
for pt in curve_data:
    x_ideal = pt["ideal_out_0"]
    y_tile = pt["tile_out_0"]
    xp = px1(x_ideal)
    yp_ideal = py1(x_ideal)
    yp_tile = py1(y_tile)
    ideal_pts.append(f"{xp:.1f},{yp_ideal:.1f}")
    actual_pts.append(f"{xp:.1f},{yp_tile:.1f}")
    elements.append(f'<circle cx="{xp:.1f}" cy="{yp_tile:.1f}" r="3" fill="#2563eb"/>')

# Diagonal ideal reference
elements.append(f'<line x1="{px1(-3.0):.1f}" y1="{py1(-3.0):.1f}" x2="{px1(3.0):.1f}" y2="{py1(3.0):.1f}" stroke="#94a3b8" stroke-width="1.5" stroke-dasharray="4"/>')
# Actual quantized staircase
elements.append(f'<polyline points="{" ".join(actual_pts)}" fill="none" stroke="#2563eb" stroke-width="2"/>')

for v in [-3, -2, -1, 0, 1, 2, 3]:
    xp = px1(v)
    yp = py1(v)
    elements.append(f'<text x="{xp:.1f}" y="{M_TOP + PANEL_H + 18:.1f}" text-anchor="middle" font-size="10" fill="#64748b">{v}</text>')
    elements.append(f'<text x="{P1_X - 8:.1f}" y="{yp + 4:.1f}" text-anchor="end" font-size="10" fill="#64748b">{v}</text>')

# --- Panel 2: Canonical Matrix Errors Bar Chart ---
cat_labels = [
    ("identity", "Identity"),
    ("positive_uniform", "Positive"),
    ("negative_uniform", "Negative"),
    ("mixed_sign", "Mixed-Sign"),
    ("rank_one", "Rank-1"),
    ("sparse_90pct", "Sparse (90%)"),
]

N_cats = len(cat_labels)
bar_gap = PANEL_H / (N_cats + 1)
bar_h = 16

def px2(err_pct: float) -> float:
    # 0 to 25%
    return P2_X + (err_pct / 25.0) * PANEL_W

for i, (key, label) in enumerate(cat_labels):
    row = matrix_data[key]
    err_4b = row["mean_error_4b_pct"]
    err_6b = row["mean_error_6b_pct"]
    y_center = M_TOP + (i + 1) * bar_gap

    # 4-bit bar
    w4 = (err_4b / 25.0) * PANEL_W
    y4 = y_center - bar_h - 2
    elements.append(f'<rect x="{P2_X}" y="{y4:.1f}" width="{w4:.1f}" height="{bar_h}" fill="#3b82f6" rx="2"/>')
    elements.append(f'<text x="{P2_X + w4 + 6:.1f}" y="{y4 + 12:.1f}" font-size="10" font-weight="bold" fill="#2563eb">{err_4b:.1f}%</text>')

    # 6-bit bar
    w6 = (err_6b / 25.0) * PANEL_W
    y6 = y_center + 2
    elements.append(f'<rect x="{P2_X}" y="{y6:.1f}" width="{w6:.1f}" height="{bar_h}" fill="#10b981" rx="2"/>')
    elements.append(f'<text x="{P2_X + w6 + 6:.1f}" y="{y6 + 12:.1f}" font-size="10" font-weight="bold" fill="#047857">{err_6b:.1f}%</text>')

    # Category label
    elements.append(f'<text x="{P2_X - 10:.1f}" y="{y_center + 4:.1f}" text-anchor="end" font-size="11" font-weight="500" fill="#1e293b">{label}</text>')

# Panel 2 X-ticks
for pct in [0, 5, 10, 15, 20, 25]:
    x = px2(pct)
    elements.append(f'<line x1="{x:.1f}" y1="{M_TOP}" x2="{x:.1f}" y2="{M_TOP + PANEL_H}" stroke="#e2e8f0" stroke-dasharray="4"/>')
    elements.append(f'<text x="{x:.1f}" y="{M_TOP + PANEL_H + 18:.1f}" text-anchor="middle" font-size="10" fill="#64748b">{pct}%</text>')

# Legend for Panel 2
leg_y = M_TOP + 15
elements.append(f'<rect x="{P2_X + PANEL_W - 130}" y="{leg_y}" width="12" height="12" fill="#3b82f6" rx="2"/>')
elements.append(f'<text x="{P2_X + PANEL_W - 112}" y="{leg_y + 10}" font-size="10" fill="#1e293b">4-bit Cell</text>')
elements.append(f'<rect x="{P2_X + PANEL_W - 60}" y="{leg_y}" width="12" height="12" fill="#10b981" rx="2"/>')
elements.append(f'<text x="{P2_X + PANEL_W - 42}" y="{leg_y + 10}" font-size="10" fill="#1e293b">6-bit Cell</text>')

# Helper grids
def make_grid(x_off: float, title: str, x_label: str, y_label: str) -> str:
    return f"""
    <text x="{x_off + PANEL_W/2:.0f}" y="{M_TOP - 18}" text-anchor="middle" font-size="13" font-weight="bold" fill="#0f172a">{title}</text>
    <rect x="{x_off}" y="{M_TOP}" width="{PANEL_W}" height="{PANEL_H}" fill="#f8fafc" stroke="#334155" stroke-width="1.5"/>
    <text x="{x_off + PANEL_W/2:.0f}" y="{M_TOP + PANEL_H + 36}" text-anchor="middle" font-size="10" fill="#64748b">{x_label}</text>
    <text x="{x_off - 35}" y="{M_TOP + PANEL_H/2}" text-anchor="middle" transform="rotate(-90 {x_off - 35} {M_TOP + PANEL_H/2})" font-size="10" fill="#64748b">{y_label}</text>
    """

g1 = make_grid(P1_X, "Panel 1: Transfer Characteristic", "Ideal Output y_ideal", "Tile Output y_tile")
g2 = make_grid(P2_X, "Panel 2: MVM Error across Matrix Classes", "Mean Relative Error (%)", "Matrix Class")

svg_content = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" font-family="-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif">
  <rect width="{W}" height="{H}" fill="#ffffff"/>
  <text x="{W/2:.0f}" y="32" text-anchor="middle" font-size="18" font-weight="bold" fill="#0f172a">Physical Tile Contract Linearity &amp; Error Response (0021)</text>
  <text x="{W/2:.0f}" y="52" text-anchor="middle" font-size="12" fill="#64748b">CrossbarTile execution consuming dac-r2r-v1 (4b) + crossbar-v1 (10-100 μS) + adc-sar-v1 (4b)</text>

  {g1}
  {g2}

  {' '.join(elements)}
</svg>
"""

_OUT.write_text(svg_content, "utf-8")
print(f"Generated physical tile linearity SVG: {_OUT}")
