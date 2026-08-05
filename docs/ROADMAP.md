# Roadmap — Analog LLM Accelerator (simulation)

The product is a hybrid analog-digital accelerator for running a small LLM,
simulated end to end in NumPy. Each milestone is done only when backed by
executable evidence (tests + a runnable demo/report), never by prose alone.

## Book track — hardware verification (SPICE, before building)
- [x] Verify the 0005 weighted-sum circuit in ngspice/PySpice against the hand
      arithmetic (6 input cases within ~5 mV)
- [x] Ship the circuit schematic and a runnable `sim_neuron.py` as a chapter
      deliverable
- [x] Add a real (non-ideal) op-amp model (finite Aol, offset, rail saturation)
      and demonstrate saturation/offset against the ideal result
      (`book/0005-one-analog-neuron/sim_neuron_nonideal.py`)
- [x] DC sweep showing the linear region and both rail clip points
      (`book/0005-one-analog-neuron/sweep_neuron.py` + `diagrams/sweep.svg`)
- [x] Virtual-ground and rail-headroom check: summing node error vs open-loop
      gain + headroom up/down on the 5 V supply
      (`book/0005-one-analog-neuron/headroom_neuron.py` + `diagrams/virtual_ground.svg`)
- [x] Build files for 0005: full schematic, BOM (`bom.csv`), pin-by-pin
      wiring (`breadboard.md`), test points (`testpoints.md`), and bring-up /
      calibration + power-down (`calibration.md`)
- [x] Chapter 0006: many neurons (10/100/1000) as a layer — numpy scaling
      ledger (cells/MACs/tiles), growth plot, and a 2-neuron SPICE check
      (`book/0006-many-neurons/`)

Exit: a builder can reproduce the circuit's expected voltages in simulation
before assembling hardware.

## M0 — Contracts and honest framing
- [x] Define simulator scope and unit conventions (PRODUCT_SPEC.md)
- [x] Converter model: DAC/ADC bits, clipping, noise, gain/offset
- [x] Differential conductance weight model with finite resolution
- [x] Fail-closed validation on invalid inputs
- [ ] Freeze error-budget and reporting format (ledger + token agreement)

Exit: repository layout, matrix convention, and metric definitions are stable.

## M1 — Crossbar and tile
- [x] Weight normalization to [-1,1] and differential encoding
- [x] Single programmable tile with all converter non-idealities
- [x] Hand-computable tile tests (positive/negative/zero weights)
- [ ] Sweep `g_bits` vs effective-weight error and publish the curve

Exit: a tile's output is attributable and bounded by its configuration.

## M2 — Accelerator and tiling
- [x] Split a logical matrix into physical tiles with digital partial sums
- [x] Pad edge blocks to the physical tile size
- [x] Physical ledger: MACs, tile cycles, rewrites, tiles used
- [ ] Multi-tile parallelism model and temporal-reuse scheduler analysis
- [ ] Report a matrix larger than one physical tile (multi-tile demo)

Exit: tiling matches dense reference within the configured error bound.

## M3 — Tiny transformer on the accelerator
- [x] Deterministic nanoGPT-style model (numpy, seeded)
- [x] Hybrid forward: all linears through tiles, rest digital
- [x] Autoregressive generation (no KV cache, documented)
- [x] Unified demo report with float baseline
- [ ] KV-cache path to remove redundant recompute
- [ ] Per-token latency and ledger trace through a full layer

Exit: analog route matches float baseline at high precision.

## M4 — Accuracy / sensitivity study
- [x] High-precision vs budget-constrained configuration in demo
- [x] Per-non-ideality ablation (bits, noise, gain/offset independently)
      (`scripts/ablation.py` + `ablation.svg`)
- [x] Bit sweep producing an accuracy-vs-cost curve
      (`scripts/bit_sweep.py` + `bit_sweep_g.svg` / `bit_sweep_adc.svg`)
- [ ] Guardrail that prevents claiming GPU-equivalence from the ledger

Exit: each non-ideality's contribution to logit error is quantified.

## M5 — Larger / pretrained weights (experimental)
- [ ] Loader for real checkpoint weights (e.g. GPT-2 class) via safetensors
- [ ] tokenizer + numeric parity check against a reference forward pass
- [ ] Map a real small model's layers to tiles and report full-sequence
- [ ] Failure analysis, not only best-case results

Exit: a real open checkpoint runs through the simulated accelerator with a
documented accuracy-vs-baseline table.

## M6 — Energy / latency product estimate (measured assumptions only)
- [ ] Model converter count, tile programming cost, and reuse in the ledger
- [ ] Sensitivity of system latency to tile capacity and parallelism
- [ ] No GPU comparison without measured physical assumptions

Exit: the roadmap's `O(1)`-style claims are replaced by explicit formulas.
