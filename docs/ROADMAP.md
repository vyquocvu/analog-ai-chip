# Roadmap — Analog LLM Accelerator (simulation)

The product is a hybrid analog-digital accelerator for running a small LLM,
simulated end to end in NumPy. Each milestone is done only when backed by
executable evidence (tests + a runnable demo/report), never by prose alone.

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
- [ ] Per-non-ideality ablation (bits, noise, gain/offset independently)
- [ ] Bit sweep producing an accuracy-vs-cost curve
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
