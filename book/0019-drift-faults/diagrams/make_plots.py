"""Generate Chapter 0019 3-panel plot SVG for Drift, Stuck Faults & Non-Linearity.

Stdlib-only and deterministic: reads
``verification/circuit/results/drift-faults-0019-extract.json`` and renders

  panel 1: Temporal conductance drift G(t) (uS) over 7 decades of time (1s .. 1yr).
  panel 2: MVM output error (%) vs stuck fault density (0.1% .. 10%).
  panel 3: I-V curve (uA) vs Read Voltage (V) showing non-linear cubic distortion.

Run:  python book/0019-drift-faults/diagrams/make_plots.py
"""

from __future__ import annotations

import json
from pathlib import Path

_OUT = Path(__file__).with_name("drift_and_fault_effects.svg")
_EXTRACT = Path(__file__).resolve().parents[3] / "verification" / "circuit" / "results" / "drift-faults-0019-extract.json"

W, H = 960, 680
M = 80
PANEL_W = 240
PANEL_H = 480
TOP = 110

d = json.loads(_EXTRACT.read_text("utf-8"))

drift_data = d["drift_trajectories_16states"]
fault_data = d["fault_parameters"]["fault_rate_sweeps"]
iv_data = d["non_linear_iv"]["iv_curves"]

# Panel 1 coordinates: X = 80 .. 320 (log10(t) from 0 to 7.5), Y = TOP+PANEL_H .. TOP (G from 0 to 110 uS)
def px1(log_t: float) -> float:
    return M + (log_t / 7.5) * PANEL_W

def py1(g_us: float) -> float:
    return TOP + PANEL_H - (g_us / 110.0) * PANEL_H

# Panel 2 coordinates: X = 390 .. 630 (p_fault from 0 to 10%), Y = TOP+PANEL_H .. TOP (Error from 0 to 50%)
X2_OFFSET = M + PANEL_W + 70
def px2(p_pct: float) -> float:
    return X2_OFFSET + (p_pct / 10.0) * PANEL_W

def py2(err_pct: float) -> float:
    return TOP + PANEL_H - (err_pct / 50.0) * PANEL_H

# Panel 3 coordinates: X = 700 .. 940 (V from -0.25 to +0.25 V), Y = TOP+PANEL_H .. TOP (I from -30 to +30 uA)
X3_OFFSET = X2_OFFSET + PANEL_W + 70
def px3(v_val: float) -> float:
    return X3_OFFSET + ((v_val + 0.25) / 0.50) * PANEL_W

def py3(i_ua: float) -> float:
    return TOP + PANEL_H - ((i_ua + 30.0) / 60.0) * PANEL_H

elements = []

# --- Panel 1: Drift over Time ---
time_logs = [0.0, 1.0, 1.778, 3.556, 4.937, 6.0, 7.498]
states_to_plot = [0, 5, 10, 15]
drift_colors = ["#64748b", "#10b981", "#3b82f6", "#ef4444"]

for idx, color in zip(states_to_plot, drift_colors):
    row = drift_data[idx]
    conds = row["conductance_over_time_uS"]
    pts = []
    for log_t, g in zip(time_logs, conds):
        x = px1(log_t)
        y = py1(g)
        pts.append(f"{x:.1f},{y:.1f}")
        elements.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="3" fill="{color}"/>')
    elements.append(f'<polyline points="{" ".join(pts)}" fill="none" stroke="{color}" stroke-width="2"/>')
    # Label at end
    last_x, last_y = px1(time_logs[-1]), py1(conds[-1])
    elements.append(f'<text x="{last_x + 4:.1f}" y="{last_y + 3:.1f}" font-size="9" fill="{color}">S{idx}</text>')

# Panel 1 X-labels
t_labels = [("1s", 0.0), ("1m", 1.778), ("1h", 3.556), ("1d", 4.937), ("1yr", 7.498)]
for lbl, lt in t_labels:
    x = px1(lt)
    elements.append(f'<text x="{x:.1f}" y="{TOP + PANEL_H + 16:.1f}" text-anchor="middle" font-size="9" fill="#475569">{lbl}</text>')

