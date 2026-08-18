# Sprint History Archive

This document archives completed Sprint reviews, retrospectives, and historical deliverables from Sprints 1 through 17. For active backlog items and the current sprint, see [`docs/BACKLOG.md`](../BACKLOG.md).

---

## Historical Completed Backlog Items (A1–A5, B1–B6, M1–M6, D1)

### A1 — Real (non-ideal) op-amp model for the 0005 neuron `[S]`
- [x] Sim script runs inverting summer with saturating op-amp model.
- [x] In linear region output matches ideal within tolerance.
- [x] Output clips past rails rather than producing negative values.
- [x] Input offset `Vos` reported.

### A2 — DC sweep / linearity plot for 0005 `[S]`
- [x] Script sweeps input over range spanning both rails (`sweep_neuron.py`).
- [x] Linear slope matches $-W_1$, writes `diagrams/sweep.svg`.
- [x] Linear region and clip points reported.

### A3 — Rail/headroom and virtual-ground check `[S]`
- [x] Script sweeps linear region and reports `max |n - VREF|` (`headroom_neuron.py`).
- [x] Error grows with $1/A_{ol}$.

### A4 — Breadboard wiring + BOM + test-point table for 0005 `[M]`
- [x] `bom.csv` with parts + substitutes; `breadboard.md` with LM358 wiring.
- [x] `testpoints.md` (TP1–TP9) + `calibration.md`.

### A5 — Chapter 0006: many neurons (10 / 100 / 1000) as a layer `[M]`
- [x] NumPy layer model computes $y = W \cdot x$ for $N = 10, 100, 1000$.
- [x] Reports scaling ledger (cells, differential cells, MACs, tiles).

### B1 — Bit sweep: accuracy-vs-cost with simulator `[S]`
- [x] `scripts/bit_sweep.py` sweeping `g_bits` and `adc_bits`.
- [x] Reports token agreement + max logit error vs cost.

### B2 — Per-non-ideality ablation `[S]`
- [x] `scripts/ablation.py` toggles each non-ideality independently (leave-one-out).

### B3 — Multi-tile demo `[M]`
- [x] `scripts/multi_tile_demo.py` runs matrix larger than one physical tile.
- [x] Parallel and temporal-reuse scenarios match dense reference.

### B5 — KV-cache path in transformer `[M]`
- [x] `analog_llm/transformer.py` supports autoregressive generation with KV cache.

### B6 — Per-token ledger trace `[S]`
- [x] `scripts/token_trace.py` traces MACs, tile cycles, rewrites per token position.

### M1 — g_bits vs effective-weight error curve `[S]`
- [x] `analog_llm/sweep.py` sweeps `g_bits` from 1 to 16 against float reference.

### M5 — Real pretrained weights through simulator `[L]`
- [x] GPT-2 weights mapped onto simulated accelerator tiles.

### M6 — Energy / latency product estimate `[M]`
- [x] Ledger extended with tile `programs`; `analog_llm/latency.py` explicit formulas.

### D1 — CI runs circuit sim when ngspice available `[S]`
- [x] `.github/workflows/ci.yml` adds optional `circuit-sim` job.

---

## Sprint 1 (completed) — Review & Retrospective
**Increment (A1, doD met):**
- `book/0005-one-analog-neuron/sim_neuron_nonideal.py` — non-ideal op-amp (finite Aol + input offset + explicit rail clamping).
- Measured: linear @2.5 V ref → out 2.3496 vs ideal 2.3500; saturation → ideal 5.875 clips at 5.000; gnd-referenced single-supply clips at 0 V; Vos 10 mV shifts out +0.0175 V.
- pytest `test_neuron_nonideal_linear_and_rails`.

## Sprint 2 (completed) — Review & Retrospective
**Increment (A2, doD met):**
- `book/0005-one-analog-neuron/sweep_neuron.py` + `diagrams/sweep.svg`.
- Linear slope −0.500 matches $-W_1 = -R_f/R_1 = -10k/20k$; rails flat at 0.000 V and 5.000 V.

## Sprint 3 (completed) — Review & Retrospective
**Increment (A3, doD met):**
- `book/0005-one-analog-neuron/headroom_neuron.py` + `diagrams/virtual_ground.svg`.
- Virtual ground offset $|n - VREF| = 0.038$ mV for $A_{ol} = 100k$ vs 3.75 mV for $A_{ol} = 1k$.

## Sprint 4 (completed) — Review & Retrospective
**Increment (A4, doD met):**
- `book/0005-one-analog-neuron/` `bom.csv`, `breadboard.md`, `testpoints.md`, `calibration.md`, `diagrams/schematic.svg`.

## Sprint 5 (completed) — Review & Retrospective
**Increment (A5, doD met):**
- `book/0006-many-neurons/layer_scaling.py`, `diagrams/scaling_growth.svg`, `sim_layer_spice.py`.

## Sprint 6 (completed) — Review & Retrospective
**Increment (M1, doD met):**
- `analog_llm/sweep.py` + `tests/test_sweep.py` + `scripts/weight_error_curve.py` + `weight_error.svg`.

## Sprint 7 (completed) — Review & Retrospective
**Increment (B1, doD met):**
- `scripts/bit_sweep.py` + `bit_sweep_g.svg` + `bit_sweep_adc.svg` + `tests/test_bit_sweep.py`.

## Sprint 8 (completed) — Review & Retrospective
**Increment (B2, doD met):**
- `scripts/ablation.py` + `ablation.svg` + `tests/test_ablation.py`.

## Sprint 9 (completed) — Review & Retrospective
**Increment (B3, doD met):**
- `scripts/multi_tile_demo.py` + `multi_tile_layout.svg` + `tests/test_multi_tile.py`.

## Sprint 10 (completed) — Review & Retrospective
**Increment (B5, doD met):**
- `analog_llm/transformer.py` autoregressive generation with KV cache + `tests/test_kv_cache.py`.

## Sprint 11 (completed) — Review & Retrospective
**Increment (B6, doD met):**
- `scripts/token_trace.py` + `token_trace.svg` + `tests/test_token_trace.py`.

## Sprint 12 (completed) — Review & Retrospective
**Increment (M5, doD met):**
- `analog_llm/weights.py` + `scripts/run_pretrained_demo.py` + `tests/test_pretrained.py`.

## Sprint 13 (completed) — Review & Retrospective
**Increment (M6, doD met):**
- `analog_llm/latency.py` + `scripts/energy_latency.py` + `latency_sensitivity.svg` + `tests/test_latency.py`.

## Sprint 14 (completed) — Review & Retrospective
**Increment (D1, doD met):**
- `.github/workflows/ci.yml` `circuit-sim` job.

## Sprint 15 (completed) — Review & Retrospective
**Increment (M4, M0, M2, M3, doD met):**
- `analog_llm/guardrail.py` + `docs/PRODUCT_SPEC.md` reporting format + `docs/TILING.md`.

## Sprint 16 (completed) — Review & Retrospective
**Increment (0007, doD met):**
- `book/0007-crossbar-column/crossbar_column.py` SPICE differential crossbar column model.

## Sprint 17 (completed) — Review & Retrospective
**Increment (MEAS, doD met):**
- `book/0005-one-analog-neuron/measurements.csv` + `scripts/check_measurements.py` + `tests/test_measurements.py`.
