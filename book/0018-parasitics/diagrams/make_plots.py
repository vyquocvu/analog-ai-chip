"""Generate Chapter 0018 transient waveforms & settling time plot SVG.

Stdlib-only and deterministic: reads
``verification/circuit/results/parasitics-0018-extract.json`` and renders

  panel 1: Transient current waveforms I_out(t) (uA) across array sizes N = 4 .. 64.
  panel 2: 1% Settling time t_settle (ps) and maximum frequency f_max (GHz) vs N.

Run:  python book/0018-parasitics/diagrams/make_plots.py
"""

from __future__ import annotations

import json
from pathlib import Path

_OUT = Path(__file__).with_name("transient_settling.svg")
_EXTRACT = Path(__file__).resolve().parents[3] / "verification" / "circuit" / "results" / "parasitics-0018-extract.json"

W, H = 960, 620
M = 90
PLOT_W, PLOT_H = W - 2 * M, 210
TOP1, TOP2 = 80, 360

d = json.loads(_EXTRACT.read_text("utf-8"))
results = d["sweep_results"]
n_points = len(results)

def px1(t_ns: float) -> float:
    # 0 to 1.0 ns
    t_clamped = min(max(t_ns, 0.0), 1.0)
    return M + (t_clamped / 1.0) * PLOT_W

def py1(i_ua: float) -> float:
    # 0 to 30 uA
    return TOP1 + PLOT_H - (i_ua / 30.0) * PLOT_H

def px2(idx: int) -> float:
    return M + (idx / (n_points - 1)) * PLOT_W

def py2_settle(ts_ps: float) -> float:
    # 0 to 30 ps
    return TOP2 + PLOT_H - (ts_ps / 30.0) * PLOT_H

def py2_freq(f_ghz: float) -> float:
    # 30 to 60 GHz
    return TOP2 + PLOT_H - ((f_ghz - 30.0) / 30.0) * PLOT_H

elements = []

colors = ["#10b981", "#3b82f6", "#6366f1", "#f97316", "#ef4444"]

# Panel 1: Waveforms
for i, r in enumerate(results):
    c = colors[i]
    times = r["waveform_sampled"]["time_ns"]
    currents = r["waveform_sampled"]["i_out_uA"]
    pts = []
    for t_ns, i_ua in zip(times, currents):
        if t_ns <= 1.0:
            x = px1(t_ns)
            y = py1(i_ua)
            pts.append(f"{x:.1f},{y:.1f}")
    if pts:
        elements.append(f'<polyline points="{" ".join(pts)}" fill="none" stroke="{c}" stroke-width="2"/>')

# Panel 1 X-labels
for t_val in [0.0, 0.2, 0.4, 0.6, 0.8, 1.0]:
    x = px1(t_val)
    elements.append(
        f'<text x="{x:.1f}" y="{TOP1 + PLOT_H + 18:.1f}" text-anchor="middle" font-size="10" fill="#475569">'
        f'{t_val:.1f} ns</text>'
    )

# Panel 2: Settling time (bars) and f_max (line)
f_pts = []
for i, r in enumerate(results):
    x = px2(i)
    ts = r["t_settle_1pct_ps"]
    fmax = r["f_max_ghz"]
    y_ts = py2_settle(ts)
    y_f = py2_freq(fmax)
    f_pts.append(f"{x:.1f},{y_f:.1f}")

    elements.append(
        f'<rect x="{x - 14:.1f}" y="{y_ts:.1f}" width="28" height="{TOP2 + PLOT_H - y_ts:.1f}" '
        f'fill="#3b82f6" opacity="0.8" rx="2"/>'
    )
    elements.append(f'<circle cx="{x:.1f}" cy="{y_f:.1f}" r="4" fill="#ea580c"/>')
    elements.append(
        f'<text x="{x:.1f}" y="{TOP2 + PLOT_H + 18:.1f}" text-anchor="middle" font-size="10" fill="#475569">'
        f'N={r["size"]}</text>'
    )

elements.append(f'<polyline points="{" ".join(f_pts)}" fill="none" stroke="#ea580c" stroke-width="2"/>')

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

p1_grid = grid(TOP1, "Panel 1: Step Response Waveforms I_out(t) vs Time across Array Sizes", "Output Current (uA)")
p2_grid = grid(TOP2, "Panel 2: 1% Settling Time (ps, Bars) and Max Frequency (GHz, Line) vs N", "Settling Time t_settle (ps)")

# Legend items Panel 1
leg1 = []
for i, r in enumerate(results):
    lx = W - 180
    ly = TOP1 + 10 + i * 16
    c = colors[i]
    leg1.append(f'<line x1="{lx}" y1="{ly}" x2="{lx + 15}" y2="{ly}" stroke="{c}" stroke-width="2"/>')
    leg1.append(f'<text x="{lx + 20}" y="{ly + 4}" font-size="9" fill="#0f172a">N = {r["size"]}</text>')

# Legend items Panel 2
leg2 = f"""
<rect x="{W - 190}" y="{TOP2 + 10}" width="10" height="10" fill="#3b82f6" opacity="0.8"/>
<text x="{W - 175}" y="{TOP2 + 19}" font-size="10" fill="#0f172a">1% Settling (ps)</text>
<line x1="{W - 190}" y1="{TOP2 + 35}" x2="{W - 175}" y2="{TOP2 + 35}" stroke="#ea580c" stroke-width="2"/>
<circle cx="{W - 182}" cy="{TOP2 + 35}" r="3" fill="#ea580c"/>
<text x="{W - 170}" y="{TOP2 + 38}" font-size="10" fill="#ea580c">f_max (GHz)</text>
"""

svg_content = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" font-family="-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif">
  <rect width="{W}" height="{H}" fill="#ffffff"/>
  <text x="{W/2:.0f}" y="30" text-anchor="middle" font-size="18" font-weight="bold" fill="#0f172a">Distributed RC Crossbar Transient Dynamics (0018)</text>
  <text x="{W/2:.0f}" y="50" text-anchor="middle" font-size="12" fill="#64748b">R_wire = 1.0 Ohm, C_seg = 1.5 fF, Step = 0.25 V at t = 0.1 ns</text>

  {p1_grid}
  {p2_grid}

  {' '.join(leg1)}
  {leg2}
  {' '.join(elements)}
</svg>
"""

_OUT.write_text(svg_content, "utf-8")
print(f"Generated transient settling SVG: {_OUT}")
