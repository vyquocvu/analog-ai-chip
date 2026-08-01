# 0002 — Signed weights with differential pairs

Neural-network weights may be negative, but conductance cannot. Represent each weight with two cells:

```text
W = (G+ - G-) / scale
```

For `W = [[1, -2], [-0.5, 3]]` and `scale = 4`, the positive array stores positive parts and the negative array stores magnitudes of negative parts. Both arrays remain non-negative.

For input `x = [2, 1]`:

```text
W @ x = [1×2 + (-2)×1, (-0.5)×2 + 3×1] = [0, 2]
```

The two arrays independently produce currents, then a digital or mixed-signal subtraction recovers the signed result.

Run `python lessons/0002-differential-pairs/train.py`.

## Cost revealed

A differential mapping doubles the number of programmed conductance cells for the simple representation used here. Later lessons will track this area and energy cost rather than treating signed weights as free.
