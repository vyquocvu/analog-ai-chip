"""Generate the 0010 ADC transfer plot SVG from the committed extract.

Stdlib-only and deterministic: reads
``verification/circuit/results/adc-sar-v1-extract.json`` and renders (a) the
SAR code staircase over the input envelope and (b) the differential-domain
reconstruction error against the LSB quantization bound.

Run:  python book/0010-adc-sar/diagrams/make_transfer.py
"""

from __future__ import annotations

import json
from pathlib import Path

_OUT = Path(__file__).with_name("transfer.svg")
_EXTRACT = Path(__file__).resolve().parents[3] / "verification" / "circuit" / "results" / "adc-sar-v1-extract.json"

W, H = 960, 460
M = 90
PLOT_W, PLOT_H = W - 2 * M, 150
TOP1, TOP2 = 70, 270  # top of each of the two stacked plots

d = json.loads(_EXTRACT.read_text("utf-8"))
rows = d["transfer"]
bits, vref, lsb = int(d["bits"]), d["vref_v"], d["lsb_v"]
n_code = 2**bits


def px(v_in: float) -> float:
    return M + (v_in / vref) * PLOT_W


def py1(code: float) -> float:
    return TOP1 + PLOT_H - (code / n_code) * PLOT_H


def py2(err: float) -> float:
    return TOP2 + PLOT_H - (err / (1.5 * lsb)) * PLOT_H


# panel 1: code staircase from the SPICE transfer (code is constant between samples)
stair = []
for i, r in enumerate(rows):
    x = px(r["v_in_v"])
    y = py1(r["code_spice"])
    stair.append((x, y))
    if i < len(rows) - 1:
        stair.append((px(rows[i + 1]["v_in_v"]), y))
pts = " ".join(f"{x:.1f},{y:.1f}" for x, y in stair)

# panel 2: differential-domain reconstruction error per sample
err_pts = " ".join(
    f"{px(r['v_in_v']):.1f},{py2(abs(2.0 * (r['v_in_v'] - vref / 2.0) - ((r['code_spice'] + 0.5) * lsb * 2.0 - vref))):.1f}"
    for r in rows
)


def axis(x0: float, x1: float, y0: float, y1: float, title: str) -> str:
    return f"""
<text x="{W / 2:.0f}" y="{y0 - 8}" text-anchor="middle" font-size="13" fill="#111">{title}</text>
<line x1="{x0}" y1="{y0}" x2="{x1}" y2="{y0}" stroke="#333" stroke-width="1.5"/>
<line x1="{x0}" y1="{y0}" x2="{x0}" y2="{y1}" stroke="#333" stroke-width="1.5"/>"""


svg = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" font-family="Menlo,Consolas,monospace">
<rect width="{W}" height="{H}" fill="#ffffff"/>
<text x="480" y="28" text-anchor="middle" font-size="18" font-weight="bold" fill="#111">SAR ADC transfer (0010)</text>
<text x="480" y="48" text-anchor="middle" font-size="12" fill="#7f8c8d">129-sample SPICE transfer sweep · 4-bit · VREF = 2.5 V · LSB = 0.15625 V</text>

{axis(M, W - M, TOP1, TOP1 + PLOT_H, "code = SAR(Vin) — SPICE == hand ideal_code at every sample (worst deviation 0 codes)")}
<text x="{W - M}" y="{TOP1 + PLOT_H + 18}" text-anchor="end" fill="#333" font-size="12">Vin (V)</text>
<text x="{M - 6}" y="{TOP1 + 10}" text-anchor="end" fill="#333" font-size="12">code</text>
<polyline points="{pts}" fill="none" stroke="#1e8449" stroke-width="3"/>
<text x="{M + 8}" y="{TOP1 + 18}" fill="#1e8449" font-size="12">SPICE SAR code (green)</text>
<text x="{M + 8}" y="{TOP1 + 34}" fill="#7f8c8d" font-size="11">hand: code = floor(Vin/LSB) clipped to [0, 15]</text>

{axis(M, W - M, TOP2, TOP2 + PLOT_H, "differential-domain reconstruction error |Vdiff − Vdiff_hat| vs LSB bound")}
<text x="{W - M}" y="{TOP2 + PLOT_H + 18}" text-anchor="end" fill="#333" font-size="12">Vin (V)</text>
<text x="{M - 6}" y="{TOP2 + 10}" text-anchor="end" fill="#333" font-size="12">|err| (V)</text>
<line x1="{M}" y1="{py2(lsb):.1f}" x2="{W - M}" y2="{py2(lsb):.1f}" stroke="#c0392b" stroke-dasharray="6,4" stroke-width="2"/>
<text x="{M + 8}" y="{py2(lsb) - 6}" fill="#c0392b" font-size="12">quantization bound LSB = 0.15625 V</text>
<polyline points="{err_pts}" fill="none" stroke="#1a5276" stroke-width="2.5"/>
<text x="{M + 8}" y="{TOP2 + PLOT_H - 8}" fill="#1a5276" font-size="12">max error = LSB (front gain 1/2 doubles the unipolar LSB/2 bound)</text>
</svg>
"""
_OUT.write_text(svg, "utf-8")
print(f"wrote {_OUT}")
