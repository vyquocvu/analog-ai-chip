"""Generate the 0012 MVM / headroom plots SVG from the committed extract.

Stdlib-only and deterministic: reads
``verification/circuit/results/crossbar-2x2-0012-extract.json`` and renders

  panel 1: SPICE vs hand Vout for every case x output (grouped bars),
  panel 2: the four half-stage TIA outputs per case against the 0..5 V
           single rail, highlighting the boundary-case violation (the
           usable per-input envelope finding |u| <= 1.25 V).

Run:  python book/0012-crossbar-2x2/diagrams/make_plots.py
"""

from __future__ import annotations

import json
from pathlib import Path

_OUT = Path(__file__).with_name("mvm_cases.svg")
_EXTRACT = Path(__file__).resolve().parents[3] / "verification" / "circuit" / "results" / "crossbar-2x2-0012-extract.json"

W, H = 960, 640
M = 90
PLOT_W, PLOT_H = W - 2 * M, 220
TOP1, TOP2 = 80, 380

d = json.loads(_EXTRACT.read_text("utf-8"))
cases = d["cases"]
n_cases = len(cases)


def py1(v: float) -> float:
    return TOP1 + PLOT_H - ((v + 3.0) / 6.0) * PLOT_H  # y range -3 .. +3 V


def py2(v: float) -> float:
    return TOP2 + PLOT_H - ((v + 3.0) / 9.5) * PLOT_H  # y range -3 .. 6.5 V


# panel 1: grouped bars, 4 bars per case (out0 spice/hand, out1 spice/hand)
group_w = PLOT_W / n_cases
bar_w = group_w * 0.18
bars = []
for c, row in enumerate(cases):
    for o in range(2):
        for s, name in ((0, "spice"), (1, "hand")):
            v = row["vout_spice"][o] if s == 0 else row["vout_hand"][o]
            x0 = M + c * group_w + o * group_w * 0.5 + s * bar_w
            x1 = x0 + bar_w
            y = py1(v)
            y0 = py1(0.0)
            fill = "#1e8449" if s == 0 else "#1a5276"
            bars.append(
                f'<rect x="{x0:.1f}" y="{min(y, y0):.1f}" width="{bar_w:.1f}" '
                f'height="{abs(y - y0):.1f}" fill="{fill}" opacity="0.85"/>'
            )

case_labels = " ".join(
    f'<text x="{M + c * group_w + group_w / 2:.0f}" y="{TOP1 + PLOT_H + 22}" '
    f'text-anchor="middle" fill="#666" font-size="11">case {c}</text>'
    for c in range(n_cases)
)

# panel 2: half-stage outputs per case (Vp0, Vm0, Vp1, Vm1), rail band 0..5 V
rail_y0, rail_y1 = py2(0.0), py2(5.0)
half_pts = []
half_labels = ("Vp0", "Vm0", "Vp1", "Vm1")
for c, row in enumerate(cases):
    cx = M + c * group_w + group_w / 2
    for k, v in enumerate(row["half_stage_outputs_v"]):
        color = "#922b21" if not (0.0 <= v <= 5.0) else "#1a5276"
        half_pts.append(
            f'<circle cx="{cx:.0f}" cy="{py2(v):.1f}" r="6" fill="{color}"/>'
        )
        half_pts.append(
            f'<text x="{cx:.0f}" y="{py2(v) - 10:.0f}" text-anchor="middle" '
            f'fill="{color}" font-size="10">{half_labels[k]}</text>'
        )
    half_pts.append(
        f'<text x="{cx:.0f}" y="{TOP2 + PLOT_H + 22}" text-anchor="middle" '
        f'fill="#666" font-size="11">case {c}</text>'
    )


