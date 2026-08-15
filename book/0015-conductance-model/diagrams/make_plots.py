"""Generate Chapter 0015 conductance states and differential weight mapping plot SVG.

Stdlib-only and deterministic: reads
``verification/circuit/results/conductance-model-0015-extract.json`` and renders

  panel 1: Discrete 4-bit (16-level) programmed conductance states (uS).
  panel 2: Differential signed weight transfer w_target vs w_effective over [-1, 1].

Run:  python book/0015-conductance-model/diagrams/make_plots.py
"""

from __future__ import annotations

import json
from pathlib import Path

_OUT = Path(__file__).with_name("state_levels.svg")
_EXTRACT = Path(__file__).resolve().parents[3] / "verification" / "circuit" / "results" / "conductance-model-0015-extract.json"

W, H = 960, 620
M = 90
PLOT_W, PLOT_H = W - 2 * M, 210
TOP1, TOP2 = 80, 360

d = json.loads(_EXTRACT.read_text("utf-8"))
states = d["states_4bit"]
weights = d["weight_mappings"]

# Helper functions
def px1(idx: int) -> float:
    return M + (idx / (len(states) - 1)) * PLOT_W

def py1(g_us: float) -> float:
    # 0 to 110 uS
    return TOP1 + PLOT_H - (g_us / 110.0) * PLOT_H

def px2(w: float) -> float:
    # -1.0 to 1.0
    return M + ((w + 1.0) / 2.0) * PLOT_W

def py2(w_eff: float) -> float:
    # -1.0 to 1.0
    return TOP2 + PLOT_H - ((w_eff + 1.0) / 2.0) * PLOT_H

elements = []

# Panel 1: Conductance States
for i, s in enumerate(states):
    x = px1(i)
    g = s["conductance_uS"]
    y = py1(g)
    elements.append(
        f'<rect x="{x - 14:.1f}" y="{y:.1f}" width="28" height="{TOP1 + PLOT_H - y:.1f}" '
        f'fill="#2563eb" opacity="0.85" rx="2"/>'
    )
    elements.append(
        f'<text x="{x:.1f}" y="{y - 6:.1f}" text-anchor="middle" font-size="10" font-weight="bold" fill="#1d4ed8">'
        f'{g:.1f}</text>'
    )
    elements.append(
        f'<text x="{x:.1f}" y="{TOP1 + PLOT_H + 18:.1f}" text-anchor="middle" font-size="10" fill="#475569">'
        f'S{i}</text>'
    )

# Panel 2: Differential Weight Mapping (Staircase vs Ideal Line)
# Ideal diagonal line
x_min, y_min = px2(-1.0), py2(-1.0)
x_max, y_max = px2(1.0), py2(1.0)
elements.append(
    f'<line x1="{x_min}" y1="{y_min}" x2="{x_max}" y2="{y_max}" stroke="#cbd5e1" stroke-width="2" stroke-dasharray="4"/>'
)

# Quantized weight steps
w_pts = []
for row in weights:
    x = px2(row["w_target"])
    y = py2(row["w_effective"])
    w_pts.append(f"{x:.1f},{y:.1f}")
    elements.append(
        f'<circle cx="{x:.1f}" cy="{y:.1f}" r="4" fill="#ea580c"/>'
    )

elements.append(
    f'<polyline points="{" ".join(w_pts)}" fill="none" stroke="#ea580c" stroke-width="2"/>'
)

# Grids
def grid(top: float, title: str, y_label: str) -> str:
    return f"""
    <text x="{W/2:.0f}" y="{top - 20}" text-anchor="middle" font-size="14" font-weight="bold" fill="#0f172a">{title}</text>
    <line x1="{M}" y1="{top}" x2="{M + PLOT_W}" y2="{top}" stroke="#e2e8f0" stroke-dasharray="4"/>
    <line x1="{M}" y1="{top + PLOT_H/2}" x2="{M + PLOT_W}" y2="{top + PLOT_H/2}" stroke="#e2e8f0" stroke-dasharray="4"/>
    <line x1="{M}" y1="{top + PLOT_H}" x2="{M + PLOT_W}" y2="{top + PLOT_H}" stroke="#334155" stroke-width="1.5"/>
    <line x1="{M}" y1="{top}" x2="{M}" y2="{top + PLOT_H}" stroke="#334155" stroke-width="1.5"/>
    <text x="{M - 15}" y="{top + PLOT_H/2}" text-anchor="middle" transform="rotate(-90 {M - 15} {top + PLOT_H/2})" font-size="11" fill="#64748b">{y_label}</text>
    """

p1_grid = grid(TOP1, "Panel 1: Programmed 4-Bit Discrete Conductance Levels (16 States: 10 uS .. 100 uS)", "Conductance (uS)")
p2_grid = grid(TOP2, "Panel 2: Differential Signed Weight Transfer Curve (w_target vs w_effective)", "Effective Weight w_eff")

svg_content = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" font-family="-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif">
  <rect width="{W}" height="{H}" fill="#ffffff"/>
  <text x="{W/2:.0f}" y="30" text-anchor="middle" font-size="18" font-weight="bold" fill="#0f172a">Conductance State Discretization &amp; Differential Weight Transfer (0015)</text>
  <text x="{W/2:.0f}" y="50" text-anchor="middle" font-size="12" fill="#64748b">G_min = 10 uS (HRS), G_max = 100 uS (LRS), Span = 90 uS, Step = 6.0 uS/state</text>

  {p1_grid}
  {p2_grid}

  <!-- Axis labels for Panel 2 -->
  <text x="{px2(-1.0):.0f}" y="{TOP2 + PLOT_H + 20}" text-anchor="middle" font-size="11" fill="#475569">-1.0</text>
  <text x="{px2(-0.5):.0f}" y="{TOP2 + PLOT_H + 20}" text-anchor="middle" font-size="11" fill="#475569">-0.5</text>
  <text x="{px2(0.0):.0f}" y="{TOP2 + PLOT_H + 20}" text-anchor="middle" font-size="11" fill="#475569">0.0 (w_target)</text>
  <text x="{px2(0.5):.0f}" y="{TOP2 + PLOT_H + 20}" text-anchor="middle" font-size="11" fill="#475569">+0.5</text>
  <text x="{px2(1.0):.0f}" y="{TOP2 + PLOT_H + 20}" text-anchor="middle" font-size="11" fill="#475569">+1.0</text>

  <!-- Legend -->
  <circle cx="{W - 180}" cy="{TOP2 + 25}" r="4" fill="#ea580c"/>
  <text x="{W - 170}" y="{TOP2 + 28}" font-size="11" fill="#0f172a">Quantized Weight (4-bit)</text>
  <line x1="{W - 185}" y1="{TOP2 + 45}" x2="{W - 155}" y2="{TOP2 + 45}" stroke="#cbd5e1" stroke-width="2" stroke-dasharray="4"/>
  <text x="{W - 150}" y="{TOP2 + 48}" font-size="11" fill="#64748b">Ideal Linear Transfer</text>

  <!-- Plot Elements -->
  {' '.join(elements)}
</svg>
"""

_OUT.write_text(svg_content, "utf-8")
print(f"Generated state levels SVG: {_OUT}")
