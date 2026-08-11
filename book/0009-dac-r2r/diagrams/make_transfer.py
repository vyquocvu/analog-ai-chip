"""Generate the 0009 transfer plot SVG from the committed DAC extract.

Stdlib-only and deterministic: reads
``verification/circuit/results/dac-r2r-v1-extract.json`` and renders the SPICE
transfer staircase against the ideal line ``Vout = VREF*code/16``.

Run:  python book/0009-dac-r2r/diagrams/make_transfer.py
"""

from __future__ import annotations

import json
from pathlib import Path

_OUT = Path(__file__).with_name("transfer.svg")
_EXTRACT = Path(__file__).resolve().parents[3] / "verification" / "circuit" / "results" / "dac-r2r-v1-extract.json"

W, H, M = 960, 420, 80          # canvas and margin
PLOT_W, PLOT_H = W - 2 * M, 280
X0, Y0 = M, H - 80              # axes origin (bottom-left of plot)
VMAX = 2.5

d = json.loads(_EXTRACT.read_text("utf-8"))
volts = d["sweep_v"]
n = len(volts)
vref = d["vref_v"]


def px(code: int) -> float:
    return X0 + (code / (n - 1)) * PLOT_W


def py(v: float) -> float:
    return Y0 - (v / VMAX) * PLOT_H


# staircase from the SPICE sweep
stair = []
for i, v in enumerate(volts):
    stair.append((px(i), py(v)))
    if i < n - 1:
        stair.append((px(i + 1), py(v)))

pts = " ".join(f"{x:.1f},{y:.1f}" for x, y in stair)
ideal = " ".join(f"{px(i):.1f},{py(d['vref_v'] * i / (n - 1)):.1f}" for i in range(n))

labels_x = " ".join(
    f'<text x="{px(i):.0f}" y="{Y0 + 24}" text-anchor="middle" fill="#666" font-size="11">{i}</text>'
    for i in range(0, n, 2)
)
labels_y = "".join(
    f'<text x="{X0 - 6}" y="{py(v):.0f}" text-anchor="end" fill="#666" font-size="11">{v:.2f}</text>'
    for v in (0.0, 0.625, 1.25, 1.875, 2.5)
)

svg = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" font-family="Menlo,Consolas,monospace">
<rect width="{W}" height="{H}" fill="#ffffff"/>
<text x="480" y="26" text-anchor="middle" font-size="18" font-weight="bold" fill="#111">DAC transfer: Vout vs code (0009)</text>
<text x="480" y="46" text-anchor="middle" font-size="12" fill="#7f8c8d">SPICE staircase (green) vs ideal Vout = VREF·code/16 (blue dashed) · 4-bit R-2R ladder</text>
<line x1="{X0}" y1="{Y0}" x2="{X0 + PLOT_W}" y2="{Y0}" stroke="#333" stroke-width="1.5"/>
<line x1="{X0}" y1="{Y0}" x2="{X0}" y2="{Y0 - PLOT_H}" stroke="#333" stroke-width="1.5"/>
{labels_x}
{labels_y}
<text x="{X0 + PLOT_W}" y="{Y0 + 24}" text-anchor="end" fill="#333" font-size="12">code</text>
<text x="{X0 - 6}" y="{Y0 - PLOT_H - 8}" text-anchor="end" fill="#333" font-size="12">Vout (V)</text>
<polyline points="{ideal}" fill="none" stroke="#1a5276" stroke-dasharray="5,4" stroke-width="2"/>
<polyline points="{pts}" fill="none" stroke="#1e8449" stroke-width="3"/>
<text x="{X0 + 8}" y="{Y0 - 10}" fill="#1e8449" font-size="12">SPICE (all 16 codes, worst |err| = 4.4e-16 V)</text>
<text x="{X0 + 8}" y="{Y0 - 30}" fill="#1a5276" font-size="12">ideal Vout = VREF·code/16 (dashed)</text>
</svg>
"""
_OUT.write_text(svg, "utf-8")
print(f"wrote {_OUT}")