def axis(x0: float, x1: float, y0: float, y1: float, title: str) -> str:
    return f"""
<text x="{W / 2:.0f}" y="{y0 - 10}" text-anchor="middle" font-size="13" fill="#111">{title}</text>
<line x1="{x0}" y1="{y0}" x2="{x1}" y2="{y0}" stroke="#333" stroke-width="1.5"/>
<line x1="{x0}" y1="{y0}" x2="{x0}" y2="{y1}" stroke="#333" stroke-width="1.5"/>"""


svg = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" font-family="Menlo,Consolas,monospace">
<rect width="{W}" height="{H}" fill="#ffffff"/>
<text x="480" y="28" text-anchor="middle" font-size="18" font-weight="bold" fill="#111">2×2 differential crossbar array — SPICE MVM and headroom (0012)</text>
<text x="480" y="48" text-anchor="middle" font-size="12" fill="#7f8c8d">worst |SPICE − hand| {d['worst_abs_err_v']:.1e} V over {n_cases} cases x 2 outputs · VREF = {d['vref_v']} V · Rf·Gscale = 1 V per volt per weight</text>

{axis(M, W - M, TOP1, TOP1 + PLOT_H, "Vout per case (SPICE vs hand): Vout_j = Rf·Gscale·(W@u)_j")}
<text x="{W - M}" y="{TOP1 + PLOT_H + 22}" text-anchor="end" fill="#333" font-size="12">case (2 outputs each)</text>
<text x="{M - 6}" y="{TOP1 + 10}" text-anchor="end" fill="#333" font-size="12">Vout (V)</text>
{chr(10).join(bars)}
{case_labels}
<text x="{M + 8}" y="{TOP1 + 18}" fill="#1e8449" font-size="12">SPICE (green)  ·  hand reference (blue)</text>
<line x1="{M}" y1="{py1(d['headroom_v']):.1f}" x2="{W - M}" y2="{py1(d['headroom_v']):.1f}" stroke="#c0392b" stroke-dasharray="6,4" stroke-width="2"/>
<line x1="{M}" y1="{py1(-d['headroom_v']):.1f}" x2="{W - M}" y2="{py1(-d['headroom_v']):.1f}" stroke="#c0392b" stroke-dasharray="6,4" stroke-width="2"/>
<text x="{M + 8}" y="{py1(d['headroom_v']) - 6}" fill="#c0392b" font-size="12">+/-{d['headroom_v']} V headroom (dashed)</text>

{axis(M, W - M, TOP2, TOP2 + PLOT_H, "half-stage TIA outputs per case vs the single 0..5 V rail")}
<text x="{W - M}" y="{TOP2 + PLOT_H + 22}" text-anchor="end" fill="#333" font-size="12">case</text>
<text x="{M - 6}" y="{TOP2 + 10}" text-anchor="end" fill="#333" font-size="12">half-stage V (V)</text>
<rect x="{M}" y="{rail_y0:.1f}" width="{PLOT_W}" height="{rail_y1 - rail_y0:.1f}" fill="#eaf2f8" opacity="0.5"/>
<text x="{W - M - 8}" y="{rail_y0 + 16:.0f}" text-anchor="end" fill="#1a5276" font-size="11">0..5 V single rail (shaded)</text>
{chr(10).join(half_pts)}
<text x="{M + 8}" y="{TOP2 + PLOT_H - 10}" fill="#922b21" font-size="12">red: boundary case G+ half-stage at -2.5 V — below the 0 V rail (finding)</text>
<text x="{M + 8}" y="{TOP2 + PLOT_H + 34}" fill="#333" font-size="12">usable per-input envelope for |w|=1: |u| &lt;= {d['half_stage_rail_envelope_v']:.2f} V = VREF/(Rf·(G0+Gscale))</text>
</svg>
"""
_OUT.write_text(svg, "utf-8")
print(f"wrote {_OUT}")
print(f"worst_err {d['worst_abs_err_v']:.2e}  max|Vout| {d['max_abs_vout_v']:.3f}  "
      f"violations {d['half_stage_rail_violations']}  "
      f"rail envelope {d['half_stage_rail_envelope_v']:.2f} V")
