"""Generate Chapter 0016 Monte Carlo variation & differential weight SNR plot SVG.

Stdlib-only and deterministic: reads
``verification/circuit/results/variation-0016-extract.json`` and renders

  panel 1: Conductance standard deviation (uS) vs state index (empirical vs theoretical).
  panel 2: Differential weight error dispersion sigma_w(w) (%) across target weights [-1, 1].

Run:  python book/0016-variation/diagrams/make_plots.py
"""

from __future__ import annotations

import json
from pathlib import Path

_OUT = Path(__file__).with_name("monte_carlo_distribution.svg")
_EXTRACT = Path(__file__).resolve().parents[3] / "verification" / "circuit" / "results" / "variation-0016-extract.json"

W, H = 960, 620
M = 90
PLOT_W, PLOT_H = W - 2 * M, 210
TOP1, TOP2 = 80, 360

d = json.loads(_EXTRACT.read_text("utf-8"))
state_stats = d["state_variation_statistics"]
weight_stats = d["weight_variation_statistics"]

def px1(idx: int) -> float:
    return M + (idx / (len(state_stats) - 1)) * PLOT_W

def py1(std_us: float) -> float:
    # 0 to 4.0 uS
    return TOP1 + PLOT_H - (std_us / 4.0) * PLOT_H

def px2(w: float) -> float:
    return M + ((w + 1.0) / 2.0) * PLOT_W

def py2(std_w_pct: float) -> float:
    # 0 to 4.0%
    return TOP2 + PLOT_H - (std_w_pct / 4.0) * PLOT_H

elements = []

# Panel 1: State Std Dev (Bars = Empirical, Points/Line = Expected)
exp_points = []
for i, s in enumerate(state_stats):
    x = px1(i)
    emp = s["empirical_std_uS"]
    exp = s["expected_std_uS"]
    y_emp = py1(emp)
    y_exp = py1(exp)
    exp_points.append(f"{x:.1f},{y_exp:.1f}")

    elements.append(
        f'<rect x="{x - 12:.1f}" y="{y_emp:.1f}" width="24" height="{TOP1 + PLOT_H - y_emp:.1f}" '
        f'fill="#3b82f6" opacity="0.8" rx="2"/>'
    )
    elements.append(
        f'<circle cx="{x:.1f}" cy="{y_exp:.1f}" r="3" fill="#ea580c"/>'
    )
    elements.append(
        f'<text x="{x:.1f}" y="{TOP1 + PLOT_H + 18:.1f}" text-anchor="middle" font-size="10" fill="#475569">'
        f'S{i}</text>'
    )

elements.append(
    f'<polyline points="{" ".join(exp_points)}" fill="none" stroke="#ea580c" stroke-width="2" stroke-dasharray="3"/>'
)

# Panel 2: Differential Weight Standard Deviation
th_w_points = []
emp_w_points = []
for w_row in weight_stats:
    x = px2(w_row["w_target"])
    emp_pct = w_row["empirical_std_w"] * 100.0
    th_pct = w_row["theoretical_std_w"] * 100.0
    y_emp = py2(emp_pct)
    y_th = py2(th_pct)
    emp_w_points.append(f"{x:.1f},{y_emp:.1f}")
    th_w_points.append(f"{x:.1f},{y_th:.1f}")

    elements.append(
        f'<circle cx="{x:.1f}" cy="{y_emp:.1f}" r="4" fill="#2563eb"/>'
    )

elements.append(
    f'<polyline points="{" ".join(th_w_points)}" fill="none" stroke="#ea580c" stroke-width="2" stroke-dasharray="4"/>'
)
elements.append(
    f'<polyline points="{" ".join(emp_w_points)}" fill="none" stroke="#2563eb" stroke-width="2"/>'
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

p1_grid = grid(TOP1, "Panel 1: Conductance Std Dev per State (1000-Trial Monte Carlo vs G_k · σ_tot)", "Std Dev σ_G (uS)")
p2_grid = grid(TOP2, "Panel 2: Differential Weight Standard Deviation σ_w(w) across Target Weights", "Weight Std Dev σ_w (%)")

svg_content = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" font-family="-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif">
  <rect width="{W}" height="{H}" fill="#ffffff"/>
  <text x="{W/2:.0f}" y="30" text-anchor="middle" font-size="18" font-weight="bold" fill="#0f172a">Monte Carlo Programming &amp; Read Variability Sweeps (0016)</text>
  <text x="{W/2:.0f}" y="50" text-anchor="middle" font-size="12" fill="#64748b">σ_prog = 3.0%, σ_read = 1.0%, σ_tot = 3.16%, N=1000 trials/state, Seed = 42</text>

  {p1_grid}
  {p2_grid}

  <!-- Panel 1 Legend -->
  <rect x="{W - 200}" y="{TOP1 + 10}" width="12" height="12" fill="#3b82f6" opacity="0.8"/>
  <text x="{W - 180}" y="{TOP1 + 20}" font-size="11" fill="#0f172a">Empirical Monte Carlo</text>
  <line x1="{W - 200}" y1="{TOP1 + 35}" x2="{W - 185}" y2="{TOP1 + 35}" stroke="#ea580c" stroke-width="2" stroke-dasharray="3"/>
  <text x="{W - 180}" y="{TOP1 + 38}" font-size="11" fill="#64748b">Theoretical G_k·σ_tot</text>

  <!-- Panel 2 X-Axis Labels -->
  <text x="{px2(-1.0):.0f}" y="{TOP2 + PLOT_H + 20}" text-anchor="middle" font-size="11" fill="#475569">-1.0</text>
  <text x="{px2(-0.5):.0f}" y="{TOP2 + PLOT_H + 20}" text-anchor="middle" font-size="11" fill="#475569">-0.5</text>
  <text x="{px2(0.0):.0f}" y="{TOP2 + PLOT_H + 20}" text-anchor="middle" font-size="11" fill="#475569">0.0 (w_target)</text>
  <text x="{px2(0.5):.0f}" y="{TOP2 + PLOT_H + 20}" text-anchor="middle" font-size="11" fill="#475569">+0.5</text>
  <text x="{px2(1.0):.0f}" y="{TOP2 + PLOT_H + 20}" text-anchor="middle" font-size="11" fill="#475569">+1.0</text>

  <!-- Panel 2 Legend -->
  <circle cx="{W - 195}" cy="{TOP2 + 15}" r="4" fill="#2563eb"/>
  <text x="{W - 180}" y="{TOP2 + 18}" font-size="11" fill="#0f172a">Empirical σ_w</text>
  <line x1="{W - 200}" y1="{TOP2 + 35}" x2="{W - 185}" y2="{TOP2 + 35}" stroke="#ea580c" stroke-width="2" stroke-dasharray="4"/>
  <text x="{W - 180}" y="{TOP2 + 38}" font-size="11" fill="#64748b">Theoretical σ_w(w)</text>

  <!-- Data elements -->
  {' '.join(elements)}
</svg>
"""

_OUT.write_text(svg_content, "utf-8")
print(f"Generated Monte Carlo variation SVG: {_OUT}")
