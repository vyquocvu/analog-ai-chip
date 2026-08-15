"""Generate the 0014 array scaling & noise gain plot SVG.

Stdlib-only and deterministic: reads
``verification/circuit/results/array-timing-0014-extract.json`` and renders

  panel 1: Closed-loop Noise Gain (NG) and DC gain error (%) vs row count N.
  panel 2: SPICE simulated MVM absolute error vs row count N.

Run:  python book/0014-array-timing/diagrams/make_plots.py
"""

from __future__ import annotations

import json
from pathlib import Path

_OUT = Path(__file__).with_name("scaling_plots.svg")
_EXTRACT = Path(__file__).resolve().parents[3] / "verification" / "circuit" / "results" / "array-timing-0014-extract.json"

W, H = 960, 620
M = 90
PLOT_W, PLOT_H = W - 2 * M, 210
TOP1, TOP2 = 80, 360

d = json.loads(_EXTRACT.read_text("utf-8"))
rows = d["row_scaling_sweep"]
n_points = len(rows)

ns = [r["n_rows"] for r in rows]
ngs = [r["noise_gain"] for r in rows]
errors_pct = [r["expected_gain_error"] * 100.0 for r in rows]
mvm_errs_mv = [r["mvm_abs_error"] * 1e3 for r in rows]  # mV

# Scaling helpers
def px(idx: int) -> float:
    return M + (idx / (n_points - 1)) * PLOT_W

def py1(val: float, max_val: float = 70.0) -> float:
    return TOP1 + PLOT_H - (val / max_val) * PLOT_H

def py2(val: float, max_val: float = 2.0) -> float:
    return TOP2 + PLOT_H - (val / max_val) * PLOT_H

# Build SVG
elements = []

# Panel 1: Noise Gain (left bars/points) & Gain Error % (right line)
ng_points = []
err_points = []
for i, r in enumerate(rows):
    x = px(i)
    y_ng = py1(r["noise_gain"])
    y_err = py1(r["expected_gain_error"] * 100.0, max_val=1.0)
    ng_points.append(f"{x:.1f},{y_ng:.1f}")
    err_points.append(f"{x:.1f},{y_err:.1f}")

    # Column Bar for Noise Gain
    elements.append(
        f'<rect x="{x - 18:.1f}" y="{y_ng:.1f}" width="36" height="{TOP1 + PLOT_H - y_ng:.1f}" '
        f'fill="#3b82f6" opacity="0.8" rx="3"/>'
    )
    elements.append(
        f'<text x="{x:.1f}" y="{y_ng - 8:.1f}" text-anchor="middle" font-size="11" font-weight="bold" fill="#1d4ed8">'
        f'NG={r["noise_gain"]:.0f}</text>'
    )
    # X-axis labels
    elements.append(
        f'<text x="{x:.1f}" y="{TOP1 + PLOT_H + 20:.1f}" text-anchor="middle" font-size="11" fill="#475569">'
        f'N={r["n_rows"]}</text>'
    )

# Panel 2: MVM Error (mV)
for i, r in enumerate(rows):
    x = px(i)
    err_mv = r["mvm_abs_error"] * 1e3
    y_mv = py2(err_mv, max_val=2.0)
    elements.append(
        f'<rect x="{x - 18:.1f}" y="{y_mv:.1f}" width="36" height="{TOP2 + PLOT_H - y_mv:.1f}" '
        f'fill="#ea580c" opacity="0.8" rx="3"/>'
    )
    elements.append(
        f'<text x="{x:.1f}" y="{y_mv - 8:.1f}" text-anchor="middle" font-size="11" font-weight="bold" fill="#c2410c">'
        f'{err_mv:.3f} mV</text>'
    )
    elements.append(
        f'<text x="{x:.1f}" y="{TOP2 + PLOT_H + 20:.1f}" text-anchor="middle" font-size="11" fill="#475569">'
        f'N={r["n_rows"]}</text>'
    )

# Grid and reference lines
def grid_panel(top: float, title: str, y_label: str) -> str:
    lines = [
        f'<text x="{W/2:.0f}" y="{top - 20}" text-anchor="middle" font-size="14" font-weight="bold" fill="#0f172a">{title}</text>',
        f'<line x1="{M}" y1="{top}" x2="{M + PLOT_W}" y2="{top}" stroke="#e2e8f0" stroke-dasharray="4"/>',
        f'<line x1="{M}" y1="{top + PLOT_H/2}" x2="{M + PLOT_W}" y2="{top + PLOT_H/2}" stroke="#e2e8f0" stroke-dasharray="4"/>',
        f'<line x1="{M}" y1="{top + PLOT_H}" x2="{M + PLOT_W}" y2="{top + PLOT_H}" stroke="#334155" stroke-width="1.5"/>',
        f'<line x1="{M}" y1="{top}" x2="{M}" y2="{top + PLOT_H}" stroke="#334155" stroke-width="1.5"/>',
        f'<text x="{M - 12}" y="{top + PLOT_H/2}" text-anchor="middle" transform="rotate(-90 {M - 12} {top + PLOT_H/2})" font-size="11" fill="#64748b">{y_label}</text>',
    ]
    return "\n".join(lines)

p1_grid = grid_panel(TOP1, "Panel 1: Closed-Loop Noise Gain Scaling (NG = 1 + N · RF · G0)", "Noise Gain (V/V)")
p2_grid = grid_panel(TOP2, "Panel 2: SPICE Differential MVM Absolute Error vs Row Count N", "Output Error (mV)")

svg_content = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" font-family="-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif">
  <rect width="{W}" height="{H}" fill="#ffffff"/>
  <text x="{W/2:.0f}" y="30" text-anchor="middle" font-size="18" font-weight="bold" fill="#0f172a">Crossbar Array Loading &amp; Scaling Sweeps (0014)</text>
  <text x="{W/2:.0f}" y="50" text-anchor="middle" font-size="12" fill="#64748b">Measured in SPICE operating point solves across row dimensions N = 2 .. 64 with RF=10k, G0=0.1mS, A_OL=1e4</text>

  {p1_grid}
  {p2_grid}

  <!-- Data elements -->
  {' '.join(elements)}
</svg>
"""

_OUT.write_text(svg_content, "utf-8")
print(f"Generated scaling plots SVG: {_OUT}")
