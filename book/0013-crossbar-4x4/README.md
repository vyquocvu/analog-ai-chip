# 0013 — 4×4 differential crossbar array (R3 gate exit)

> **Bản tiếng Việt:** [`README.vi.md`](README.vi.md)

Scales the validated 0012 topology to a full 4×4 array: four shared input rows
and four independent output columns, each column an 0007 column repeated four
times. This chapter is the **R3 gate exit**: it quantifies the error of the
*architecture simulator's* behavioral model (the `analog_llm` CrossbarTile on
the validated `crossbar-column-v1` profile) against both the SPICE array and
the hand reference, and records the array currents and an assumed-capacitance
settling data point.

```
Vout_j = Rf · Σ_i u_i · (G+_ij − G−_ij) = Rf · Gscale · (W @ u)_j,
u_i = x_i − VREF,  W_ij ∈ [−1, 1],  Rf·Gscale = 1 V per volt per weight
```

Same constants as 0005/0007/0009/0010/0012: `VREF = 2.5 V`, `G0 = Gscale =
0.1 mS`, `Rf = 10 kΩ`, `HEADROOM = ±2.5 V`.

## Method

- **SPICE**: every TIA half-column (8 total) is an independent linear network
  solved in its own ngspice netlist with the same finite-gain (1e4) VCVS as
  0007/0012, then combined by superposition: `Vout_j = Vm_j − Vp_j`.
- **Hand reference**: `Vout = Rf·Gscale·(W @ u)` in NumPy, plus per-cell
  `Iplus_j = Σ_i u_i·G+_ij` current sums.
- **Behavioral tile**: `analog_llm.build_tile_factory` on
  `device_profiles/crossbar-column-v1.json` with 16-bit programming/DAC/ADC
  quantization — the tile's error is its quantization floor, not a hand-tuned
  number.
- **Deterministic suite**: 5 `(W, u)` cases × 4 outputs: mixed-sign, sparse
  diagonal, rank-1, and the zero matrix (balanced-zero check).

## Results (committed in `verification/circuit/results/crossbar-4x4-0013-extract.json`)

| quantity | value |
|---|---|
| worst \|SPICE − hand\| | 5.5e-4 V (rms 3.3e-4 V) |
| worst \|tile − hand\| | 3.8e-5 V (rms 2.8e-5 V) |
| worst \|SPICE − tile\| | 5.2e-4 V (rms 3.1e-4 V) |
| frozen R3 error budget | 2e-3 V (all met) |
| max \|Vout\| | 0.50 V ≪ ±2.5 V headroom |
| max virtual-ground error | 3.0e-4 V |
| worst column-current error | 1.8e-7 A |
| largest cell current | 1.0e-4 A (feasibility bound) |
| 2×2 regression (vs 0012 extract) | 0.0e+00 V |
| zero matrix output | exactly 0 V |

**Behavioral-equivalence finding**: the tile (quantization floor 3.8e-5 V) is
an order of magnitude *closer* to the hand reference than the SPICE array
itself (VCVS finite-gain error 5.5e-4 V), and both are well inside the frozen
2e-3 V budget. The tile is a faithful, conservative behavioral model of the
SPICE array.

## Currents and settling

- Column currents recovered from SPICE half-stage outputs,
  `Iplus_j = (VREF − Vp_j)/Rf`, match the hand `Σ u_i·G+_ij` to 1.8e-7 A.
- **Settling is recorded, not claimed.** A transient with an *assumed*
  1 pF summing-node capacitance gives 22.7 ns to settle within 1 mV (single-pole
  hand lower bound 13.2 ns), but the ideal VCVS has no bandwidth model — the
  waveform tail is model-dominated, so this lives in the extract JSON only and
  fails closed under `physical_claim`. Bounded settling is the 0014 gate item.

## R3 gate exit

All gate items are ticked in `docs/ROADMAP.md` with committed, reproducible
SPICE evidence + behavioral-equivalence report
(`verification/reports/crossbar-4x4-summary.md`). R3 is **COMPLETE**; R4
(programmable-conductance device realism) is the next gate.

## Diagrams

- `diagrams/array_4x4.svg` — full 4×4 schematic: shared rails, 32 differential
  cells, Vp/Vm summing buses, eight TIA stages with Rf feedback, subtractor nodes.
- `diagrams/theory.svg` — theory of operation: MVM equation, differential cell,
  superposition, hand-computable worked example, behavioral-equivalence and
  claim-level summary.
- `diagrams/make_plots.py` → `diagrams/mvm_error.svg` — stdlib-only SVG
  regenerated from the committed extract (per-case error bars vs the R3 budget;
  per-case max |Vout| vs headroom with virtual-ground error).

## Run

```
python book/0013-crossbar-4x4/crossbar_4x4.py      # SPICE suite + assertions
python verification/circuit/extract_crossbar_4x4.py # regenerate extract JSON
python verification/reports/generate_crossbar_4x4_summary.py
python book/0013-crossbar-4x4/diagrams/make_plots.py
pytest tests/test_crossbar_4x4.py
```
