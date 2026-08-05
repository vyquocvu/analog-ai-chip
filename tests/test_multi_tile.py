import numpy as np

from analog_llm import Accelerator, CrossbarTile


def _factory(tile_rows, tile_cols, seed=0):
    def make():
        return CrossbarTile(tile_rows, tile_cols, g_bits=14, dac_bits=16,
                            adc_bits=16, vout_max=16.0,
                            rng=np.random.default_rng(seed))
    return make


def _scenario(matrix, vector, tile_rows, tile_cols, tile_count, seed=0):
    acc = Accelerator(_factory(tile_rows, tile_cols, seed), tile_rows, tile_cols,
                      tile_count)
    out = acc.mvm(matrix, vector)
    return out, acc


def test_multi_tile_matches_dense() -> None:
    rng = np.random.default_rng(1)
    w = rng.normal(size=(12, 10))   # larger than the 3x3 tile
    x = rng.normal(size=10)
    out, _ = _scenario(w, x, 3, 3, 3)
    np.testing.assert_allclose(out, w @ x, atol=0.02)


def test_parallel_ledger_no_rewrites() -> None:
    w = np.ones((6, 6))
    x = np.ones(6)
    # 6x6 over 3x3 tile -> 2x2 = 4 blocks; 4 tiles on board -> parallel
    _out, acc = _scenario(w, x, 3, 3, 4)
    assert acc.macs == 36
    assert acc.tile_cycles == 1
    assert acc.rewrites == 0


def test_temporal_reuse_counts_rewrites() -> None:
    w = np.ones((6, 6))
    x = np.ones(6)
    _out, acc = _scenario(w, x, 3, 3, 2)   # 4 blocks over 2 tiles -> reuse
    assert acc.rewrites == 4 - 2
    assert acc.tile_cycles == int(np.ceil(4 / 2))
    assert acc.macs == 36
