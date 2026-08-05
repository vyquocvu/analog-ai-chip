"""B1 — accuracy-vs-cost sweep for the analog LLM accelerator.

Runs the tiny transformer (float baseline) through the analog tile accelerator
at different resolutions and measures two quality metrics per setting:

  - token agreement (fraction of generated tokens that match the float model)
  - max absolute logit error on a fixed forward pass

Two one-dimensional sweeps are run, matching ROADMAP M4:
  1. weight resolution  `g_bits`
  2. converter resolution `adc_bits` (DAC kept high)

"Cost" is reported as the number of programmable conductance levels (2^g_bits)
and as the ADC codes (2^adc_bits), and plotted on log axes. The result is the
accuracy-vs-cost curve: more bits cost more, degrade error, and (beyond a
point) buy little. No GPU/energy claim is made.
"""

import numpy as np

from analog_llm import Accelerator, CrossbarTile, TinyGPT, TinyGPTConfig
from analog_llm.report import max_abs_logit_error, token_agreement


def build_tile(**kw):
    return lambda: CrossbarTile(64, 64, **kw)


def run(prompt, seq, g_bits, adc_bits, cfg):
    model = TinyGPT(cfg)
    float_tokens = model.generate(prompt, max_new=seq, greedy=True)
    acc = Accelerator(build_tile(g_bits=g_bits, dac_bits=16, adc_bits=adc_bits, vout_max=16.0),
                      64, 64, 64)
    analog_tokens = model.generate(prompt, max_new=seq, greedy=True, accelerator=acc)
    float_l = model.forward_logits(float_tokens)
    analog_l = model.forward_logits(analog_tokens, accelerator=acc)
    return {
        "agreement": token_agreement(float_tokens, analog_tokens),
        "logit_err": max_abs_logit_error(float_l, analog_l),
    }


def sweep(prompt, seq, cfg, g_bits_list, adc_bits_list):
    rows = []
    for g in g_bits_list:
        r = run(prompt, seq, g, max(adc_bits_list), cfg)
        rows.append({"g_bits": g, "levels": 2 ** g,
                     "agreement": r["agreement"], "logit_err": r["logit_err"]})
    rows2 = []
    for a in adc_bits_list:
        r = run(prompt, seq, max(g_bits_list), a, cfg)
        rows2.append({"adc_bits": a, "codes": 2 ** a,
                      "agreement": r["agreement"], "logit_err": r["logit_err"]})
    return rows, rows2


def make_svg(xs, ys, path, xlab, title):
    X0, X1, Y0, Y1 = 150.0, 860.0, 70.0, 500.0
    lo, hi = min(xs), max(xs)

    def px(x): return X0 + (np.log10(x) - np.log10(lo)) / (np.log10(hi) - np.log10(lo)) * (X1 - X0)
    def py(y): return Y1 - (y - 0.0) / (np.max(ys) + 1e-9) * (Y1 - Y0)

    pts = " ".join(f"{px(x):.1f},{py(y):.1f}" for x, y in zip(xs, ys))
    axes = [
        f'<line x1="{X0}" y1="{Y0}" x2="{X1}" y2="{Y0}" stroke="#333" stroke-width="1.5"/>',
        f'<line x1="{X0}" y1="{Y0}" x2="{X0}" y2="{Y1}" stroke="#333" stroke-width="1.5"/>',
        f'<text x="{X1}" y="{Y1+26}" text-anchor="end" fill="#333">{xlab} (log)</text>',
        f'<text x="{X0-10}" y="{Y0+14}" fill="#333">max logit error</text>',
    ]
    ticks = [f'<text x="{px(x)}" y="{Y0+16}" text-anchor="middle" fill="#666" font-size="11">{x}</text>' for x in xs]
    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 960 540" width="960" height="540" font-family="Menlo,Consolas,monospace">
<rect width="960" height="540" fill="#ffffff"/>
<text x="480" y="30" text-anchor="middle" font-size="18" font-weight="bold" fill="#111">{title}</text>
<text x="480" y="52" text-anchor="middle" font-size="12" fill="#7f8c8d">max |logit error| vs {xlab}</text>
{chr(10).join(axes)}
{chr(10).join(ticks)}
<polyline points="{pts}" fill="none" stroke="#1a5276" stroke-width="3"/>
</svg>"""
    with open(path, "w") as fh:
        fh.write(svg)


def main():
    cfg = TinyGPTConfig(vocab_size=128, n_embd=32, n_layer=2, n_head=4, block_size=8, seed=0)
    prompt = np.array([3, 9, 14, 22])
    seq = 3
    g_list = [2, 4, 6, 8, 10, 12, 14]
    a_list = [2, 3, 4, 5, 6, 7, 8, 10, 12]

    rows, rows2 = sweep(prompt, seq, cfg, g_list, a_list)

    print("Sweep over conductance bits g_bits (adc_bits held high)")
    print("  g_bits  levels  agreement  logit_err")
    for r in rows:
        print(f"   {r['g_bits']:4d}  {r['levels']:6d}   {r['agreement']:.2f}    {r['logit_err']:.3f}")
    print("\nSweep over converter bits adc_bits (g_bits held high)")
    print("  adc_bits  codes  agreement  logit_err")
    for r in rows2:
        print(f"    {r['adc_bits']:4d}  {r['codes']:6d}   {r['agreement']:.2f}    {r['logit_err']:.3f}")

    # guardrails: error should generally decrease with more bits
    e1 = [r["logit_err"] for r in rows]
    e2 = [r["logit_err"] for r in rows2]
    assert min(e1) <= 0.2, "high g_bits should reach low logit error"
    assert e1[0] > e1[-1], "more conductance bits should reduce error"
    assert e2[0] > e2[-1], "more converter bits should reduce error"

    make_svg([r["levels"] for r in rows], e1, "scripts/bit_sweep_g.svg",
             "conductance levels (2^g_bits)", "Accuracy vs conductance resolution")
    make_svg([r["codes"] for r in rows2], e2, "scripts/bit_sweep_adc.svg",
             "ADC codes (2^adc_bits)", "Accuracy vs converter resolution")
    print("\nwrote scripts/bit_sweep_g.svg and scripts/bit_sweep_adc.svg")


if __name__ == "__main__":
    main()
