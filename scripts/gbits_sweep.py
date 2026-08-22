"""M1 — sweep programmable-conductance resolution vs effective-weight error.

A signed weight ``w in [-1, 1]`` is stored on two conductance cells
``(G+, G-)`` that resolve to ``w_eff = G+ - G-``. Each cell has ``2**g_bits``
programmable levels over ``[gmin, gmax]``, so the weight resolution is finite.
This script sweeps ``g_bits`` and reports the maximum absolute error between the
ideal weight and the effective quantized weight:

  err(g_bits) = max_w |w - w_eff(w, g_bits)|

with the analytic bound for a differential cell (grid spacing ``d``,
``w_eff`` error <= ``d / 2``, normalized by the conductance span):

  bound(g_bits) = 1 / (2 * (2**g_bits - 1))

The result is the weight-side accuracy-vs-cost curve: more conductance levels
halve the worst-case effective-weight error. This is a *weight quantization*
study at the crossbar level (no energy / GPU claim).
"""

import numpy as np

from analog_llm.crossbar import map_differential

GMIN, GMAX = 0.05, 1.0
GBITS = [2, 3, 4, 5, 6, 8, 10, 12, 14]


def effective_weight_sweep(weights: np.ndarray) -> list[dict]:
    span = GMAX - GMIN
    rows = []
    for bits in GBITS:
        _, _, w_eff = map_differential(weights, bits, gmin=GMIN, gmax=GMAX)
        # the tile normalizes by the conductance span (see tile.forward), so the
        # gmin DC offset (w=1 -> G+ - G- = gmax-gmin) is absorbed; measure the
        # remaining *quantization* error in normalized units.
        err = float(np.max(np.abs(weights - w_eff / span)))
        bound = 1.0 / (2 * (2 ** bits - 1))
        rows.append({
            "g_bits": bits, "levels": 2 ** bits,
            "err": err, "bound": bound,
        })
    return rows


def make_svg(rows: list, path: str) -> None:
    X0, X1, Y0, Y1 = 150.0, 870.0, 70.0, 500.0
    levels = [r["levels"] for r in rows]
    lo, hi = min(levels), max(levels)

    def px(x): return X0 + (np.log10(x) - np.log10(lo)) / (np.log10(hi) - np.log10(lo)) * (X1 - X0)
    def py(y): return Y1 - (np.log10(y) - np.log10(5e-4)) / \
        (np.log10(1.0) - np.log10(5e-4)) * (Y1 - Y0)

    meas = " ".join(f"{px(r['levels']):.1f},{py(max(r['err'], 5e-4)):.1f}" for r in rows)
    theo = " ".join(f"{px(r['levels']):.1f},{py(max(r['bound'], 5e-4)):.1f}" for r in rows)
    ticks = [f'<text x="{px(level)}" y="{Y0 + 16}" text-anchor="middle" font-size="11" fill="#666">{level}</text>'
             for level in levels]
    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 960 540" width="960" height="540" font-family="Menlo,Consolas,monospace">
<rect width="960" height="540" fill="#ffffff"/>
<text x="480" y="30" text-anchor="middle" font-size="18" font-weight="bold" fill="#111">Effective-weight error vs conductance resolution</text>
<text x="480" y="52" text-anchor="middle" font-size="12" fill="#7f8c8d">max |w - w_eff| over [-1,1] vs number of conductance levels 2^g_bits (log-log)</text>
<line x1="{X0}" y1="{Y0}" x2="{X1}" y2="{Y0}" stroke="#333" stroke-width="1.5"/>
<line x1="{X0}" y1="{Y0}" x2="{X0}" y2="{Y1}" stroke="#333" stroke-width="1.5"/>
{chr(10).join(ticks)}
<polyline points="{theo}" fill="none" stroke="#7f8c8d" stroke-width="2" stroke-dasharray="5 5"/>
<polyline points="{meas}" fill="none" stroke="#1a5276" stroke-width="3"/>
<rect x="150" y="330" width="12" height="12" fill="#1a5276"/><text x="168" y="341" font-size="12" fill="#333">measured max |w - w_eff|</text>
<rect x="150" y="356" width="12" height="12" fill="#7f8c8d"/><text x="168" y="367" font-size="12" fill="#333">analytic bound 1 / (2 (2^g_bits - 1))</text>
</svg>"""
    with open(path, "w") as fh:
        fh.write(svg)


def main() -> None:
    rng = np.random.default_rng(0)
    dense = np.linspace(-1.0, 1.0, 1001)
    rand = rng.uniform(-1.0, 1.0, 2000)
    weights = np.concatenate([dense, rand])

    rows = effective_weight_sweep(weights)

    print("=" * 60)
    print("M1 — g_bits vs effective-weight error")
    print("=" * 60)
    print(f"{'g_bits':<7}{'levels':<8}{'max |err|':>12}{'bound':>12}")
    for r in rows:
        print(f"{r['g_bits']:<7}{r['levels']:<8}{r['err']:>12.5f}{r['bound']:>12.5f}")

    errs = [r["err"] for r in rows]
    assert errs[-1] < errs[0], "error must fall as g_bits rises"
    for r in rows:
        assert r["err"] <= r["bound"] + 1e-12, "error must respect the analytic bound"
    assert rows[-1]["err"] < 5e-3, "high g_bits should give small weight error"

    make_svg(rows, "scripts/gbits.svg")
    print("\nwrote scripts/gbits.svg")


if __name__ == "__main__":
    main()
