"""B2 — per-non-ideality ablation for the analog LLM accelerator.

Ablates each simulator non-ideality independently (leave-one-out) and reports
each one's contribution to the max absolute logit error, so a designer can see
which effect dominates a budget-constrained build.

Non-idealities modelled (see ``analog_llm/tile.py`` and ``PRODUCT_SPEC.md``):

  - ``g_bits``        programmable-conductance resolution (weight side)
  - ``dac_bits``      input DAC resolution (activation side)
  - ``adc_bits``      output ADC resolution (activation side)
  - ``adc_noise_std`` additive Gaussian noise at the ADC
  - ``adc_gain``      static gain error on the analog output path
  - ``adc_offset``    static offset error on the analog output path
  - ``vout_max``      output clipping / saturation at the ADC

Method
------
``IDEAL`` deactivates every non-ideality (high resolution, no noise, unity
gain/offset, no clip). ``BUDGET`` is the budget-constrained build with all
non-idealities on. For each factor we keep every other factor at its BUDGET
value but set only THIS factor to its IDEAL value (leave-one-out), and measure
the residual logit error:

  contribution(f) = error(BUDGET) - error(BUDGET with f idealized)

A larger contribution means fixing that factor alone recovers the most
accuracy. Shares are normalized to 100%. Because the non-idealities interact,
one-at-a-time (LOO) contributions overlap, so shares are an attribution of each
factor's standalone effect rather than a strict partition of the total error.

No GPU / energy / raw-speed claim is made: this is an accuracy-only study.
"""

import numpy as np

from analog_llm import Accelerator, CrossbarTile, TinyGPT, TinyGPTConfig
from analog_llm.report import max_abs_logit_error, token_agreement

IDEAL = {
    "g_bits": 16, "dac_bits": 16, "adc_bits": 16, "vout_max": 8.0,
    "adc_noise_std": 0.0, "adc_gain": 1.0, "adc_offset": 0.0,
}

BUDGET = {
    "g_bits": 4, "dac_bits": 6, "adc_bits": 6, "vout_max": 4.0,
    "adc_noise_std": 0.06, "adc_gain": 1.10, "adc_offset": 0.10,
}

FACTORS = ["g_bits", "dac_bits", "adc_bits", "adc_noise_std",
           "adc_gain", "adc_offset", "vout_max"]

FACTOR_LABELS = {
    "g_bits": "weight resolution (g_bits)",
    "dac_bits": "input DAC bits",
    "adc_bits": "output ADC bits",
    "adc_noise_std": "ADC noise",
    "adc_gain": "converter gain error",
    "adc_offset": "converter offset error",
    "vout_max": "output clipping",
}


def _tile_factory(params: dict[str, float], seed: int):
    def make() -> CrossbarTile:
        return CrossbarTile(48, 48, rng=np.random.default_rng(seed), **params)

    return make


def metrics(params: dict[str, float], cfg, prompt, seq, seed: int):
    """Token agreement + max logit error for a given tile parameter set."""
    model = TinyGPT(cfg)
    float_tokens = model.generate(prompt, max_new=seq, greedy=True)
    float_l = model.forward_logits(float_tokens)

    acc = Accelerator(_tile_factory(params, seed), 48, 48, 16)
    analog_tokens = model.generate(prompt, max_new=seq, greedy=True, accelerator=acc)
    analog_l = model.forward_logits(analog_tokens, accelerator=acc)

    return {
        "agreement": token_agreement(float_tokens, analog_tokens),
        "logit_err": max_abs_logit_error(float_l, analog_l),
    }


def run_ablation(cfg, prompt, seq, seed: int = 0):
    ideal = metrics(IDEAL, cfg, prompt, seq, seed)
    budget = metrics(BUDGET, cfg, prompt, seq, seed)

    resid = {}
    for f in FACTORS:
        p = dict(BUDGET)
        p[f] = IDEAL[f]
        resid[f] = metrics(p, cfg, prompt, seq, seed)["logit_err"]

    contrib = {f: budget["logit_err"] - resid[f] for f in FACTORS}
    total_contrib = sum(max(c, 0.0) for c in contrib.values())
    shares = {f: (max(c, 0.0) / total_contrib * 100.0 if total_contrib > 0 else 0.0)
              for f, c in contrib.items()}
    return {"ideal": ideal, "budget": budget, "residual": resid,
            "contribution": contrib, "total_contrib": total_contrib,
            "shares": shares}


