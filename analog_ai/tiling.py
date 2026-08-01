"""Map a logical matrix-vector multiplication over finite crossbar tiles."""

from __future__ import annotations

import numpy as np
from numpy.typing import ArrayLike, NDArray


def tiled_mvm(matrix: ArrayLike, vector: ArrayLike, tile_rows: int, tile_cols: int) -> NDArray:
    """Compute matrix @ vector using explicit tile partial sums."""
    a = np.asarray(matrix, dtype=np.float64)
    x = np.asarray(vector, dtype=np.float64)
    if a.ndim != 2 or x.ndim != 1 or a.shape[1] != x.shape[0]:
        raise ValueError("expected matrix [outputs, inputs] and vector [inputs]")
    if tile_rows <= 0 or tile_cols <= 0:
        raise ValueError("tile dimensions must be positive")

    result = np.zeros(a.shape[0], dtype=np.float64)
    for row_start in range(0, a.shape[0], tile_rows):
        row_end = min(row_start + tile_rows, a.shape[0])
        for col_start in range(0, a.shape[1], tile_cols):
            col_end = min(col_start + tile_cols, a.shape[1])
            result[row_start:row_end] += (
                a[row_start:row_end, col_start:col_end] @ x[col_start:col_end]
            )
    return result
