"""A5 — chapter 0006: one neuron scaled to a layer of N neurons.

A layer of N neurons, each with M inputs, is just the matrix-vector product
`y = W @ x` (W is N×M). Here we build that layer for N = 10, 100, 1000 (with
M = 16 inputs), compute it two ways — float reference and the analog tile
accelerator from `analog_llm` — and report the scaling ledger:

  cells              = N * M                    (unsigned conductances)
  differential cells = 2 * N * M                (signed weights, see 0002)
  MACs per forward   = N * M
  physical tiles     = ceil(N/T) * ceil(M/T),   T = tile size

The key teaching point: adding neurons is LINEAR in cells and MACs (for fixed
inputs). No "constant-time" claim is made — the multi-tile ledger (cycles,
rewrites) makes that explicit (see chapter 0004 / complexity).
"""

import numpy as np

from analog_llm import Accelerator, CrossbarTile

M = 16             # inputs per neuron
NEURONS = [10, 100, 1000]
TILE = 64          # physical tile rows == cols
SEED = 0


def build_layer(n_neurons, rng):
    w = rng.normal(0.0, 1.0 / np.sqrt(M), (n_neurons, M))
    x = rng.normal(0.0, 1.0, M)
    return w, x


def tiled_forward(acc, w, x):
    return acc.mvm(w, x)


def make_tile():
    return CrossbarTile(TILE, TILE, g_bits=14, dac_bits=16, adc_bits=16, vout_max=32.0)


def summary(n_neurons, rng):
    w, x = build_layer(n_neurons, rng)
    ref = w @ x
    acc = Accelerator(make_tile, TILE, TILE, 64)  # plenty of tiles -> no rewrite
    y = tiled_forward(acc, w, x)
    err = float(np.max(np.abs(y - ref)))
    tiles_rows = -(-n_neurons // TILE)
    tiles_cols = -(-M // TILE)
    tiles = tiles_rows * tiles_cols
    return {
        "n": n_neurons,
        "inputs": M,
        "cells": n_neurons * M,
        "cells_signed": 2 * n_neurons * M,
        "macs": n_neurons * M,
        "tiles": tiles,
        "cycles": acc.tile_cycles,
        "max_abs_err": err,
    }


def main():
    rng = np.random.default_rng(SEED)
    rows = [summary(n, rng) for n in NEURONS]

    print("Layer scaling (M = 16 inputs per neuron, signed differential weights)")
    print("  N     cells  cells(signed)   MACs  tiles  cycles     max|err|")
    for r in rows:
        print(f"  {r['n']:5d}  {r['cells']:7d}  {r['cells_signed']:10d}  "
              f"{r['macs']:7d}  {r['tiles']:5d}  {r['cycles']:6d}  {r['max_abs_err']:.2e}")

    for r in rows:
        exp_tiles = (-(-r["n"] // TILE)) * (-(-M // TILE))
        assert r["tiles"] == exp_tiles, f"N={r['n']} tiles {r['tiles']} != {exp_tiles}"
        assert r["max_abs_err"] < 1e-1, f"N={r['n']} err too large: {r['max_abs_err']}"
        assert r["cells"] == r["n"] * M
        assert r["cells_signed"] == 2 * r["n"] * M
        assert r["macs"] == r["n"] * M

    print("\nGrowth is linear in N: cells and MACs scale as N*M.")
    print("\nWrite growth plot ...")
    _write_svg(rows)


def _write_svg(rows):
    X0, X1, Y0, Y1 = 150.0, 860.0, 70.0, 500.0
    ns = np.array([r["n"] for r in rows], dtype=float)
    cells = np.array([r["cells"] for r in rows], dtype=float)
    macs = np.array([r["macs"] for r in rows], dtype=float)
    lo, hi = 1e1, 1e5

    def px(x): return X0 + (np.log10(x) - np.log10(lo)) / (np.log10(hi) - np.log10(lo)) * (X1 - X0)
    def py(y): return Y1 - (np.log10(y) - np.log10(lo)) / (np.log10(hi) - np.log10(lo)) * (Y1 - Y0)

    def line(xs, ys, color, wdt, dash=None):
        pts = " ".join(f"{px(x):.1f},{py(y):.1f}" for x, y in zip(xs, ys))
        d = f' stroke-dasharray="{dash}"' if dash else ""
        return f'<polyline points="{pts}" fill="none" stroke="{color}" stroke-width="{wdt}"{d}/>'

    parts = [
        line(ns, cells, "#1a5276", 3),
        line(ns, macs, "#1e8449", 3, "5,4"),
        f'<text x="{px(1000)+6}" y="{py(16000)-6}" fill="#1a5276" font-size="13">cells = N·16</text>',
        f'<text x="{px(1000)+6}" y="{py(16000)+8}" fill="#1e8449" font-size="13">MACs = N·16</text>',
    ]
    axes = [
        f'<line x1="{X0}" y1="{Y0}" x2="{X1}" y2="{Y0}" stroke="#333" stroke-width="1.5"/>',
        f'<line x1="{X0}" y1="{Y0}" x2="{X0}" y2="{Y1}" stroke="#333" stroke-width="1.5"/>',
        f'<text x="{X1}" y="{Y1+26}" text-anchor="end" fill="#333">neurons N (log)</text>',
        f'<text x="{X0-10}" y="{Y0+14}" fill="#333">cells / MACs (log)</text>',
    ]
    ticks = []
    for n in (10, 100, 1000):
        ticks.append(f'<text x="{px(n)}" y="{Y0+16}" text-anchor="middle" fill="#666" font-size="11">{n}</text>')
    for v in (160, 1600, 16000):
        ticks.append(f'<text x="{X0-8}" y="{py(v)+4}" text-anchor="end" fill="#666" font-size="11">{int(v)}</text>')

    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 960 540" width="960" height="540" font-family="Menlo,Consolas,monospace">
<rect width="960" height="540" fill="#ffffff"/>
<text x="480" y="30" text-anchor="middle" font-size="18" font-weight="bold" fill="#111">Layer growth: cells and MACs vs number of neurons (M = 16)</text>
<text x="480" y="52" text-anchor="middle" font-size="12" fill="#7f8c8d">blue = conductance cells · green dashed = MACs · both linear in N (log axes)</text>
{chr(10).join(axes)}
{chr(10).join(ticks)}
{chr(10).join(parts)}
</svg>"""
    with open("diagrams/growth.svg", "w") as fh:
        fh.write(svg)
    print("wrote diagrams/growth.svg")


if __name__ == "__main__":
    main()
