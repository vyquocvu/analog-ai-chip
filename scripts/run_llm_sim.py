"""Run a tiny LLM through the analog tile accelerator and report results.

Use a generous (high-bit, low-noise) accelerator to establish the error floor,
then a budget-constrained one to show realistic degradation. Deterministic:
all randomness uses fixed seeds.
"""

import numpy as np

from analog_llm import Accelerator, CrossbarTile, Metrics, TinyGPT, TinyGPTConfig
from analog_llm.report import format_report, max_abs_logit_error, token_agreement


def build_acc(tile_rows: int, tile_cols: int, tile_count: int, **tile_kwargs) -> Accelerator:
    def factory() -> CrossbarTile:
        return CrossbarTile(tile_rows, tile_cols, **tile_kwargs)
    return Accelerator(factory, tile_rows, tile_cols, tile_count)


def main() -> None:
    rng = np.random.default_rng(11)
    cfg = TinyGPTConfig(vocab_size=128, n_embd=64, n_layer=2, n_head=4, block_size=16, seed=0)
    model = TinyGPT(cfg)
    prompt = np.array([3, 9, 14, 22, 5])

    # ---- baseline (float) ----
    float_seq = model.generate(prompt, max_new=6, greedy=True, rng=rng)
    float_logits = model.forward_logits(float_seq)

    # ---- analog: high precision -> error floor ----
    acc_hi = build_acc(64, 64, 1, g_bits=14, dac_bits=16, adc_bits=16, vout_max=16.0)
    hi_metrics = Metrics()
    analog_hi = model.generate(prompt, max_new=6, greedy=True, accelerator=acc_hi, rng=rng)
    hi_logits = model.forward_logits(analog_hi, accelerator=acc_hi)
    hi_metrics.update(acc_hi)

    # ---- analog: budget constraints -> realistic degradation ----
    acc_lo = build_acc(
        64, 64, 1, g_bits=6, dac_bits=8, adc_bits=8, vout_max=8.0,
        adc_noise_std=0.01, rng=np.random.default_rng(5),
    )
    lo_metrics = Metrics()
    analog_lo = model.generate(prompt, max_new=6, greedy=True, accelerator=acc_lo, rng=rng)
    lo_logits = model.forward_logits(analog_lo, accelerator=acc_lo)
    lo_metrics.update(acc_lo)

    accs = {
        "token agreement (high-precision)": token_agreement(float_seq, analog_hi),
        "token agreement (budget)": token_agreement(float_seq, analog_lo),
    }
    print(format_report(
        {
            "model": f"TinyGPT {cfg.n_layer}L {cfg.n_embd}D {cfg.n_head}H",
            "vocab": cfg.vocab_size,
            "prompt tokens": prompt.tolist(),
            "generated": float_seq[prompt.size:].tolist(),
        },
        hi_metrics,
        accs,
        tiles_used=1,
    ))
    print("max |logit error| (high-precision):", f"{max_abs_logit_error(float_logits, hi_logits):.3f}")
    print("max |logit error| (budget)        :", f"{max_abs_logit_error(float_logits, lo_logits):.3f}")


if __name__ == "__main__":
    main()
