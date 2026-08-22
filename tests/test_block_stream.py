import numpy as np
import pytest

from analog_llm.accelerator import Accelerator
from analog_llm.block_stream import (
    BlockStreamedLinear,
    streamed_linear_mvm,
)
from analog_llm.tile import CrossbarTile


def test_hand_computable_block_stream_parity() -> None:
    # 4 outputs, 6 inputs, 2x2 tile blocks
    W = np.array([
        [1.0, 2.0, 3.0, 4.0, 5.0, 6.0],
        [2.0, 0.0, 1.0, -1.0, 0.5, 2.0],
        [-1.0, 1.0, 0.0, 2.0, -2.0, 1.0],
        [0.5, -0.5, 1.0, 0.0, 3.0, -1.0],
    ])
    b = np.array([0.1, -0.2, 0.3, 0.4])
    x = np.array([1.0, 0.5, 2.0, -1.0, 0.0, 1.5])

    expected = x @ W.T + b
    actual = streamed_linear_mvm(x, W, bias=b, tile_rows=2, tile_cols=2)

    np.testing.assert_allclose(actual, expected, atol=1e-12)


def test_batched_prefill_and_arbitrary_unaligned_dimensions() -> None:
    rng = np.random.default_rng(42)
    # Unaligned dimensions: 23 out, 37 in over 16x16 tiles
    out_features, in_features = 23, 37
    tokens = 5

    W = rng.normal(0.0, 0.1, (out_features, in_features))
    b = rng.normal(0.0, 0.05, (out_features,))
    X = rng.normal(0.0, 1.0, (tokens, in_features))

    expected = X @ W.T + b
    actual = streamed_linear_mvm(X, W, bias=b, tile_rows=16, tile_cols=16)

    np.testing.assert_allclose(actual, expected, atol=1e-12)

    # Verify each row independently matches
    for t in range(tokens):
        row_actual = streamed_linear_mvm(X[t], W, bias=b, tile_rows=16, tile_cols=16)
        np.testing.assert_allclose(row_actual, expected[t], atol=1e-12)


def test_block_streamed_linear_class_wrapper() -> None:
    rng = np.random.default_rng(99)
    W = rng.normal(0.0, 0.02, (64, 64))
    b = np.zeros(64)
    x = rng.normal(0.0, 1.0, (3, 64))

    layer = BlockStreamedLinear(W, bias=b, tile_rows=16, tile_cols=16)
    out = layer(x)

    np.testing.assert_allclose(out, x @ W.T, atol=1e-12)

    budget = layer.memory_budget(tokens=3, dtype_bytes=2)
    assert budget.working_block_bytes == 16 * 16 * 2
    assert budget.input_buffer_bytes == 3 * 64 * 8
    assert budget.output_buffer_bytes == 3 * 64 * 8
    assert budget.whole_matrix_float64_bytes == 64 * 64 * 8


def test_analog_accelerator_integration_with_block_streaming() -> None:
    rng = np.random.default_rng(123)
    W = rng.normal(0.0, 0.05, (32, 32))
    x = rng.normal(0.0, 1.0, (2, 32))

    acc = Accelerator(
        lambda: CrossbarTile(16, 16, g_bits=8, dac_bits=8, adc_bits=8, vout_max=4.0),
        tile_rows=16,
        tile_cols=16,
        tile_count=4,
    )

    out = streamed_linear_mvm(x, W, tile_rows=16, tile_cols=16, accelerator=acc)
    assert out.shape == (2, 32)
    assert acc.macs == 2 * 32 * 32


def test_block_stream_fails_closed_on_invalid_inputs() -> None:
    W = np.zeros((8, 8))
    # 3D input not supported
    with pytest.raises(ValueError, match="Input x must be 1D or 2D"):
        streamed_linear_mvm(np.zeros((1, 2, 8)), W)

    # In-features dimension mismatch
    with pytest.raises(ValueError, match="Dimension mismatch"):
        streamed_linear_mvm(np.zeros(7), W)

    # Bias shape mismatch
    with pytest.raises(ValueError, match="Bias shape"):
        streamed_linear_mvm(np.zeros(8), W, bias=np.zeros(9))
