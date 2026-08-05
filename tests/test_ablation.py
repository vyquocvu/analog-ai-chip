import numpy as np

from analog_llm import Accelerator, CrossbarTile, TinyGPT, TinyGPTConfig
from analog_llm.report import max_abs_logit_error, token_agreement

IDEAL = {"g_bits": 16, "dac_bits": 16, "adc_bits": 16, "vout_max": 8.0,
         "adc_noise_std": 0.0, "adc_gain": 1.0, "adc_offset": 0.0}
BUDGET = {"g_bits": 4, "dac_bits": 6, "adc_bits": 6, "vout_max": 4.0,
          "adc_noise_std": 0.06, "adc_gain": 1.10, "adc_offset": 0.10}
FACTORS = ["g_bits", "dac_bits", "adc_bits", "adc_noise_std",
           "adc_gain", "adc_offset", "vout_max"]


def _tile_factory(params, seed=0):
    def make():
        return CrossbarTile(24, 24, rng=np.random.default_rng(seed), **params)
    return make


def _err(params, model, prompt, seed=0):
    float_tokens = model.generate(prompt, max_new=2, greedy=True)
    float_l = model.forward_logits(float_tokens)
    acc = Accelerator(_tile_factory(params, seed), 24, 24, 8)
    tokens = model.generate(prompt, max_new=2, greedy=True, accelerator=acc)
    logits = model.forward_logits(tokens, accelerator=acc)
    return (token_agreement(float_tokens, tokens),
            max_abs_logit_error(float_l, logits))


def test_ideal_is_better_than_budget() -> None:
    cfg = TinyGPTConfig(vocab_size=64, n_embd=16, n_layer=1, n_head=2,
                        block_size=6, seed=0)
    model = TinyGPT(cfg)
    prompt = np.array([1, 2, 3])
    ideal_agr, ideal_err = _err(IDEAL, model, prompt)
    budget_agr, budget_err = _err(BUDGET, model, prompt)
    assert ideal_err <= budget_err
    assert ideal_agr >= budget_agr


def test_leave_one_out_residuals_are_nonnegative_finite() -> None:
    cfg = TinyGPTConfig(vocab_size=64, n_embd=16, n_layer=1, n_head=2,
                        block_size=6, seed=0)
    model = TinyGPT(cfg)
    prompt = np.array([1, 2, 3])
    _, budget_err = _err(BUDGET, model, prompt)
    for f in FACTORS:
        p = dict(BUDGET)
        p[f] = IDEAL[f]
        _, resid = _err(p, model, prompt)
        assert np.isfinite(resid) and resid >= 0.0, f
        # idealizing a non-ideality (bits/noise/gain/offset) alone must not
        # worsen error; clipping is excluded because vout_max also trades
        # against ADC resolution
        if f != "vout_max":
            assert resid <= budget_err + 1e-9, f
