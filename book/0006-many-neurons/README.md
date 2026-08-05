# 0006 — Many neurons: a layer (10, 100, 1000)

> **Reading time:** ~15 min · **Run:** `python book/0006-many-neurons/layer_neuron.py`
> **Bản tiếng Việt:** [`README.vi.md`](README.vi.md)

Chapter 0005 built one analog neuron. A neural network needs hundreds or
thousands of them. The good news: **a layer of N neurons, each summing M
inputs, is exactly the matrix-vector product `y = W @ x` from chapter 0001.**
Scaling is nothing new — it is the same math on more conductance cells.

## 1. One neuron → a layer

A single neuron is `y = w1·x1 + w2·x2`. A layer of `N` neurons, each reading the
same M inputs, is:

```text
y[i] = sum_j W[i,j]·x[j]      for i = 0..N-1, j = 0..M-1
Y    = W @ x                  (W is N × M)
```

This is the crossbar again: rows are the N neurons' weight vectors, columns are
the M inputs, and each output is one summed column (0001's `I = G @ V`, with
signed weights via differential pairs from 0002).

## 2. Run it: 10, 100, 1000 neurons

```bash
python book/0006-many-neurons/layer_neuron.py
```

For `M = 16` inputs per neuron (signed, differential):

```text
  N     cells  cells(signed)   MACs  tiles  cycles     max|err|
   10      160         320      160      1       1  5.37e-04
  100     1600        3200     1600      2       1  5.74e-04
 1000    16000       32000    16000     16       1  6.28e-04
```

![Layer growth: cells and MACs vs neurons](diagrams/growth.svg)

The tiled `analog_llm` layer matches the float reference to ~6e-4 — adding
neurons changes only the *size*, not the *arithmetic*.

## 3. What actually grows

Everything scales **linearly** in `N` (for fixed `M`):

- `cells = N·M` conductances (unsigned), `2·N·M` with differential signed
  weights (0002);
- `MACs = N·M` multiplies-accumulates per forward pass;
- `physical tiles = ceil(N/T)·ceil(M/T)` for a tile of size `T` (here 64).

Going from 10 → 100 → 1000 neurons multiplies cells and MACs by 10 each time.
This is the honest cost of "more neurons": more silicon area (conductance
cells), more energy (MACs), and for very large layers more tiles and
accumulation — never a free `O(1)`. (See chapter 0004 and `maths/complexity.md`.)

## 4. Circuit view: 2 neurons on one LM358

A tiny physical sample is straightforward: both neurons are inverting summers
sharing the same 2.5 V virtual reference, and the dual LM358 has exactly two
op-amps. Verify it in SPICE:

```bash
python book/0006-many-neurons/layer_neuron_spice.py
```

```text
x = [3.0, 2.1]  VREF = 2.5
  neuron0: sim=2.3496  ideal=2.3500  err=0.0004
  neuron1: sim=2.3496  ideal=2.3500  err=0.0004
```

Two summer stages run from one chip — the first step toward the crossbar tile
the `analog_llm` simulator (and chapter 0001's `G`) already model.

## 5. Why many neurons justify the crossbar

For thousands of neurons, wiring each neuron's summing node by hand is
hopeless. The crossbar solves this structurally: one shared array of cells,
rows = inputs, columns = outputs (0001). 0006 is the bridge: "multiple neurons"
*is* "a matrix", and "a matrix" *is* "a crossbar". The `analog_llm` simulator
then runs real LLM layers over such tiles.

## 6. Boundary / honest limits

- This is a **functional + simulated** layer; real 1000-neuron arrays need
  programmable conductance (digital pots or later ReRAM), calibration, and
  IR-drop/converter handling — all out of scope here but explicit in
  `docs/PRODUCT_SPEC.md` and `analog_llm`.
- Linear growth of cells/MACs is stated as arithmetic, not as an energy/latency
  advantage over a GPU.

## 7. Exercises

1. Recompute `cells` and `MACs` for `N = 500`, `M = 32` by hand.
2. How many 64×64 tiles does `N = 1000, M = 64` need?
3. Why does `cycles` stay 1 in the table even though `tiles` grows? (All tiles
   fire in parallel when there are enough of them.)
4. Change `M` in `layer_neuron.py` and re-run: does the error stay small?
