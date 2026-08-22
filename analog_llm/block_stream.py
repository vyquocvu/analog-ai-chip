"""Block-streamed linear projection engine for memory-bounded execution.

Evaluates dense linear matrix-vector multiplications across physical crossbar
tile blocks without materializing full-matrix float64 transposition copies.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray

from .accelerator import Accelerator

FloatArray = NDArray[np.float64]


@dataclass(frozen=True)
class StreamedMemoryBudget:
    """Analytical memory requirements for block-streamed execution."""

    whole_matrix_float64_bytes: int
    working_block_bytes: int
    input_buffer_bytes: int
    output_buffer_bytes: int
    peak_working_bytes: int
    memory_reduction_ratio: float


def streamed_linear_mvm(
    x: FloatArray,
    weight: FloatArray,
    bias: FloatArray | None = None,
    tile_rows: int = 16,
    tile_cols: int = 16,
    accelerator: Accelerator | None = None,
) -> FloatArray:
    """Execute linear projection Y = X @ W.T + bias via block-streamed tile iteration.

    Parameters
    ----------
    x : FloatArray
        Input activation tensor, shape [in_features] or [tokens, in_features].
    weight : FloatArray
        Weight matrix in simulator-native out_in layout [out_features, in_features].
    bias : FloatArray | None
        Optional additive bias vector [out_features].
    tile_rows : int
        Physical crossbar tile row count (along in_features).
    tile_cols : int
        Physical crossbar tile column count (along out_features).
    accelerator : Accelerator | None
        Optional physical tile accelerator for hardware non-ideality simulation.

    Returns
    -------
    FloatArray
        Projected output tensor, shape [out_features] or [tokens, out_features].
    """
    x_arr = np.asarray(x, dtype=np.float64)
    weight_arr = np.asarray(weight)
    is_1d = x_arr.ndim == 1
    if is_1d:
        x_2d = x_arr[None, :]
    elif x_arr.ndim == 2:
        x_2d = x_arr
    else:
        raise ValueError(f"Input x must be 1D or 2D, got shape {x_arr.shape}")

    tokens, in_features = x_2d.shape
    out_features, weight_in = weight_arr.shape
    if in_features != weight_in:
        raise ValueError(
            f"Dimension mismatch: x in_features ({in_features}) != weight in_features ({weight_in})"
        )

    out = np.zeros((tokens, out_features), dtype=np.float64)

    row_blocks = math.ceil(in_features / tile_rows)
    col_blocks = math.ceil(out_features / tile_cols)

    for cb in range(col_blocks):
        c_start = cb * tile_cols
        c_end = min(c_start + tile_cols, out_features)
        actual_cols = c_end - c_start

        # Accumulate partial sums across row blocks (in_features partitioning)
        partial_sum = np.zeros((tokens, actual_cols), dtype=np.float64)

        for rb in range(row_blocks):
            r_start = rb * tile_rows
            r_end = min(r_start + tile_rows, in_features)
            actual_rows = r_end - r_start

            # Extract block without copying entire matrix
            w_block = weight_arr[c_start:c_end, r_start:r_end]
            x_chunk = x_2d[:, r_start:r_end]

            if accelerator is None:
                # Digital vectorized tile-block evaluation
                partial_sum += x_chunk @ w_block.T
            else:
                # Route through physical tile accelerator with padding if necessary
                if actual_rows < tile_rows or actual_cols < tile_cols:
                    padded_w = np.zeros((tile_cols, tile_rows), dtype=np.float64)
                    padded_w[:actual_cols, :actual_rows] = w_block
                    for t in range(tokens):
                        padded_x = np.zeros(tile_rows, dtype=np.float64)
                        padded_x[:actual_rows] = x_chunk[t]
                        tile_out = accelerator.mvm(padded_w, padded_x)
                        partial_sum[t] += tile_out[:actual_cols]
                else:
                    for t in range(tokens):
                        partial_sum[t] += accelerator.mvm(w_block, x_chunk[t])

        out[:, c_start:c_end] = partial_sum

    if bias is not None:
        bias_arr = np.asarray(bias, dtype=np.float64)
        if bias_arr.shape != (out_features,):
            raise ValueError(f"Bias shape {bias_arr.shape} does not match out_features {out_features}")
        out += bias_arr

    return out[0] if is_1d else out


def calculate_execution_memory_budget(
    in_features: int,
    out_features: int,
    tokens: int = 1,
    dtype_bytes: int = 2,
    tile_rows: int = 16,
    tile_cols: int = 16,
) -> StreamedMemoryBudget:
    """Calculate peak working memory bound vs whole-matrix float64 copy."""
    whole_matrix_float64 = in_features * out_features * 8
    working_block = tile_rows * tile_cols * dtype_bytes
    input_buffer = tokens * in_features * 8
    output_buffer = tokens * out_features * 8
    peak_working = working_block + input_buffer + output_buffer
    ratio = whole_matrix_float64 / max(1, peak_working)

    return StreamedMemoryBudget(
        whole_matrix_float64_bytes=whole_matrix_float64,
        working_block_bytes=working_block,
        input_buffer_bytes=input_buffer,
        output_buffer_bytes=output_buffer,
        peak_working_bytes=peak_working,
        memory_reduction_ratio=ratio,
    )


class BlockStreamedLinear:
    """Encapsulates a linear layer executed via block streaming."""

    def __init__(
        self,
        weight: FloatArray,
        bias: FloatArray | None = None,
        tile_rows: int = 16,
        tile_cols: int = 16,
    ) -> None:
        self.weight = np.asarray(weight)
        self.bias = np.asarray(bias, dtype=np.float64) if bias is not None else None
        self.tile_rows = int(tile_rows)
        self.tile_cols = int(tile_cols)
        self.out_features, self.in_features = self.weight.shape

    def __call__(
        self,
        x: FloatArray,
        accelerator: Accelerator | None = None,
    ) -> FloatArray:
        return streamed_linear_mvm(
            x=x,
            weight=self.weight,
            bias=self.bias,
            tile_rows=self.tile_rows,
            tile_cols=self.tile_cols,
            accelerator=accelerator,
        )

    def memory_budget(self, tokens: int = 1, dtype_bytes: int = 2) -> StreamedMemoryBudget:
        return calculate_execution_memory_budget(
            in_features=self.in_features,
            out_features=self.out_features,
            tokens=tokens,
            dtype_bytes=dtype_bytes,
            tile_rows=self.tile_rows,
            tile_cols=self.tile_cols,
        )