def make_ablation_svg(shares: dict[str, float], path: str) -> None:
    X0, X1 = 340.0, 900.0
    Y0, Y1, row_h = 80.0, 70.0, 42.0
    order = sorted(shares, key=lambda f: -shares[f])
    max_share = max(shares.values()) if shares else 1.0

    bars = []
    labels = []
    for i, f in enumerate(order):
        y = Y0 + i * row_h
        w = shares[f] / max_share * (X1 - X0)
        bars.append(
            f'<rect x="{X0}" y="{y}" width="{w:.1f}" height="{row_h - 14}" '
            f'fill="#1a5276" rx="3"/>'
        )
        labels.append(
            f'<text x="{X0 - 10}" y="{y + (row_h - 14) / 2 + 4}" text-anchor="end" '
            f'fill="#333" font-size="13">{FACTOR_LABELS[f]}</text>'
        )
        labels.append(
            f'<text x="{X0 + w + 8}" y="{y + (row_h - 14) / 2 + 4}" fill="#111" '
            f'font-size="13">{shares[f]:.1f}%</text>'
        )
    bars.append(f'<line x1="{X0}" y1="{Y1}" x2="{X1}" y2="{Y1}" stroke="#333" stroke-width="1.5"/>')

    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 960 {Y0 + row_h * len(order) + 60}" width="960" height="{Y0 + row_h * len(order) + 60}" font-family="Menlo,Consolas,monospace">
<rect width="960" height="{Y0 + row_h * len(order) + 60}" fill="#ffffff"/>
<text x="480" y="30" text-anchor="middle" font-size="18" font-weight="bold" fill="#111">Per-non-ideality contribution to logit error (leave-one-out)</text>
<text x="480" y="52" text-anchor="middle" font-size="12" fill="#7f8c8d">normalized share of the budget-config error; bar length scaled to the largest share</text>
{chr(10).join(bars)}
{chr(10).join(labels)}
</svg>"""
    with open(path, "w") as fh:
        fh.write(svg)


def main():
    cfg = TinyGPTConfig(vocab_size=128, n_embd=32, n_layer=2, n_head=4, block_size=8, seed=0)
    prompt = np.array([3, 9, 14, 22])
    seq = 3

    r = run_ablation(cfg, prompt, seq)

    print("=" * 68)
    print("B2 — per-non-ideality ablation (leave-one-out)")
    print("=" * 68)
    print(f"ideal   (all non-idealities off): logit_err={r['ideal']['logit_err']:.4f} "
          f"agreement={r['ideal']['agreement']:.3f}")
    print(f"budget  (all non-idealities on ): logit_err={r['budget']['logit_err']:.4f} "
          f"agreement={r['budget']['agreement']:.3f}")
    print("-" * 68)
    print(f"{'factor':<26}{'budget err':>12}{'resid (LOO)':>13}{'contrib':>10}{'share':>8}")
    for f in sorted(FACTORS, key=lambda f: -r["shares"][f]):
        print(f"{FACTOR_LABELS[f]:<26}{r['budget']['logit_err']:>12.4f}"
              f"{r['residual'][f]:>13.4f}{r['contribution'][f]:>10.4f}{r['shares'][f]:>7.1f}%")
    print("-" * 68)
    print(f"sum of standalone contributions          : {r['total_contrib']:.4f}")
    print(f"budget error (ideal-to-budget gap)       : "
          f"{r['budget']['logit_err'] - r['ideal']['logit_err']:.4f}")
    print("note: one-at-a-time contributions overlap when non-idealities interact,")
    print("      so the sum of shares is >100%; share is the error recovered by")
    print("      fixing ONLY that factor (others stay at budget).")

    # guardrails: leave-one-out residual must not exceed the budget error
    for f in FACTORS:
        assert r["residual"][f] <= r["budget"]["logit_err"] + 1e-9, (
            f"idealizing {f} must not increase logit error"
        )
        assert r["residual"][f] >= -1e-9, "error is non-negative"

    make_ablation_svg(r["shares"], "scripts/ablation.svg")
    print("\nwrote scripts/ablation.svg")


if __name__ == "__main__":
    main()
