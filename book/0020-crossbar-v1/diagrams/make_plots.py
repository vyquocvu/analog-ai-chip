"""Generate Chapter 0020 Error Budget Breakdown plot SVG for crossbar-v1.

Stdlib-only and deterministic: renders an error contribution comparison chart
across all physical non-idealities modeled in Gate R4 (Chapters 0015-0019).

Run:  python book/0020-crossbar-v1/diagrams/make_plots.py
"""

from __future__ import annotations

from pathlib import Path

_OUT = Path(__file__).with_name("error_budget_breakdown.svg")

W, H = 960, 560
M_LEFT, M_RIGHT, M_TOP, M_BOT = 260, 60, 90, 60
PLOT_W = W - M_LEFT - M_RIGHT
PLOT_H = H - M_TOP - M_BOT

# Data items: (Category, Label, Error %, Color)
data = [
    ("Quantization", "4-Bit Discretization Step (0015)", 3.33, "#3b82f6"),
    ("Quantization", "6-Bit Discretization Step (0015)", 0.79, "#60a5fa"),
    ("Noise", "Stochastic Noise @ w=0 (0016)", 0.50, "#10b981"),
    ("Noise", "Stochastic Noise @ |w|=1 (0016)", 3.53, "#059669"),
    ("IR Drop", "IR Drop @ 16x16 (1.0 Ohm) (0017)", 1.87, "#f59e0b"),
    ("IR Drop", "IR Drop @ 32x32 (1.0 Ohm) (0017)", 6.77, "#d97706"),
    ("IR Drop", "IR Drop @ 64x64 (1.0 Ohm) (0017)", 21.84, "#dc2626"),
    ("Defects", "Stuck Defects @ 0.5% Faults (0019)", 5.64, "#8b5cf6"),
    ("Defects", "Stuck Defects @ 1.0% Faults (0019)", 9.21, "#7c3aed"),
    ("Non-Linearity", "I-V Cubic Distortion @ 0.25V (0019)", 6.25, "#ec4899"),
]

N = len(data)
bar_height = 28
bar_gap = (PLOT_H - N * bar_height) / (N + 1)

def px(err_pct: float) -> float:
    # 0 to 25%
    return M_LEFT + (err_pct / 25.0) * PLOT_W

elements = []

# Grid lines and X-axis labels
for pct in [0, 5, 10, 15, 20, 25]:
    x = px(pct)
    elements.append(f'<line x1="{x:.1f}" y1="{M_TOP}" x2="{x:.1f}" y2="{M_TOP + PLOT_H}" stroke="#e2e8f0" stroke-dasharray="4"/>')
    elements.append(f'<text x="{x:.1f}" y="{M_TOP + PLOT_H + 20:.1f}" text-anchor="middle" font-size="11" fill="#64748b">{pct}%</text>')

# 10% Error Budget Limit Line
x_10 = px(10.0)
elements.append(f'<line x1="{x_10:.1f}" y1="{M_TOP - 10}" x2="{x_10:.1f}" y2="{M_TOP + PLOT_H}" stroke="#dc2626" stroke-width="2" stroke-dasharray="6"/>')
elements.append(f'<text x="{x_10:.1f}" y="{M_TOP - 16}" text-anchor="middle" font-size="11" font-weight="bold" fill="#dc2626">10% System Error Budget Limit</text>')

# Render horizontal bars
for i, (cat, label, val, color) in enumerate(data):
    y = M_TOP + bar_gap + i * (bar_height + bar_gap)
    w_bar = (val / 25.0) * PLOT_W
    elements.append(f'<rect x="{M_LEFT}" y="{y:.1f}" width="{w_bar:.1f}" height="{bar_height}" fill="{color}" rx="3"/>')
    elements.append(f'<text x="{M_LEFT - 12}" y="{y + 18:.1f}" text-anchor="end" font-size="11" font-weight="500" fill="#1e293b">{label}</text>')
    elements.append(f'<text x="{M_LEFT + w_bar + 8:.1f}" y="{y + 18:.1f}" font-size="11" font-weight="bold" fill="{color}">{val:.2f}%</text>')

# Axes lines
elements.append(f'<line x1="{M_LEFT}" y1="{M_TOP}" x2="{M_LEFT}" y2="{M_TOP + PLOT_H}" stroke="#334155" stroke-width="2"/>')
elements.append(f'<line x1="{M_LEFT}" y1="{M_TOP + PLOT_H}" x2="{M_LEFT + PLOT_W}" y2="{M_TOP + PLOT_H}" stroke="#334155" stroke-width="2"/>')

svg_content = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" font-family="-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif">
  <rect width="{W}" height="{H}" fill="#ffffff"/>
  <text x="{W/2:.0f}" y="32" text-anchor="middle" font-size="18" font-weight="bold" fill="#0f172a">Crossbar-v1 Non-Ideality Error Budget Breakdown (0020)</text>
  <text x="{W/2:.0f}" y="52" text-anchor="middle" font-size="12" fill="#64748b">Relative MVM error contributions across all Gate R4 physical non-ideality mechanisms</text>

  <text x="{M_LEFT + PLOT_W/2:.0f}" y="{M_TOP + PLOT_H + 45}" text-anchor="middle" font-size="12" font-weight="bold" fill="#334155">Relative Computation Error (%)</text>

  {' '.join(elements)}
</svg>
"""

_OUT.write_text(svg_content, "utf-8")
print(f"Generated error budget breakdown SVG: {_OUT}")
