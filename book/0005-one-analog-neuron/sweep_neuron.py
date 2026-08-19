"""A2 — DC sweep of the 0005 neuron: find the linear region and the clip points.

Reuses the non-ideal op-amp model from `sim_neuron_nonideal.py` (finite gain +
input offset + explicit 0..5 V rail clamp). With the non-inverting input held
at a 2.5 V virtual reference and x2 fixed at 2.5 V, sweeping x1 traces a line

    Vout = VREF - W1*(x1 - VREF)

that is linear while inside the rails and clips at 0 V / 5 V outside them.

The script prints a table, asserts the linear region slope/clip position, and
writes an annotated SVG plot to `diagrams/sweep.svg`.
"""

import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sim_neuron_nonideal import VHI, VLO, W1, clamp, run_linear

VREF = 2.5
X2 = VREF           # x2 contribution is 0 (x2 == reference)
XMIN, XMAX, N = -4.0, 9.0, 40


def sweep():
    xs = np.linspace(XMIN, XMAX, N)
    outs_lin = []
    outs_chip = []
    for x1 in xs:
        out, _ = run_linear(float(x1), X2, VREF)
        outs_lin.append(out)
        outs_chip.append(clamp(out))
    return xs, np.array(outs_lin), np.array(outs_chip)


def make_svg(xs, outs_lin, outs_chip, path):
    # map x -> px (x in XMIN..XMAX), out -> py (out in -1..6)
    X0, X1, Y0, Y1 = 150.0, 860.0, 60.0, 500.0
    oxmin, oxmax = XMIN, XMAX
    oymin, oymax = -1.0, 6.0

    def px(x): return X0 + (x - oxmin) / (oxmax - oxmin) * (X1 - X0)
    def py(v): return Y1 - (v - oymin) / (oymax - oymin) * (Y1 - Y0)

    def poly(xs_, ys_):
        return " ".join(f"{px(x):.1f},{py(y):.1f}" for x, y in zip(xs_, ys_))

    parts = []
    # rails
    parts.append(f'<line x1="{X0}" y1="{py(0)}" x2="{X1}" y2="{py(0)}" stroke="#ffd0d0" stroke-width="1.5"/>')
    parts.append(f'<line x1="{X0}" y1="{py(5)}" x2="{X1}" y2="{py(5)}" stroke="#ffd0d0" stroke-width="1.5"/>')
    parts.append(f'<text x="{X1}" y="{py(0)+3}" text-anchor="end" fill="#c0392b" font-size="12">rail 0 V</text>')
    parts.append(f'<text x="{X1}" y="{py(5)+16}" text-anchor="end" fill="#c0392b" font-size="12">rail 5 V</text>')
    # linear ideal line (unclamped) as dashed
    idl = [VREF - W1 * (x - VREF) for x in xs]
    parts.append(f'<polyline points="{poly(xs, idl)}" fill="none" stroke="#1a5276" stroke-dasharray="5,4" stroke-width="2"/>')
    # chip (clamped) solid
    parts.append(f'<polyline points="{poly(xs, outs_chip)}" fill="none" stroke="#1e8449" stroke-width="3"/>')

    axes = [
        f'<line x1="{px(0)}" y1="{Y0}" x2="{px(0)}" y2="{Y1}" stroke="#333" stroke-width="1.5"/>',
        f'<line x1="{X0}" y1="{py(0)}" x2="{X1}" y2="{py(0)}" stroke="#333" stroke-width="1.5"/>',
        f'<text x="{X1}" y="{Y0+16}" text-anchor="end" fill="#333">x1 (V)</text>',
        f'<text x="{X0+8}" y="{Y1-6}" fill="#333">Vout (V)</text>',
    ]
    ticks = []
    for xv in range(-4, 10, 2):
        ticks.append(f'<text x="{px(xv)}" y="{Y0+14}" text-anchor="middle" fill="#666" font-size="11">{xv}</text>')
    for vv in (0, 1, 2, 3, 4, 5):
        ticks.append(f'<text x="{X0-6}" y="{py(vv)+4}" text-anchor="end" fill="#666" font-size="11">{vv}</text>')

    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 960 540" width="960" height="540" font-family="Menlo,Consolas,monospace">
<rect width="960" height="540" fill="#ffffff"/>
<text x="480" y="28" text-anchor="middle" font-size="18" font-weight="bold" fill="#111">Vout vs x1 (x2 = 2.5 V reference)</text>
<text x="480" y="48" text-anchor="middle" font-size="12" fill="#7f8c8d">green solid = chip output (clamped) · blue dashed = ideal linear · pink = rails</text>
{chr(10).join(axes)}
{chr(10).join(ticks)}
{chr(10).join(parts)}
</svg>"""
    with open(path, "w") as fh:
        fh.write(svg)


def main():
    xs, outs_lin, outs_chip = sweep()
    linear_mask = (outs_chip > VLO + 1e-9) & (outs_chip < VHI - 1e-9)

    print(f"Sweep x1 in [{XMIN}, {XMAX}] V, x2 = {X2} V (virtual ref {VREF} V)")
    print("  x1      Vout(lin)  Vout(chip)")
    for x, linear, clipped in zip(xs[::5], outs_lin[::5], outs_chip[::5]):
        print(f"  {x:7.2f}  {linear:8.3f}  {clipped:9.3f}")

    # assertions
    slope = np.polyfit(xs[linear_mask], outs_chip[linear_mask], 1)[0]
    print(f"\nlinear-region slope = {slope:.3f} (expect ~{ -W1:.3f})")
    assert abs(slope - (-W1)) < 0.02, f"slope {slope:.3f} != target {-W1:.3f}"
    assert np.all(outs_chip[middle_region(xs, outs_chip, outs_lin)] <= VHI + 1e-9)
    assert np.all(outs_chip >= VLO - 1e-9)

    # clip positions (first/last x where clipped)
    hi5_x = xs[np.argmax(outs_chip >= VHI - 1e-9)]
    lo0_x = xs[np.argmax(outs_chip <= VLO + 1e-9)]
    print(f"clips at the 5 V rail for x1 <= {hi5_x:.2f} V;  clips at the 0 V rail for x1 >= {lo0_x:.2f} V")
    print(f"linear region approx x1 in ({hi5_x:.2f}, {lo0_x:.2f}) V")

    make_svg(xs, outs_lin, outs_chip, "diagrams/sweep.svg")
    print("wrote diagrams/sweep.svg")


def middle_region(xs, outs_chip, outs_lin):
    return (outs_chip > VLO + 1e-9) & (outs_chip < VHI - 1e-9)


if __name__ == "__main__":
    main()
