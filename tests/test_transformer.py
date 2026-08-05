import numpy as np
import pytest

from analog_llm.accelerator import Accelerator
from analog_llm.tile import CrossbarTile
from analog_llm.transformer import Metrics, TinyGPT, TinyGPTConfig


def _make(cfg: TinyGPTConfig = None) -> TinyGPT:
    return TinyGPT(cfg or TinyGPTConfig())


def _acc(tile_rows=64, tile_cols=64, tile_count=1, vout_max=8.0) -> Accelerator:
    def factory() -> CrossbarTile:
        return CrossbarTile(
            tile_rows, tile_cols, g_bits=12, dac_bits=16, adc_bits=16, vout_max=vout_max
        )
    return Accelerator(factory, tile_rows, tile_cols, tile_count)


def test_float_forward_shape() -> None:
    model = _make()
    tokens = np.array([1, 2, 3, 4])
    logits = model.forward_logits(tokens)
    assert logits.shape == (4, model.cfg.vocab_size)


def test_analog_forward_close_to_float() -> None:
    model = _make(TinyGPTConfig(n_embd=32, n_layer=2, n_head=4, block_size=8))
    tokens = np.array([1, 2, 3])
    acc = _acc(tile_rows=64, tile_cols=64, tile_count=1)
    float_l = model.forward_logits(tokens)
    analog_l = model.forward_logits(tokens, accelerator=acc)
    assert analog_l.shape == float_l.shape
    np.testing.assert_allclose(analog_l, float_l, atol=0.4)


def test_generate_extends_prompt() -> None:
    model = _make()
    prompt = np.array([5, 6, 7])
    out = model.generate(prompt, max_new=4, greedy=True)
    assert out.shape[0] == 7
    assert np.all(out[:3] == prompt)


def test_generate_sampling_requires_rng() -> None:
    model = _make()
    with pytest.raises(ValueError, match="rng required"):
        model.generate(np.array([1]), max_new=1, greedy=False)


def test_too_long_sequence_rejected() -> None:
    model = _make(TinyGPTConfig(block_size=4))
    with pytest.raises(ValueError, match="sequence length"):
        model.forward_logits(np.arange(5))


def test_metrics_accumulate() -> None:
    m = Metrics()
    acc = _acc()
    model = _make()
    model.forward_logits(np.array([1, 2, 3]), accelerator=acc)
    m.update(acc)
    acc.reset_ledger()
    model.forward_logits(np.array([2, 3, 4]), accelerator=acc)
    m.update(acc)
    assert m.macs > 0 and m.cycles > 0
