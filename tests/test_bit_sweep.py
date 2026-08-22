import numpy as np

from analog_llm import TinyGPT, TinyGPTConfig
from analog_llm.report import max_abs_logit_error, token_agreement


def test_accuracy_improves_with_more_conductance_bits() -> None:
    cfg = TinyGPTConfig(vocab_size=64, n_embd=16, n_layer=1, n_head=2, block_size=6, seed=0)
    model = TinyGPT(cfg)
    prompt = np.array([1, 2, 3])

    float_tokens = model.generate(prompt, max_new=2, greedy=True)
    float_l = model.forward_logits(float_tokens)

    from analog_llm import Accelerator, CrossbarTile

    def run(g_bits):
        acc = Accelerator(lambda: CrossbarTile(32, 32, g_bits=g_bits, dac_bits=14,
                                               adc_bits=14, vout_max=8.0), 32, 32, 16)
        t = model.generate(prompt, max_new=2, greedy=True, accelerator=acc)
        logits = model.forward_logits(t, accelerator=acc)
        return token_agreement(float_tokens, t), max_abs_logit_error(float_l, logits)

    lo = run(2)
    hi = run(10)
    assert hi[1] < lo[1], "higher g_bits should lower logit error"
    assert hi[0] >= lo[0], "higher g_bits should not hurt token agreement"
