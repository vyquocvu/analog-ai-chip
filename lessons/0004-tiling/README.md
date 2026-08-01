# 0004 — Tiling a matrix across physical arrays

A logical LLM matrix is much larger than one practical crossbar. Split both output rows and input columns into tiles. Each tile computes a local matrix-vector product; tiles that cover different input columns produce partial sums that must be accumulated.

For a matrix with shape `4×5` and physical tiles `2×3`, the mapping uses four tiles:

```text
rows 0:2, cols 0:3    rows 0:2, cols 3:5
rows 2:4, cols 0:3    rows 2:4, cols 3:5
```

The two column tiles for each row range are added to recover the logical output.

Run `python lessons/0004-tiling/train.py`. It prints each reference output and verifies the tiled implementation exactly matches dense multiplication.

## Why O(1) needs qualification

One physical array may evaluate its resident MVM in one analog operation, but a large layer requires multiple tiles, converter cycles, partial-sum accumulation, communication, and scheduling. End-to-end layer time is therefore not simply constant with model size.
