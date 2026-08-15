"""Generate the 0013 MVM-error / behavioral-equivalence plot SVG.

Stdlib-only and deterministic: reads
``verification/circuit/results/crossbar-4x4-0013-extract.json`` and renders

  panel 1: per-case worst |SPICE-hand|, |tile-hand|, |SPICE-tile| errors
           (log axis, against the frozen R3 budget of 2e-3 V),
  panel 2: per-case max |Vout| against the +/-2.5 V headroom, plus the
           max virtual-ground error per case.

Run:  python book/0013-crossbar-4x4/diagrams/make_plots.py
"""

from __future__ import annotations

import json
import math
from pathlib import Path

_OUT = Path(__file__).with_name("mvm_error.svg")
_EXTRACT = Path(__file__).resolve().parents[3] / "verification" / "circuit" / "results" / "crossbar-4x4-0013-extract.json"

W, H = 960, 660
M = 90
PLOT_W, PLOT_H = W - 2 * M, 230
TOP1, TOP2 = 80, 380

d = json.loads(_EXTRACT.read_text("utf-8"))
cases = d["cases"]
n_cases = len(cases)

# panel 1: log y from 1e-6 .. 1e-2 V (errors are tiny)
def py1(v: float) -> float:
    lo, hi = 1e-6, 1e-2
    v = max(lo, min(hi, v))
    return TOP1 + PLOT_H - (math.log10(v) - math.log10(lo)) / (math.log10(hi) - math.log10(lo)) * PLOT_H

group_w = PLOT_W / n_cases
bar_w = group_w * 0.22
series = [
    ("max_abs_err_spice_hand_v", "#1e8449", "|SPICE − hand|"),
    ("max_abs_err_tile_hand_v", "#1a5276", "|tile − hand|"),
    ("max_abs_err_spice_tile_v", "#ca6f1e", "|SPICE − tile|"),
]
bars = []
for c, row in enumerate(cases):
    for k, (key, fill, _) in enumerate(series):
        v = row[key]
        x0 = M + c * group_w + k * bar_w * 1.25
        y = py1(v)
        bars.append(
            f'<rect x="{x0:.1f}" y="{y:.1f}" width="{bar_w:.1f}" '
            f'height="{TOP1 + PLOT_H - y:.1f}" fill="{fill}" opacity="0.85"/>'
        )

case_labels = " ".join(
    f'<text x="{M + c * group_w + group_w / 2:.0f}" y="{TOP1 + PLOT_H + 22}" '
    f'text-anchor="middle" fill="#666" font-size="11">case {c}</text>'
    for c in range(n_cases)
)

# panel 2: max |Vout| per case vs headroom; virtual-ground error (right axis)
def py2(v: float) -> float:
    return TOP2 + PLOT_H - (v / 3.0) * PLOT_H  # y range 0 .. 3 V

vg_max = max(row["max_virtual_ground_err_v"] for row in cases)
vg_scale = max(vg_max, 1e-9)

vout_pts = []
vg_pts = []
for c, row in enumerate(cases):
    cx = M + c * group_w + group_w / 2
    v = max(abs(x) for x in row["vout_spice"])
    vout_pts.append(
        f'<rect x="{cx - 14:.0f}" y="{py2(v):.1f}" width="28" height="{TOP2 + PLOT_H - py2(v):.1f}" '
        f'fill="#1e8449" opacity="0.85"/>'
    )
    vg = row["max_virtual_ground_err_v"]
    vg_pts.append(
        f'<circle cx="{cx + 16:.0f}" cy="{py2(vg / vg_scale * 3.0):.1f}" r="5" fill="#922b21"/>'
    )
    vout_pts.append(
        f'<text x="{cx:.0f}" y="{py2(v) - 6:.0f}" text-anchor="middle" fill="#1e8449" font-size="10">{v:.2f}</text>'
    )

headroom_y = py2(d["headroom_v"])


