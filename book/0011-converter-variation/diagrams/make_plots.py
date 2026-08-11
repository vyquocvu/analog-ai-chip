"""Generate the 0011 variation/calibration plots SVG from the committed extract.

Stdlib-only and deterministic. Panel 1: the 64-sample SPICE mismatch transfer
envelope around the ideal line (band = min..max over samples per code). Panel 2:
worst |error| per code after each calibration candidate (raw vs two-point vs
lookup table) using the chapter's ``calibration`` module.

Run:  python book/0011-converter-variation/diagrams/make_plots.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np
from calibration import lookup_table_calibrate, two_point_calibrate

_OUT = Path(__file__).with_name("mismatch_transfer.svg")
_EXTRACT = Path(__file__).resolve().parents[3] / "verification" / "circuit" / "results" / "converter-variation-0011-extract.json"

W, H = 960, 460
M = 90
PLOT_W, PLOT_H = W - 2 * M, 150
TOP1, TOP2 = 70, 270

d = json.loads(_EXTRACT.read_text("utf-8"))
bits, vref = int(d["bits"]), d["vref_v"]
t = np.asarray(d["transfers_spice"], dtype=float)  # (64, 16)
codes = np.arange(2**bits)
ideal = codes * (vref / (2**bits))
lsb = vref / (2**bits)

# per-code envelope over the 64 samples
lo = t.min(axis=0)
hi = t.max(axis=0)


def px(code: float) -> float:
    return M + (code / (2**bits - 1)) * PLOT_W


def py(v: float, top: int = TOP1) -> float:
    return top + PLOT_H - (v / vref) * PLOT_H


# envelope band
band = []
for i in range(2**bits):
    band.append((px(i), py(lo[i])))
for i in range(2**bits - 1, -1, -1):
    band.append((px(i), py(hi[i])))
band_pts = " ".join(f"{x:.1f},{y:.1f}" for x, y in band)

ideal_line = " ".join(f"{px(i):.1f},{py(ideal[i]):.1f}" for i in range(2**bits))

# calibration residuals, worst over samples per code
raw = np.abs(t - ideal[None, :]).max(axis=0)
two = np.abs(two_point_calibrate(t, bits=bits, vref=vref) - ideal[None, :]).max(axis=0)
lut = np.abs(lookup_table_calibrate(t, bits=bits, vref=vref) - ideal[None, :]).max(axis=0)
y_scale = max(1.1 * 2.0 * lsb, float(raw.max()))

raw_pts = " ".join(f"{px(i):.1f},{TOP2 + PLOT_H - (raw[i] / y_scale) * PLOT_H:.1f}" for i in range(2**bits))
two_pts = " ".join(f"{px(i):.1f},{TOP2 + PLOT_H - (two[i] / y_scale) * PLOT_H:.1f}" for i in range(2**bits))
lut_pts = " ".join(f"{px(i):.1f},{TOP2 + PLOT_H - (lut[i] / y_scale) * PLOT_H:.1f}" for i in range(2**bits))

# first/last code = endpoints (offset/gain anchored), mid codes show INL
err = " ".join(
    f'{px(i):.0f}:{TOP2 + PLOT_H - (raw[i] / y_scale) * PLOT_H:.1f},'
    for i in range(2**bits)
)


def axis(x0: float, x1: float, y0: float, y1: float, title: str) -> str:
    return f"""
<text x="{W / 2:.0f}" y="{y0 - 8}" text-anchor="middle" font-size="13" fill="#111">{title}</text>
<line x1="{x0}" y1="{y0}" x2="{x1}" y2="{y0}" stroke="#333" stroke-width="1.5"/>
<line x1="{x0}" y1="{y0}" x2="{x0}" y2="{y1}" stroke="#333" stroke-width="1.5"/>"""


svg = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" font-family="Menlo,Consolas,monospace">
<rect width="{W}" height="{H}" fill="#ffffff"/>
<text x="480" y="28" text-anchor="middle" font-size="18" font-weight="bold" fill="#111">Converter mismatch and calibration (0011)</text>
<text x="480" y="48" text-anchor="middle" font-size="12" fill="#7f8c8d">64-sample R-2R mismatch MC · sigma 1% assumed Gaussian · seed 7 · VREF = 2.5 V</text>

{axis(M, W - M, TOP1, TOP1 + PLOT_H, "SPICE mismatch transfer envelope (min..max over 64 samples) vs ideal ladder")}
<text x="{W - M}" y="{TOP1 + PLOT_H + 18}" text-anchor="end" fill="#333" font-size="12">code</text>
<text x="{M - 6}" y="{TOP1 + 10}" text-anchor="end" fill="#333" font-size="12">Vout (V)</text>
<polygon points="{band_pts}" fill="#e8f6f3" stroke="#1e8449" stroke-width="1.5" opacity="0.9"/>
<polyline points="{ideal_line}" fill="none" stroke="#1a5276" stroke-dasharray="6,4" stroke-width="2"/>
<text x="{M + 8}" y="{TOP1 + 18}" fill="#1e8449" font-size="12">64-sample envelope (green band)</text>
<text x="{M + 8}" y="{TOP1 + 34}" fill="#1a5276" font-size="12">ideal Vout = VREF·code/16 (dashed)</text>
<text x="{M + 8}" y="{TOP1 + PLOT_H - 8}" fill="#7f8c8d" font-size="11">offset = 0 (all legs grounded at code 0) · gain error mean {d['gain_error_mean']:.2e} (std {d['gain_error_std']:.2e})</text>

{axis(M, W - M, TOP2, TOP2 + PLOT_H, "worst |error| per code after calibration: raw vs two-point vs lookup table")}
<text x="{W - M}" y="{TOP2 + PLOT_H + 18}" text-anchor="end" fill="#333" font-size="12">code</text>
<text x="{M - 6}" y="{TOP2 + 10}" text-anchor="end" fill="#333" font-size="12">|err| (V)</text>
<line x1="{M}" y1="{TOP2 + PLOT_H - (lsb / y_scale) * PLOT_H:.1f}" x2="{W - M}" y2="{TOP2 + PLOT_H - (lsb / y_scale) * PLOT_H:.1f}" stroke="#c0392b" stroke-dasharray="6,4" stroke-width="2"/>
<text x="{M + 8}" y="{TOP2 + PLOT_H - (lsb / y_scale) * PLOT_H - 6}" fill="#c0392b" font-size="12">LSB = 0.15625 V</text>
<polyline points="{raw_pts}" fill="none" stroke="#c0392b" stroke-width="2.5"/>
<polyline points="{two_pts}" fill="none" stroke="#ca6f1e" stroke-width="2.5"/>
<polyline points="{lut_pts}" fill="none" stroke="#1e8449" stroke-width="2.5"/>
<text x="{M + 8}" y="{TOP2 + PLOT_H - 8}" fill="#c0392b" font-size="12">raw (worst {raw.max():.2e} V)  ·  two-point (worst {two.max():.2e} V, = INL scaled)  ·  LUT (worst {lut.max():.2e} V)</text>
</svg>
"""
_OUT.write_text(svg, "utf-8")
print(f"wrote {_OUT}")
print(f"raw {raw.max():.2e}  two {two.max():.2e}  lut {lut.max():.2e}  y_scale {y_scale:.3f}")
