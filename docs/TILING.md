# Tiling and temporal-reuse scheduler analysis (M2)

This document freezes how the accelerator maps a logical matrix over physical
crossbar tiles and analyzes the resulting schedule.

## Block decomposition

A logical matrix `W` of shape `(R, C)` over physical tiles of shape
`(Tr, Tc)` splits into row and column groups:

```
BR = ceil(R / Tr)     # row groups
BC = ceil(C / Tc)     # column groups
blocks = BR * BC
```

Each block is a `(Tr, Tc)` tile-sized chunk that is programmed onto a physical
tile and multiplied by its slice of the input. Partial sums across the `BC`
column groups are accumulated **digitally** per output row block, so a tile
only ever stores one block at a time.

## Linear-scan schedule over `T` on-board tiles

The reference schedule processes blocks in row-major order, reusing the `T`
physical tiles round-robin (`tile[i % T]`). Because every block is equal cost
and independent, the lower bound on sequential block-MVM cycles is:

```
mvm_cycles = ceil(blocks / T)
```

and the number of tile (re)programs is:

```
programs  = blocks                        # one program per block
initial   = min(blocks, T)                # first-time programs
rewrites  = max(0, blocks - T)            # reprogramming due to reuse
```

`programs == initial + rewrites`, and `programs >= rewrites`.

## Temporal reuse

When `blocks > T` the same physical tile is re-programmed for a later block;
this is exactly the `rewrites` count. Reuse is what lets a small board run a
large matrix, at the cost of extra programming time. More on-board tiles
(`T`) reduce `rewrites` and `mvm_cycles` down to their floor
(`cycles -> ceil(blocks/T)`), but add DAC/ADC converter hardware — see
`docs/../analog_llm/latency.py` and the M6 sensitivity study.

## Across matrices / KV reuse

The same schedule runs per matrix-vector product (each linear layer, each
token). With a KV cache (M3) later tokens skip re-MVM of past context, so the
*per-token* `blocks` and thus `cycles`/`programs` stay constant, rather than
growing with context as in the no-cache trace (`scripts/token_trace.py`).

## System latency model (ties M6)

Given a run, the accelerator exposes `macs`, `cycles`, `rewrites`, `programs`.
With designer-supplied (assumed, relative-unit) timing:

```
latency = cycles * mvm_cycle_time + programs * program_time
```

This is a model estimate in relative units (`tu`) from supplied assumptions —
not a measured wall-clock value and never a GPU comparison. See
`analog_llm/latency.py`.
