"""Generate Chapter 0023 Scheduler Scaling plot SVG.

Stdlib-only and deterministic: reads
``verification/circuit/results/scheduler-0023-extract.json`` and renders

  panel 1: Parallel execution cycles vs on-chip physical tile capacity (16 .. 1024).
  panel 2: Total latency for 100-token inference (ms) comparing Weight-Stationary vs Temporal Reuse.

Run:  python book/0023-scheduler/diagrams/make_plots.py
"""

from __future__ import annotations

import json
import math
from pathlib import Path

_OUT = Path(__file__).with_name("scheduler_scaling.svg")
_EXTRACT = (
    Path(__file__).resolve().parents[3]
    / "verification"
    / "circuit"
    / "results"
    / "scheduler-0023-extract.json"
)

W, H = 960, 560
M_LEFT, M_RIGHT, M_TOP, M_BOT = 70, 50, 90, 60
PANEL_W = 390
PANEL_H = 370
P1_X = M_LEFT
P2_X = M_LEFT + PANEL_W + 60

d = json.loads(_EXTRACT.read_text("utf-8"))

sweeps = d["capacity_sweeps"]


# Panel 1 coordinates: X = log2(16) .. log2(1024) [4 .. 10], Y = 0 .. 60 (Cycles)
def px1(tc: int) -> float:
    log_val = math.log2(tc)  # 4 .. 10
    return P1_X + ((log_val - 4.0) / 6.0) * PANEL_W


def py1(cycles: float) -> float:
    return M_TOP + PANEL_H - (cycles / 60.0) * PANEL_H


# Panel 2 coordinates: X = log2(16) .. log2(1024) [4 .. 10], Y = log10(Latency ms) [0 .. 3] (1 ms to 1000 ms)
def px2(tc: int) -> float:
    log_val = math.log2(tc)
    return P2_X + ((log_val - 4.0) / 6.0) * PANEL_W


def py2(lat_ms: float) -> float:
    log_lat = math.log10(max(lat_ms, 0.1))  # -1 to 3
    # map -1 .. 3 to height
    return M_TOP + PANEL_H - ((log_lat + 1.0) / 4.0) * PANEL_H


elements = []

# --- Panel 1: Cycles vs Capacity ---
temp_cycles_pts = []
for row in sweeps:
    tc = row["tile_count"]
    cyc = row["temporal_cycles"]
    x = px1(tc)
    y = py1(cyc)
    temp_cycles_pts.append(f"{x:.1f},{y:.1f}")
    elements.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="4" fill="#3b82f6"/>')
    elements.append(
        f'<text x="{x:.1f}" y="{y - 8:.1f}" text-anchor="middle" font-size="9" font-weight="bold" fill="#2563eb">{cyc}</text>'
    )

elements.append(
    f'<polyline points="{" ".join(temp_cycles_pts)}" fill="none" stroke="#3b82f6" stroke-width="2"/>'
)

# Panel 1 X-ticks (16, 32, 64, 128, 256, 512, 1024)
for tc in [row["tile_count"] for row in sweeps]:
    x = px1(tc)
    elements.append(
        f'<text x="{x:.1f}" y="{M_TOP + PANEL_H + 18:.1f}" text-anchor="middle" font-size="9" fill="#64748b">{tc}</text>'
    )

# Panel 1 Y-ticks
for c in [0, 10, 20, 30, 40, 50, 60]:
    y = py1(c)
    elements.append(
        f'<text x="{P1_X - 8:.1f}" y="{y + 4:.1f}" text-anchor="end" font-size="10" fill="#64748b">{c}</text>'
    )

# --- Panel 2: 100-Token Latency (ms) on Log-Y ---
temp_lat_pts = []
stat_lat_pts = []

for row in sweeps:
    tc = row["tile_count"]
    lat_temp_ms = row["temporal_latency_100tok_us"] / 1000.0
    lat_stat_ms = row["stationary_latency_100tok_us"] / 1000.0

    x = px2(tc)
    y_temp = py2(lat_temp_ms)
    y_stat = py2(lat_stat_ms)

    temp_lat_pts.append(f"{x:.1f},{y_temp:.1f}")
    stat_lat_pts.append(f"{x:.1f},{y_stat:.1f}")

    elements.append(f'<circle cx="{x:.1f}" cy="{y_temp:.1f}" r="4" fill="#ef4444"/>')
    elements.append(f'<circle cx="{x:.1f}" cy="{y_stat:.1f}" r="4" fill="#10b981"/>')

