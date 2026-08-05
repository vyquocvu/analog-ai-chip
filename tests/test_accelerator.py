import numpy as np
import pytest

from analog_llm.accelerator import Accelerator
from analog_llm.tile import CrossbarTile


def _acc(tile_rows=2, tile_cols=2, tile_count=4, vout_max=64.0) -> Accelerator:
    def factory() -> CrossbarTile:
        return CrossbarTile(
            tile_rows, tile_cols, g_bits=12, dac_bits=16, adc_bits=16, vout_max=vout_max
        )
    return Accelerator(factory, tile_rows, tile_cols, tile_count)


def test_single_tile_matches_dense() -> None:
    acc = _acc(tile_rows=2, tile_cols=2, tile_count=4)
    w = np.array([[1.0, 0.5], [-0.25, 1.0]])
    x = np.array([0.6, -0.8])
    np.testing.assert_allclose(acc.mvm(w, x), w @ x, atol=0.02)


def test_tiling_across_blocks_matches_dense() -> None:
    acc = _acc(tile_rows=2, tile_cols=2, tile_count=4)
    w = np.arange(1.0, 21.0).reshape(4, 5)
    x = np.array([1.0, -1.0, 0.5, 2.0, -0.25])
    np.testing.assert_allclose(acc.mvm(w, x), w @ x, atol=0.05)


def test_ledger_counts_macs_and_cycles() -> None:
    acc = _acc(tile_rows=2, tile_cols=2, tile_count=4)
    acc.mvm(np.arange(1.0, 21.0).reshape(4, 5), np.array([1.0, -1.0, 0.5, 2.0, -0.25]))
    # (4,5) splits into 2 row groups x 3 col groups = 6 blocks; each physical MAC
    # is one resolved cell, so total == number of cells = 4*5 = 20.
    assert acc.macs == 20
    # 6 blocks over 4 parallel tiles -> ceil(6/4) = 2 sequential cycles.
    assert acc.tile_cycles == 2


def test_temporal_reuse_counts_rewrites() -> None:
    acc = _acc(tile_rows=2, tile_cols=2, tile_count=2)
    acc.mvm(np.eye(6, 6), np.ones(6))  # 9 blocks over 2 tiles
    assert acc.rewrites > 0
    acc.reset_ledger()
    assert acc.rewrites == 0 and acc.macs == 0


def test_invalid_dims_rejected() -> None:
    acc = _acc()
    with pytest.raises(ValueError, match="matrix"):
        acc.mvm(np.ones((3, 2, 1)), np.ones(2))
    with pytest.raises(ValueError, match="finite"):
        acc.mvm(np.ones((2, 2)), np.array([np.inf, 1.0]))


def test_invalid_accelerator_config_rejected() -> None:
    def factory():
        return CrossbarTile(2, 2)
    with pytest.raises(ValueError, match="positive"):
        Accelerator(factory, 0, 2, 2)