# --- Panel 2: Stuck Faults Error ---
f_pts = []
for row in fault_data:
    p_pct = row["total_fault_prob"] * 100.0
    err = row["mvm_rel_error_pct"]
    x = px2(p_pct)
    y = py2(err)
    f_pts.append(f"{x:.1f},{y:.1f}")
    elements.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="4" fill="#e11d48"/>')

elements.append(f'<polyline points="{" ".join(f_pts)}" fill="none" stroke="#e11d48" stroke-width="2"/>')

for p_val in [0, 2, 4, 6, 8, 10]:
    x = px2(p_val)
    elements.append(f'<text x="{x:.1f}" y="{TOP + PANEL_H + 16:.1f}" text-anchor="middle" font-size="9" fill="#475569">{p_val}%</text>')

# --- Panel 3: I-V Non-Linearity ---
lin_pts = []
nonlin_pts = []
for row in iv_data:
    v = row["voltage_v"]
    i_lin = row["ideal_ohmic_uA"]
    i_act = row["actual_current_uA"]
    x = px3(v)
    y_lin = py3(i_lin)
    y_act = py3(i_act)
    lin_pts.append(f"{x:.1f},{y_lin:.1f}")
    nonlin_pts.append(f"{x:.1f},{y_act:.1f}")

elements.append(f'<polyline points="{" ".join(lin_pts)}" fill="none" stroke="#94a3b8" stroke-width="1.5" stroke-dasharray="3"/>')
elements.append(f'<polyline points="{" ".join(nonlin_pts)}" fill="none" stroke="#9333ea" stroke-width="2"/>')

for v_val in [-0.25, -0.125, 0.0, 0.125, 0.25]:
    x = px3(v_val)
    elements.append(f'<text x="{x:.1f}" y="{TOP + PANEL_H + 16:.1f}" text-anchor="middle" font-size="9" fill="#475569">{v_val:+.2f}V</text>')

# Grid helper
def make_grid(x_off: float, title: str, x_label: str, y_label: str) -> str:
    return f"""
    <text x="{x_off + PANEL_W/2:.0f}" y="{TOP - 18}" text-anchor="middle" font-size="13" font-weight="bold" fill="#0f172a">{title}</text>
    <rect x="{x_off}" y="{TOP}" width="{PANEL_W}" height="{PANEL_H}" fill="#f8fafc" stroke="#334155" stroke-width="1.5"/>
    <line x1="{x_off}" y1="{TOP + PANEL_H/2}" x2="{x_off + PANEL_W}" y2="{TOP + PANEL_H/2}" stroke="#e2e8f0" stroke-dasharray="4"/>
    <text x="{x_off + PANEL_W/2:.0f}" y="{TOP + PANEL_H + 34}" text-anchor="middle" font-size="10" fill="#64748b">{x_label}</text>
    <text x="{x_off - 12}" y="{TOP + PANEL_H/2}" text-anchor="middle" transform="rotate(-90 {x_off - 12} {TOP + PANEL_H/2})" font-size="10" fill="#64748b">{y_label}</text>
    """

g1 = make_grid(M, "Panel 1: Conductance Drift G(t)", "Retention Time (log scale)", "Conductance (uS)")
g2 = make_grid(X2_OFFSET, "Panel 2: Stuck Fault Error", "Total Defect Density (%)", "MVM Error (%)")
g3 = make_grid(X3_OFFSET, "Panel 3: I-V Non-Linearity", "Read Voltage (V)", "Cell Current (uA)")

svg_content = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" font-family="-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif">
  <rect width="{W}" height="{H}" fill="#ffffff"/>
  <text x="{W/2:.0f}" y="32" text-anchor="middle" font-size="18" font-weight="bold" fill="#0f172a">NVM Drift, Stuck Faults &amp; Non-Linear Conduction (0019)</text>
  <text x="{W/2:.0f}" y="52" text-anchor="middle" font-size="12" fill="#64748b">Power-law relaxation ν ∈ [0.02, 0.06], defect rates p_fault ∈ [0.1%, 10%], cubic distortion β = 1.0 V⁻²</text>

  {g1}
  {g2}
  {g3}

  {' '.join(elements)}
</svg>
"""

_OUT.write_text(svg_content, "utf-8")
print(f"Generated drift, faults & non-linearity SVG: {_OUT}")