elements.append(
    f'<polyline points="{" ".join(temp_lat_pts)}" fill="none" stroke="#ef4444" stroke-width="2"/>'
)
elements.append(
    f'<polyline points="{" ".join(stat_lat_pts)}" fill="none" stroke="#10b981" stroke-width="2"/>'
)

# Panel 2 X-ticks
for tc in [row["tile_count"] for row in sweeps]:
    x = px2(tc)
    elements.append(
        f'<text x="{x:.1f}" y="{M_TOP + PANEL_H + 18:.1f}" text-anchor="middle" font-size="9" fill="#64748b">{tc}</text>'
    )

# Panel 2 Y-ticks (0.1ms, 1ms, 10ms, 100ms, 1000ms)
for lat_val, lbl in [
    (0.1, "0.1ms"),
    (1.0, "1ms"),
    (10.0, "10ms"),
    (100.0, "100ms"),
    (1000.0, "1s"),
]:
    y = py2(lat_val)
    elements.append(
        f'<line x1="{P2_X}" y1="{y:.1f}" x2="{P2_X + PANEL_W}" y2="{y:.1f}" stroke="#e2e8f0" stroke-dasharray="4"/>'
    )
    elements.append(
        f'<text x="{P2_X - 8:.1f}" y="{y + 4:.1f}" text-anchor="end" font-size="10" fill="#64748b">{lbl}</text>'
    )

# Panel 2 Legend
leg2_y = M_TOP + 15
elements.append(
    f'<line x1="{P2_X + 20}" y1="{leg2_y + 6}" x2="{P2_X + 45}" y2="{leg2_y + 6}" stroke="#ef4444" stroke-width="2"/>'
)
elements.append(
    f'<text x="{P2_X + 52}" y="{leg2_y + 10}" font-size="10" fill="#1e293b">Temporal Multiplexing</text>'
)
elements.append(
    f'<line x1="{P2_X + 20}" y1="{leg2_y + 26}" x2="{P2_X + 45}" y2="{leg2_y + 26}" stroke="#10b981" stroke-width="2"/>'
)
elements.append(
    f'<text x="{P2_X + 52}" y="{leg2_y + 30}" font-size="10" fill="#1e293b">Weight-Stationary (Resident)</text>'
)


# Helper grids
def make_grid(x_off: float, title: str, x_label: str, y_label: str) -> str:
    block = f"""
    <text x="{x_off + PANEL_W / 2:.0f}" y="{M_TOP - 18}" text-anchor="middle" font-size="13" font-weight="bold" fill="#0f172a">{title}</text>
    <rect x="{x_off}" y="{M_TOP}" width="{PANEL_W}" height="{PANEL_H}" fill="#f8fafc" stroke="#334155" stroke-width="1.5"/>
    <text x="{x_off + PANEL_W / 2:.0f}" y="{M_TOP + PANEL_H + 36}" text-anchor="middle" font-size="10" fill="#64748b">{x_label}</text>
    <text x="{x_off - 35}" y="{M_TOP + PANEL_H / 2}" text-anchor="middle" transform="rotate(-90 {x_off - 35} {M_TOP + PANEL_H / 2})" font-size="10" fill="#64748b">{y_label}</text>
    """
    return "\n".join(line.strip() for line in block.splitlines() if line.strip())


g1 = make_grid(
    P1_X,
    "Panel 1: MVM Cycles vs Tile Capacity",
    "Physical Tile Count N_tiles (log scale)",
    "Parallel MVM Cycles per Layer",
)
g2 = make_grid(
    P2_X,
    "Panel 2: 100-Token Latency Comparison",
    "Physical Tile Count N_tiles (log scale)",
    "Total Inference Latency (log scale)",
)

svg_content = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" font-family="-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif">
  <rect width="{W}" height="{H}" fill="#ffffff"/>
  <text x="{W / 2:.0f}" y="32" text-anchor="middle" font-size="18" font-weight="bold" fill="#0f172a">Scheduler Capacity &amp; Latency Scaling (0023)</text>
  <text x="{W / 2:.0f}" y="52" text-anchor="middle" font-size="12" fill="#64748b">Sensitivity study: t_prog = 10 μs and t_mvm = 20 ns are assumed</text>

  {g1}
  {g2}

  {" ".join(elements)}
</svg>
"""

_OUT.write_text(svg_content, "utf-8")
print(f"Generated scheduler scaling SVG: {_OUT}")
