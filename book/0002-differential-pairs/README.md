# 0002 — Signed weights with differential pairs

> **Reading time:** ~12 min · **Run:** `python book/0002-differential-pairs/train.py`
> **Bản tiếng Việt:** [`README.vi.md`](README.vi.md)

Chapter 0001 ended with a hard rule: **a crossbar cell can only store a
non-negative conductance `G ≥ 0`.** But neural-network weights are often
negative. This chapter shows the standard trick: represent each signed weight
with **two** non-negative conductances and subtract them.

## 1. The idea

Store every weight as a difference of two conductances:

```text
W = (G+ − G−) / scale        with   G+ ≥ 0  and  G− ≥ 0
```

- **G+** keeps only the positive parts of `W` (the strength of "this input
  pushes the output up").
- **G−** keeps only the magnitudes of the negative parts (the strength of "this
  input pushes the output down").
- `scale` is a chosen gain/unit constant; dividing by it recovers `W`.

Both arrays remain physically valid because neither ever goes negative.

## 2. The encoding, in pictures

![Differential-pair encoding: W = (G+ − G−)/scale](diagrams/differential_encoding.svg)

For `W = [[1.0, −2.0], [−0.5, 3.0]]` and `scale = 4`:

```text
G+ = clip(W, 0) × 4  = [[4.0, 0.0],
                        [0.0,12.0]]

G− = clip(−W,0) × 4  = [[0.0, 8.0],
                        [2.0, 0.0]]
```

Check the reconstruction by hand for the negative weight `−2.0`
(`G+ = 0`, `G− = 8`):

```text
(0 − 8) / 4 = −2.0   ✓
```

## 3. How the circuit computes the subtraction

Each weight now spans **two columns**: a `G+` column and a `G−` column. When an
input `x` arrives:

```text
I+ = G+ · x      (current from the positive columns)
I− = G− · x      (current from the negative columns)
W@x = (I+ − I−) / scale
```

```text
        x ──► [ G+ array ] ──► I+ ─┐
                                    ├─ subtraction ─► output = (I+ − I−)/scale
        x ──► [ G− array ] ──► I− ─┘
```

For `x = [2, 1]`:

```text
I+ = G+ · x = [8, 12]
I− = G− · x = [8,  4]
output = (I+ − I−) / 4 = [0, 2]
```

which matches `W @ x = [1×2 + (−2)×1, (−0.5)×2 + 3×1] = [0, 2]`.

The subtraction is done in the analog/current domain or after a mixed-signal
read — the lesson only requires the *numbers* to recover the signed result.

## 4. Run it

```bash
python book/0002-differential-pairs/train.py
```

`map_differential` builds `(G+, G−)`; `differential_mvm` applies `x` to both and
subtracts. The assertion on `[0, 2]` and the `G+ ≥ 0, G− ≥ 0` checks are the
contract.

## 5. Cost revealed (be honest about it)

A differential mapping **doubles the number of programmed conductance cells**
for this simple representation: one signed weight = two cells. Multiply that by
the matrix size and the area/energy/calibration cost of the tile grows. This is
a real, physical price — later chapters and the `analog_llm` simulator track
it (the simulator's differential model also introduces a balanced common-mode
`gmin` and finite `g_bits`, see below) rather than treating signed weights as
free.

> **Bridge to the simulator:** `analog_llm.crossbar.map_differential` uses the
> same `G+ − G−` idea but with a *balanced* pair `[gmin, gmax]`: a zero weight
> is stored as the pair `(gmin, gmin)` (both cells on, cancelling) instead of
> `(0, 0)`. That is more physically realistic — real programmable cells have a
> positive minimum conductance. The arithmetic here with `G = 0` cells is a
> simplification you can revisit there.

## 6. Why not just one cell with a sign?

Because physical conductance is a passive, non-negative quantity — you cannot
store `−2 siemens`. There is no free lunch: the "sign bit" costs a whole extra
cell per weight, and its calibration (matching the two branches) is exactly
what makes differential arrays harder than unsigned ones.

## 7. Boundary of this chapter

Reconstructing `W` numerically, and computing `(G+·x − G−·x)/scale`, is a
*functional* model. It does not model the branch-matching (gain/offset
mismatch between the `G+` and `G−` columns), common-mode error, or the
converter that reads `I+ − I−`. Those are real errors the `analog_llm` simulator
adds explicitly as `adc_gain`, `adc_offset`, and finite `g_bits`.

## 8. Exercises

1. Hand-encode `W = [[−1.0, 0.5]]` with `scale = 2` into `(G+, G−)`; verify
   `(G+ − G−)/2` recovers `W`.
2. Show that a **zero** weight maps to `(0, 0)` in this model — the simplest
   possible difference.
3. For `W = [[1.0, −2.0], [−0.5, 3.0]]` and `x = [0.5, 1.5]`, compute `W@x`
   both ways (directly and via `(G+·x − G−·x)/4`) and confirm they agree.
4. What does `scale` physically represent? Change it and explain why `W` is
   unchanged while `G+`, `G−` grow.

## 9. Next

Chapter 0003 (`converters-and-noise`) adds the fact that real inputs and outputs
pass through finite-resolution, noisy DACs and ADCs. The `analog_llm` simulator
then combines differential weights, converters, and tiling to run a full tiny
transformer (`scripts/run_llm_sim.py`).
