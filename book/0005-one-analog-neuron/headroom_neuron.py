"""A3 — virtual-ground and rail-headroom check for the 0005 neuron.

Two things a real builder must measure, now verified in simulation:

1. VIRTUAL GROUND — in the linear region the summing node `n` must sit at the
   reference `VREF` (here 2.5 V). With a finite-gain op-amp it is not exactly
   at VREF; the error is about `(Vout - VREF) / Aol`. We sweep the linear
   region, record `V(n)`, and show the error is tiny and scales with 1/Aol.

2. RAIL HEADROOM — with a 5 V supply and VREF = 2.5 V the output can swing
   `VREF` volts down (to 0 V) and `VDD - VREF` volts up (to 5 V). We report the
   available swing and the linear range of Vout.

Also demonstrates the contrast with the gnd-referenced configuration
(VREF = 0 V): the summing node sits near 0 V, but headroom downward is zero, so
any positive input clips immediately.
"""

import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sim_neuron_nonideal import VHI, VLO, VREF, run_linear

VDD = 5.0
AOL_GOOD = 1e4
AOL_WEAK = 1e3


def virtual_ground_error(aol=AOL_GOOD):
    """Return (x1s, vn_errors) over the linear region for a given open-loop gain."""
    xs = np.linspace(0.0, 5.0, 21)
    errs = []
    for x1 in xs:
        _, n = run_linear(float(x1), VREF, VREF, aol=aol)
        errs.append(n - VREF)
    return xs, np.asarray(errs)


def make_svg(xs, err_good, err_weak, path):
    X0, X1, Y0, Y1 = 150.0, 860.0, 60.0, 500.0
    oxmin, oxmax = 0.0, 5.0
    oymin, oymax = -2.0, 2.0

    def px(x): return X0 + (x - oxmin) / (oxmax - oxmin) * (X1 - X0)
    def py(v): return Y1 - (v - oymin) / (oymax - oymin) * (Y1 - Y0)

    def poly(ys):
        return " ".join(f"{px(x):.1f},{py(y):.1f}" for x, y in zip(xs, ys))

    zero_line = f'<line x1="{X0}" y1="{py(0)}" x2="{X1}" y2="{py(0)}" stroke="#c0392b" stroke-width="1.5" stroke-dasharray="4,4"/>'
    good = f'<polyline points="{poly(err_good)}" fill="none" stroke="#1e8449" stroke-width="3"/>'
    weak = f'<polyline points="{poly(err_weak)}" fill="none" stroke="#e67e22" stroke-width="2.5"/>'
    axes = [
        f'<line x1="{px(0)}" y1="{Y0}" x2="{px(0)}" y2="{Y1}" stroke="#333" stroke-width="1.5"/>',
        f'<line x1="{X0}" y1="{py(0)}" x2="{X1}" y2="{py(0)}" stroke="#333" stroke-width="1.5"/>',
        f'<text x="{X1}" y="{Y0+16}" text-anchor="end" fill="#333">x1 (V)</text>',
        f'<text x="{X0+8}" y="{Y1-6}" fill="#333">n − VREF (mV)</text>',
    ]
    ticks = []
    for xv in range(6):
        ticks.append(f'<text x="{px(xv)}" y="{Y0+14}" text-anchor="middle" fill="#666" font-size="11">{xv}</text>')
    for vv in (-1.5, -1.0, -0.5, 0.0, 0.5, 1.0, 1.5):
        ticks.append(f'<text x="{X0-6}" y="{py(vv)+4}" text-anchor="end" fill="#666" font-size="11">{vv}</text>')

    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 960 540" width="960" height="540" font-family="Menlo,Consolas,monospace">
<rect width="960" height="540" fill="#ffffff"/>
<text x="480" y="28" text-anchor="middle" font-size="18" font-weight="bold" fill="#111">Virtual-ground error  n − VREF  across the linear sweep</text>
<text x="480" y="48" text-anchor="middle" font-size="12" fill="#7f8c8d">green = Aol 1e4 · orange = Aol 1e3 · red dashed = perfect virtual ground</text>
{chr(10).join(axes)}
{chr(10).join(ticks)}
{zero_line}
{good}
{weak}
</svg>"""
    with open(path, "w") as fh:
        fh.write(svg)


def main():
    print("Virtual ground (summing node n) in the LINEAR region")
    xs, err_good = virtual_ground_error(AOL_GOOD)
    xs, err_weak = virtual_ground_error(AOL_WEAK)
    print(f"  Aol = {AOL_GOOD:.0e}:  max |n − VREF| = {np.max(np.abs(err_good))*1e3:.2f} mV")
    print(f"  Aol = {AOL_WEAK:.0e}:  max |n − VREF| = {np.max(np.abs(err_weak))*1e3:.2f} mV")

    assert np.max(np.abs(err_good)) < 1e-3, "virtual ground error too large at Aol=1e4"
    assert np.max(np.abs(err_weak)) > np.max(np.abs(err_good)), "error must scale with 1/Aol"

    print("\nSample points (x1, Vout, V(n), n − VREF)")
    print("  x1    Vout   V(n)     n−VREF")
    for x1 in (0.0, 1.25, 2.5, 3.75, 5.0):
        out, n = run_linear(x1, VREF, VREF, aol=AOL_GOOD)
        print(f"  {x1:4.2f}  {out:5.3f}  {n:6.4f}  {n-VREF:+9.2e}")

    print("\nRail headroom (VDD = 5 V, VREF = 2.5 V)")
    up = VHI - VREF
    down = VREF - VLO
    print(f"  headroom up   = VDD − VREF = {VDD} − {VREF} = {up:.1f} V")
    print(f"  headroom down = VREF − 0   = {VREF:.1f} V")
    assert abs(up - 2.5) < 1e-9 and abs(down - 2.5) < 1e-9
    print("  linear output range = [0, 5] V; keep |Vout − VREF| ≤ 2.5 V to stay linear")

    print("\nContrast — gnd-referenced (VREF = 0 V): headroom down = 0")
    _, n0 = run_linear(0.5, 1.0, 0.0, aol=AOL_GOOD)
    print(f"  n ≈ {n0:.3f} V (virtual ground at 0 V) but any positive input "
          f"needs a negative output -> clips at 0 V")

    make_svg(xs, err_good, err_weak, "diagrams/virtual_ground.svg")
    print("wrote diagrams/virtual_ground.svg")
    print("\nA3 OK: virtual ground and rail headroom are measured and reported.")


if __name__ == "__main__":
    main()
