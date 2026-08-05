import numpy as np

from analog_llm import Accelerator, CrossbarTile, TinyGPT, TinyGPTConfig


def _acc(tile_rows, tile_cols, tile_count):
    def factory():
        return CrossbarTile(tile_rows, tile_cols, g_bits=14, dac_bits=16,
                            adc_bits=16, vout_max=64.0)
    return Accelerator(factory, tile_rows, tile_cols, tile_count)


def _full_macs(model, out, acc):
    acc.reset_ledger()
    model.forward_logits(np.asarray(out, dtype=np.int64), accelerator=acc)
    return acc.macs


def test_per_token_macs_grow_with_context() -> None:
    model = TinyGPT(TinyGPTConfig(vocab_size=64, n_embd=16, n_layer=1, n_head=2,
                                  block_size=10, seed=0))
    acc = _acc(8, 8, 4)
    macs = [_full_macs(model, (np.arange(i) % 10 + 1), acc) for i in range(1, 7)]
    assert all(macs[i + 1] > macs[i] for i in range(len(macs) - 1))


def test_kv_single_position_no_more_than_full_forward() -> None:
    model = TinyGPT(TinyGPTConfig(vocab_size=64, n_embd=16, n_layer=1, n_head=2,
                                  block_size=10, seed=0))
    acc = _acc(8, 8, 4)
    full = _full_macs(model, np.array([1, 2, 3]), acc)
    acc.reset_ledger()
    model.forward_logits(np.array([7]), accelerator=acc)
    single = acc.macs
    assert single <= full
    assert single > 0
