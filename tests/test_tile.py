import numpy as np
import pytest

from analog_llm.tile import CrossbarTile


def _high_bits_tile(rows: int, cols: int) -> CrossbarTile:
    return CrossbarTile(
        rows, cols, g_bits=12, dac_bits=16, adc_bits=16, vout_max=8.0,
    )


def test_tile_forward_approximates_weighted_sum() -> None:
    tile = _high_bits_tile(rows=2, cols=2)
    w = np.array([[1.0, 0.5], [-0.25, 1.0]])
    x = np.array([0.6, -0.8])
    tile.program(w)
    y = tile.forward(x)
    np.testing.assert_allclose(y, w @ x, atol=0.02)


def test_tile_zero_input_returns_zero() -> None:
    tile = _high_bits_tile(rows=2, cols=2)
    tile.program(np.ones((2, 2)))
    assert np.allclose(tile.forward(np.zeros(2)), 0.0, atol=1e-6)


def test_forward_before_program_raises() -> None:
    tile = _high_bits_tile(rows=2, cols=2)
    with pytest.raises(RuntimeError, match="not programmed"):
        tile.forward([1.0, 1.0])


def test_shape_mismatch_raises() -> None:
    tile = _high_bits_tile(rows=2, cols=2)
    with pytest.raises(ValueError, match="expected weights shape"):
        tile.program(np.ones((3, 2)))
    tile.program(np.ones((2, 2)))
    with pytest.raises(ValueError, match="inputs"):
        tile.forward([1.0, 2.0, 3.0])


def test_nonfinite_weights_rejected() -> None:
    tile = _high_bits_tile(rows=2, cols=2)
    with pytest.raises(ValueError, match="finite"):
        tile.program(np.array([[np.nan, 0.0], [0.0, 0.0]]))


def test_invalid_dims_rejected() -> None:
    with pytest.raises(ValueError, match="positive"):
        CrossbarTile(0, 2)
