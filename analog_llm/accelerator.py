"""Accelerator: map a logical matrix-vector multiplication over crossbar tiles.

A physical crossbar tile is ``R x C`` cells and holds exactly one ``R x C``
weight block at a time. A logical weight matrix larger than one tile is split
into blocks; results are accumulated digitally across column groups (partial
sums). If the on-board tile capacity is smaller than the number of blocks, the
same tiles are reprogrammed and reused (temporal reuse), which the ledger
counts as rewrites.

The ledger reports physical metrics, not end-to-end wall-clock time:

- ``macs``: multiplies and accumulates physically performed on tiles
  (incl. the redundant differential cells? No: only the resolved dot-product
   terms ``G+ - G-`` per cell, i.e. ``rows * cols`` per block).
- ``tile_cycles``: a lower bound on sequential block-MVM latency assuming
  unlimited parallel tiles.
- ``rewrites``: how many times a physical tile had to be re-programmed.
"""

from __future__ import annotations

from typing import Callable

import numpy as np
from numpy.typing import ArrayLike, NDArray

from .tile import CrossbarTile


class Accelerator:
    def __init__(
        self,
        tile_factory: Callable[[], CrossbarTile],
        tile_rows: int,
        tile_cols: int,
        tile_count: int,
    ) -> None:
        if tile_rows <= 0 or tile_cols <= 0 or tile_count <= 0:
            raise ValueError("tile dims and count must be positive")
        self.tile_rows = int(tile_rows)
        self.tile_cols = int(tile_cols)
        self.tile_count = int(tile_count)
        self._tiles: list[CrossbarTile] = [tile_factory() for _ in range(tile_count)]
        self.reset_ledger()

    def reset_ledger(self) -> None:
        self.macs = 0
        self.tile_cycles = 0
        self.rewrites = 0
        self.programs = 0

    def _blocks(
        self, w: NDArray[np.float64], x: NDArray[np.float64]
    ) -> list[tuple[tuple[int, int, int, int], NDArray[np.float64], NDArray[np.float64]]]:
        blocks = []
        out, inp = w.shape
        for ri in range(0, out, self.tile_rows):
            r_end = min(ri + self.tile_rows, out)
            for ci in range(0, inp, self.tile_cols):
                c_end = min(ci + self.tile_cols, inp)
                blocks.append(
                    ((ri, r_end, ci, c_end), w[ri:r_end, ci:c_end], x[ci:c_end])
                )
        return blocks

    def mvm(self, matrix: ArrayLike, vector: ArrayLike) -> NDArray[np.float64]:
        """Compute ``matrix @ vector`` split over tiles, accumulating partial sums."""
        w = np.asarray(matrix, dtype=np.float64)
        x = np.asarray(vector, dtype=np.float64).reshape(-1)
        if w.ndim != 2 or x.ndim != 1 or w.shape[1] != x.shape[0]:
            raise ValueError("expected matrix [outputs, inputs] and vector [inputs]")
        if np.any(~np.isfinite(w)) or np.any(~np.isfinite(x)):
            raise ValueError("inputs must be finite")

        blocks = self._blocks(w, x)
        n_blocks = len(blocks)
        if n_blocks == 0:
            return np.zeros(w.shape[0], dtype=np.float64)

        result = np.zeros(w.shape[0], dtype=np.float64)
        for i, (slice_, wb, xb) in enumerate(blocks):
            ri, r_end, _ci, _c_end = slice_
            tile = self._tiles[i % self.tile_count]
            if i >= self.tile_count:
                self.rewrites += 1
            # pad the block to the physical tile size (unused cells stay zero)
            wp = np.zeros((self.tile_rows, self.tile_cols), dtype=np.float64)
            wp[:wb.shape[0], :wb.shape[1]] = wb
            xp = np.zeros(self.tile_cols, dtype=np.float64)
            xp[:xb.shape[0]] = xb
            tile.program(wp)
            yfull = tile.forward(xp)
            result[ri:r_end] += yfull[: r_end - ri]

        self.macs += sum(int((r_end - ri) * (c_end - ci)) for (ri, r_end, ci, c_end), _, _ in blocks)
        self.tile_cycles += int(np.ceil(n_blocks / self.tile_count))
        self.programs += n_blocks  # each block is programmed onto a tile
        return result