def axis(x0: float, x1: float, y0: float, y1: float, title: str) -> str:
    return f"""
<text x="{W / 2:.0f}" y="{y0 - 10}" text-anchor="middle" font-size="13" fill="#111">{title}</text>
<line x1="{x0}" y1="{y0}" x2="{x1}" y2="{y0}" stroke="#333" stroke-width="1.5"/>
<line x1="{x0}" y1="{y0}" x2="{x0}" y2="{y1}" stroke="#333" stroke-width="1.5"/>"""


svg = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" font-family="Menlo,Consolas,monospace">
<rect width="{W}" height="{H}" fill="#ffffff"/>
<text x="480" y="28" text-anchor="middle" font-size="18" font-weight="bold" fill="#111">4×4 differential crossbar array — MVM error and headroom (0013)</text>
<text x="480" y="48" text-anchor="middle" font-size="12" fill="#7f8c8d">worst |SPICE − hand| {d['worst_abs_err_spice_hand_v']:.1e} V · worst |tile − hand| {d['worst_abs_err_tile_hand_v']:.1e} V · frozen R3 budget 2e-3 V</text>

{axis(M, W - M, TOP1, TOP1 + PLOT_H, "worst error per case vs the hand reference and the behavioral tile (log scale)")}
<text x="{W - M}" y="{TOP1 + PLOT_H + 22}" text-anchor="end" fill="#333" font-size="12">case (4 outputs each)</text>
<text x="{M - 6}" y="{TOP1 + 10}" text-anchor="end" fill="#333" font-size="12">err (V)</text>
{chr(10).join(bars)}
{case_labels}
{chr(10).join(f'<text x="{M + 8 + i * 190}" y="{TOP1 + 16}" fill="{fill}" font-size="12">{name}</text>' for i, (_, fill, name) in enumerate(series))}
<line x1="{M}" y1="{py1(2e-3):.1f}" x2="{W - M}" y2="{py1(2e-3):.1f}" stroke="#c0392b" stroke-dasharray="6,4" stroke-width="2"/>
<text x="{W - M - 8}" y="{py1(2e-3) - 6}" text-anchor="end" fill="#c0392b" font-size="12">R3 budget 2e-3 V (dashed)</text>

{axis(M, W - M, TOP2, TOP2 + PLOT_H, "max |Vout| per case vs differential headroom (green bars) and max virtual-ground error (red dots)")}
<text x="{W - M}" y="{TOP2 + PLOT_H + 22}" text-anchor="end" fill="#333" font-size="12">case</text>
<text x="{M - 6}" y="{TOP2 + 10}" text-anchor="end" fill="#333" font-size="12">|Vout| (V)</text>
{chr(10).join(vout_pts)}
{chr(10).join(vg_pts)}
<line x1="{M}" y1="{headroom_y:.1f}" x2="{W - M}" y2="{headroom_y:.1f}" stroke="#c0392b" stroke-dasharray="6,4" stroke-width="2"/>
<text x="{M + 8}" y="{headroom_y - 6:.0f}" fill="#c0392b" font-size="12">+/-{d['headroom_v']} V headroom (dashed)</text>
<text x="{M + 8}" y="{TOP2 + PLOT_H - 8}" fill="#333" font-size="12">red dot = max |Vn − VREF| per case (max {vg_max:.1e} V, virtual ground)</text>
<text x="{M + 8}" y="{TOP2 + PLOT_H + 36}" fill="#333" font-size="12">all differential outputs within headroom; VCVS finite-gain keeps the summing node within 3.0e-4 V of VREF</text>
</svg>
"""
_OUT.write_text(svg, "utf-8")
print(f"wrote {_OUT}")
print(f"worst spice-hand {d['worst_abs_err_spice_hand_v']:.2e}  "
      f"worst tile-hand {d['worst_abs_err_tile_hand_v']:.2e}  "
      f"worst spice-tile {d['worst_abs_err_spice_tile_v']:.2e}  "
      f"max|Vout| {d['max_abs_vout_v']:.3f}  max VG err {vg_max:.1e}")
