# Product Backlog

Ordered by value (highest first). Each item is a small user story with
acceptance criteria. Work happens in sprints; the committed set is in the
"Current Sprint" section at the bottom.

Legend — size: S / M / L. Status: backlog → in-progress → done.

---

## Backlog (ordered)

### A1 — Real (non-ideal) op-amp model for the 0005 neuron  `[S]`
**As a** builder, **I want** the circuit simulation to use a non-ideal op-amp
(finite gain, input offset, rail saturation) so that the limits of a real chip
are visible before I build.

**AC:**
- [x] A sim script runs the inverting summer with a saturating op-amp model.
- [x] In the linear region the output matches the ideal within tolerance.
- [x] An input that would drive the output past a rail saturates (clips) rather
      than producing the ideal negative value.
- [x] A small input offset `Vos` shifts the zero, and the shift is reported.
- [x] Narrative added to `book/0005` + `docs/ROADMAP.md` item checked.

### A2 — DC sweep / linearity plot for 0005  `[S]`
**As a** builder, **I want** a sweep of `Vout` vs an input so I can see the
linear region and the clip points.

**AC:**
- [x] a script sweeps an input over a range spanning both rails
      (`book/0005-one-analog-neuron/sweep_neuron.py`);
- [x] it prints a table, asserts the linear slope matches `−W1`, and writes an
      annotated SVG plot (`diagrams/sweep.svg`);
- [x] the linear region and both clip points are reported;
- [x] chapter + ROADMAP updated.

### A3 — Rail/headroom and virtual-ground check  `[S]`
**As a** builder, **I want** the simulation to confirm the summing node stays
at the reference in the linear region and report the rail headroom.

**AC:**
- [x] script sweeps the linear region and reports `max |n − VREF|` for two
      open-loop gains (`headroom_neuron.py` + `diagrams/virtual_ground.svg`);
- [x] error grows with `1/Aol` (asserted);
- [x] reports headroom up/down on the 5 V supply and the gnd-reference contrast;
- [x] chapter + ROADMAP updated.

### A4 — Breadboard wiring + BOM + test-point table for 0005  `[M]`
**As a** builder, **I want** concrete build files so I can assemble the circuit
from parts and verify it.

**AC:**
- [x] `bom.csv` with parts + substitutes and correct designators;
- [x] `breadboard.md` with pin-by-pin LM358 wiring (virtual-reference design);
- [x] `testpoints.md` (TP1–TP9 expected/actual) + `calibration.md` bring-up /
      power-down;
- [x] full schematic SVG + data-file pytest (validated, no engine needed);
- [x] chapter (EN + VI) and ROADMAP updated.

### A5 — Chapter 0006: many neurons (10 / 100 / 1000) as a layer  `[M]`
**As a** builder, **I want** to scale one neuron up to a layer of N neurons and
see how MACs / conductance cells grow, so I understand the crossbar view.

**AC:**
- [x] a numpy layer model computes `y = W @ x` for N = 10, 100, 1000 and
      matches the float reference (tiled via `analog_llm`);
- [x] reports the scaling ledger (cells, differential cells, MACs, tiles);
- [x] a growth plot (SVG) shows cells/MACs vs N on a log scale;
- [x] a small SPICE 2-neuron layer sanity check (optional engine test);
- [x] chapter 0006 README (EN + VI), ROADMAP, and data/numpy pytest.

### B1 — Bit sweep: accuracy-vs-cost with the simulator  `[S]`
**As a** designer, **I want** a `scripts/bit_sweep.py` that sweeps
`g_bits`/`adc_bits` and reports the accuracy-vs-cost curve.

**AC:**
- [x] runnable `scripts/bit_sweep.py` sweeping `g_bits` and `adc_bits`;
- [x] reports token agreement + max logit error vs cost, with guardrails
      (more bits => lower error);
- [x] SVG curves `bit_sweep_g.svg` / `bit_sweep_adc.svg`; pytest
      (`tests/test_bit_sweep.py`, always);
- [x] ROADMAP M4 bit-sweep item closed.

### B2 — Per-non-ideality ablation  `[S]`
**AC:**
- [x] `scripts/ablation.py` toggles each non-ideality independently
      (leave-one-out: weight bits, DAC bits, ADC bits, noise, gain, offset,
      clipping) and reports the logit-error contribution / share of each;
- [x] guardrails on residuals, an ablation bar-chart SVG `ablation.svg`;
- [x] pytest `tests/test_ablation.py` (always); ROADMAP M4 ablation item closed.

### B3 — Multi-tile demo  `[M]`
**AC:**
- [x] `scripts/multi_tile_demo.py` runs a matrix larger than one physical tile
      (24x16 over 8x8) and reports the ledger with `tile_count > 1` and
      tile_cycles/rewrites;
- [x] both parallel (no rewrites) and temporal-reuse (rewrites>0) scenarios
      match the dense reference; guardrails on MACs/cycles/rewrites;
- [x] tiling-layout SVG `multi_tile_layout.svg`; pytest `tests/test_multi_tile.py`
      (always); ROADMAP M2 multi-tile demo item closed.

### B5 — KV-cache path in the transformer  `[M]`
**AC:**
- [x] `TinyGPT.generate_kvcache` caches per-layer K/V so each generated token
      runs a single-position forward (no full-context recompute);
- [x] greedy and sampling output parity with the no-cache `generate` about
      identical RNG (tested);
- [x] `scripts/kv_cache_demo.py` reports the query-row redundancy ledger and a
      reduction bar (`kv_cache.svg`); pytest `tests/test_kv_cache.py` (always);
      ROADMAP M3 KV-cache item closed.

### B6 — Per-token ledger trace  `[S]`
**AC:**
- [x] `scripts/token_trace.py` traces MACs / tile-cycles / rewrites per generated
      token through a full layer, for the no-KV (grows with context) and
      KV-cache (constant single-position) paths;
- [x] guardrails (per-token no-KV MACs grow; KV single-position <= full forward);
      `token_trace.svg`; pytest `tests/test_token_trace.py` (always);
      ROADMAP M3 per-token ledger trace item closed.

### M1 — g_bits vs effective-weight error curve  `[S]`
**AC:**
- [x] `scripts/gbits_sweep.py` sweeps `g_bits` (2..14) and reports max
      |w - w_eff| (normalized by the conductance span, as the tile does);
- [x] curve matches the analytic bound `1/(2(2^g_bits-1))` and falls
      geometrically; `gbits.svg`;
- [x] pytest `tests/test_gbits_sweep.py` (always); ROADMAP M1 sweep item closed.

### M5 — Real pretrained weights through the simulator  `[L]`
**AC:**
- [x] safetensors loader `load_gpt2` (Conv1D transpose, head tying, block_size,
      fail-closed) maps a real GPT-2 checkpoint into `TinyGPT`;
- [x] minimal byte-level BPE tokenizer + numeric parity vs an independent
      reference forward — **exact** on the real checkpoint;
- [x] `scripts/run_real_model.py` runs a real trained tiny GPT-2
      (`pszemraj/tiny-gpt2-magicprompt`) through the tile accelerator and
      reports full-sequence accuracy-vs-baseline;
- [x] failure analysis (budget config flips, ledger) included;
- [x] pytest `tests/test_gpt_loader.py` + `tests/test_tokenizer.py`; ROADMAP M5
      items, checkpoint staged under `data/gpt2-tiny`.

### M6 — Energy / latency product estimate  `[M]`
**AC:**
- [x] ledger extended with tile `programs`; `analog_llm/latency.py` gives an
      explicit latency/energy formula from design assumptions, all shown and
      labelled as relative units (tu/eu), no GPU comparison;
- [x] `scripts/energy_latency.py` reports converter/program/reuse accounting
      and the sensitivity of latency est. to tile parallelism and capacity
      (`latency_sensitivity.svg`);
- [x] pytest `tests/test_latency.py`; ROADMAP M6 items closed.

### D1 — CI runs the circuit sim when ngspice is available  `[S]`
**AC:**
- [x] `.github/workflows/ci.yml` adds an optional `circuit-sim` job that installs
      ngspice and runs `pytest tests/test_circuit_sim.py`; the SPICE tests skip
      cleanly (exit 0) when the engine/shared library is unavailable, so the job
      never hard-fails on a dependency-light runner.

---

## Sprint 1 (completed) — Review & Retrospective

**Increment (A1, doD met):**
- `book/0005-one-analog-neuron/sim_neuron_nonideal.py` — non-ideal op-amp
  (finite Aol + input offset + explicit rail clamping).
- Measured: 1) linear @2.5 V ref → out 2.3496 vs ideal 2.3500; 2) saturation →
  ideal 5.875 clips at 5.000; 3) gnd-referenced single-supply clips at 0 V
  (chapter warning confirmed); 4) Vos 10 mV shifts out +0.0175 V.
- pytest `test_neuron_nonideal_linear_and_rails` (auto-skip without engine).

**Retrospective:**
- Well: PySpice (shared-lib) is reliable; raw `ngspice -b` + `.print` is NOT
  (ngspice-46 bug) — glad we switched.
- Improve: make rail/headroom explicit in chapter 0005 (A3), and document the
  ngspice-46 quirk once in the chapter.

---

## Sprint 2 (completed) — Review & Retrospective

**Increment (A2, doD met):**
- `book/0005-one-analog-neuron/sweep_neuron.py` — DC sweep of x1 over both
  rails with the non-ideal model; slope matched `−W1 = −0.5`, clips at 0 V and
  5 V; wrote `diagrams/sweep.svg`.
- pytest `test_neuron_dc_sweep_slope_and_rails` (auto-skip without engine).

**Sprint Review (demo summary):**
- linear-region slope = −0.500 (expect −0.500)
- clips at 5 V rail for x1 ≤ −2.5 V; clips at 0 V rail for x1 ≥ 7.5 V
- linear region approx x1 ∈ (−2.5, 7.5) V around the 2.5 V reference

**Retrospective — what went well / to improve:**
- Well: reusing the A1 non-ideal model kept A2 small and consistent; SVG plot
  is a nice self-contained visual.
- Improve: extend the sweep to vary x2 too (2-D region), and make the
  "headroom" wording (available swing = VREF and VDD−VREF) explicit in the
  chapter — fed the A3 item.

---

## Sprint 3 (completed) — Review & Retrospective

**Increment (A3, doD met):**
- `book/0005-one-analog-neuron/headroom_neuron.py` — virtual-ground error vs
  open-loop gain + rail-headroom report; `diagrams/virtual_ground.svg`.
- pytest `test_neuron_virtual_ground_and_headroom` (auto-skip without engine).

**Sprint Review (demo summary):**
- Virtual-ground error: Aol 1e4 → 0.37 mV; Aol 1e3 → 3.74 mV (scales 1/Aol).
- Rail headroom up = down = 2.5 V; gnd-reference headroom down = 0 (clips).

**Retrospective — what went well / to improve:**
- Well: A3 cleanly reuses A1/A2; the 1/Aol error scaling is a nice, physical
  teaching point.
- Improve: next, 0005 still lacked concrete breadboard/BOM/test-point
  deliverables — fulfilled by A4 (Sprint 4).

---

## Sprint 4 (completed) — Review & Retrospective

**Increment (A4, doD met):**
- Build files for 0005: `bom.csv`, `breadboard.md`, `testpoints.md`,
  `calibration.md`, `diagrams/full_schematic.svg`; data-file pytest
  (`tests/test_chapter_files.py`, no engine). Chapter EN + VI updated.

**Sprint Review:** all build data present and machine-checked; closes 0005's
concrete-deliverable gap (a physical build + measurements remain).

**Retrospective — what went well / to improve:**
- Well: A4 closes 0005's deliverable gap; no-engine data test keeps DoD
  measurable.
- Improve: the only remaining 0005 step is a real build + `measurements.csv`
  (needs hardware).

---

## Sprint 5 (completed) — Review & Retrospective
Goal: scale one neuron into a **layer of many neurons** (10/100/1000).

| Id | Item | Size | Status |
|---|---|---|---|
| A5 | Chapter 0006: many neurons | M | **done** |

### Sprint 5 — Review & Retrospective

**Increment delivered (doD met):**
- `book/0006-many-neurons/layer_neuron.py` — numpy layer for N=10/100/1000,
  tiled via `analog_llm.Accelerator`, matching float (~6e-4); reports
  cells/MACs/tiles ledger; writes `diagrams/growth.svg`.
- `book/0006-many-neurons/layer_neuron_spice.py` — 2-neuron layer on one LM358
  (shared 2.5 V reference) verified in SPICE.
- pytest `tests/test_layer.py` (numpy, always) + optional 2-neuron SPICE test;
  chapter 0006 README (EN + VI).

**Sprint Review (demo summary):**
- cells/MACs scale linearly: N=10→160, N=100→1600, N=1000→16000.
- 2-neuron SPICE: both outputs 2.3496 vs ideal 2.3500 (err 4e-4).
- Key insight: "many neurons" == "a matrix" == "a crossbar" (bridge 0001→0005→0006→analog_llm).

**Retrospective — what went well / to improve:**
- Well: A5 reuses `analog_llm` (Accelerator) and 0005's summer pattern, so it
  tied the book's neuron view to the simulator's tile view in one step.
- Improve: next, run the same scaling through `analog_llm` delib (B-series:
  B1 bit sweep, B3 multi-tile demo) to finish the simulator milestones.

---

## Current Sprint — Sprint 6
Goal: quantify the **accuracy-vs-cost** trade-off of the simulator (ROADMAP M4).

| Id | Item | Size | Status |
|---|---|---|---|
| B1 | Bit sweep: accuracy-vs-cost | S | **done** |

## Sprint 6 — Review & Retrospective

**Increment delivered (doD met):**
- `scripts/bit_sweep.py` — sweeps `g_bits` and `adc_bits`, reports token
  agreement + max logit error vs cost; guardrails; writes `bit_sweep_g.svg` /
  `bit_sweep_adc.svg`.
- pytest `tests/test_bit_sweep.py` (always runs); ROADMAP M4 bit-sweep `[x]`.

**Sprint Review (demo summary):**
- g_bits: 2→0.391, 4→0.237, 6→0.021, 8+→~0.007 (clear knee; more bits cost,
  buy less).
- adc_bits: needs ≥10 for low error; below is noisy (~0.3–0.5).
- Conclusion: conductance resolution (g_bits) is the dominant, cheapest-to-fix
  lever; converter bits matter above a floor.

**Retrospective — what went well / to improve:**
- Well: quick win closing M4; the knee curve is a concrete, honest
  accuracy-vs-cost result (no energy claim).
- Improve: next, B2 (per-non-ideality ablation) to attribute the error to each
  source, and B3 (multi-tile demo) to close M2.

---

## Current Sprint — Sprint 7
Goal: attribute the budget-config logit error to each non-ideality (ROADMAP M4).

| Id | Item | Size | Status |
|---|---|---|---|
| B2 | Per-non-ideality ablation | S | **done** |

## Sprint 7 — Review & Retrospective

**Increment delivered (doD met):**
- `scripts/ablation.py` — leave-one-out ablation over 7 non-idealities
  (g_bits, dac_bits, adc_bits, noise, gain, offset, clipping), reports each
  one's contribution + share to max logit error; guardrails; `ablation.svg`.
- pytest `tests/test_ablation.py` (always); ROADMAP M4 ablation `[x]`.

**Sprint Review (demo summary):**
- ideal (all off) logit_err 0.0002, agreement 1.000; budget (all on) 0.516.
- Dominant standalone contributors (budget config, n_embd 32):
  ADC bits 25.8% > offset 24.7% > noise 17.6% ≈ weight bits 17.6% > clipping 14.4%;
  DAC bits and gain error ~0 here (not the binding constraint).
- One-at-a-time shares sum >100% because non-idealities interact → reported as
  standalone attribution, not a strict partition (honest framing).
- Modeling insight: `vout_max` trades off against ADC resolution (larger range
  => coarser step), so "clipping" is only cleanly isolated at enough headroom.

**Retrospective — what went well / to improve:**
- Well: closes M4 with a concrete, honest error attribution; the
  offset>noise>bits ordering is actionable for a design.
- Improve: next, B3 (multi-tile demo, ROADMAP M2) — a matrix larger than one
  tile with the physical ledger (tile_count > 1).

---

## Current Sprint — Sprint 8
Goal: demonstrate and ledger a matrix larger than one physical tile (ROADMAP M2).

| Id | Item | Size | Status |
|---|---|---|---|
| B3 | Multi-tile demo | M | **done** |

## Sprint 8 — Review & Retrospective

**Increment delivered (doD met):**
- `scripts/multi_tile_demo.py` — 24x16 matrix over 8x8 tiles (6 blocks), runs
  parallel (tile_count=6) and temporal-reuse (tile_count=2) scenarios, reports
  the physical ledger and checks both against the dense reference.
- `multi_tile_layout.svg`; pytest `tests/test_multi_tile.py` (always); ROADMAP
  M2 multi-tile demo `[x]`.

**Sprint Review (demo summary):**
- Ledger (same 384-MAC matrix):
  parallel  -> 6 tiles, cycles 1, rewrites 0;
  reuse     -> 2 tiles, cycles 3, rewrites 4.
- Both match dense within 5.4e-4; MACs identical (independent of tile_count).
- Insight: adding tiles cuts latency lower-bound (cycles) but never the work
  (MACs); the trade-off is silicon vs timing, shown as honest ledger numbers.

**Retrospective — what went well / to improve:**
- Well: closes M2's demo item with a concrete ledger contrast (parallel vs
  temporal reuse) that is honest about the MAC-vs-cycles trade.
- Improve: M2's remaining "multi-tile parallelism / temporal-reuse scheduler
  analysis" is analysis-heavy; pair it with M3's per-token trace (B6) once
  wanted, or start M5 (real pretrained weights).

---

## Current Sprint — Sprint 9
Goal: remove redundant per-step context recompute in generation (ROADMAP M3).

| Id | Item | Size | Status |
|---|---|---|---|
| B5 | KV-cache path | M | **done** |

## Sprint 9 — Review & Retrospective

**Increment delivered (doD met):**
- `TinyGPT._step` + `TinyGPT.generate_kvcache` — per-layer K/V cache; each new
  token runs a single-position forward reusing cached keys/values.
- `scripts/kv_cache_demo.py` (+ `kv_cache.svg`); pytest `tests/test_kv_cache.py`
  (always); ROADMAP M3 KV-cache `[x]`.

**Sprint Review (demo summary, P=5, G=6):**
- Attention query-rows: no-cache 45 vs with KV-cache 11 → **4.09x** reduction
  (logical-work ledger, not wall-clock/energy).
- Greedy and sampling output **identical** to the no-cache baseline (same math).

**Retrospective — what went well / to improve:**
- Well: a clean, honest efficiency change — same tokens, fewer forward rows.
- Improve: B6 (per-token ledger trace) can now show KV-cache reuse in the
  per-token MAC/cycle trace; the remaining M2 scheduler analysis can ride on it.

---

## Current Sprint — Sprint 10
Goal: trace the physical ledger per generated token through a full layer,
contrasting no-KV and KV-cache paths (ROADMAP M3).

| Id | Item | Size | Status |
|---|---|---|---|
| B6 | Per-token ledger trace | S | **done** |

## Sprint 10 — Review & Retrospective

**Increment delivered (doD met):**
- `scripts/token_trace.py` — for each generated token, captures the
  accelerator ledger delta (MACs / tile-cycles / rewrites) of a full-layer
  forward, for both the no-KV (full-context) and KV-cache (single-position)
  paths; writes `token_trace.svg`.
- pytest `tests/test_token_trace.py` (always); ROADMAP M3 per-token ledger
  trace `[x]` (latency sub-part deferred to M6 as it needs measured timing).

**Sprint Review (demo summary, 2L/64D/4H, tile 32x32 x4, P=4):**
- Per-token no-KV MACs grow linearly with context: token 0 -> 425,984 … token 4
  -> 851,968 (each step +106,496 = one position).
- KV-cache single-position forward is constant: 106,496; at ctx 8 that is 8.0x
  fewer MACs than the no-KV full forward.
- The trace makes the B5 redundancy visible per token (tile-MVM work only,
  not digital softmax/scores).

**Retrospective — what went well / to improve:**
- Well: B6 makes the KV-cache efficiency concrete per token and reuses the
  Accelerator ledger as-is (M2/M3 tie).
- Improve: remaining work is M1 g_bits-vs-error curve, M3 per-token latency
  (needs M6 timing assumptions), and M5 (real pretrained weights).

---

## Current Sprint — Sprint 11
Goal: run a real pretrained GPT-2 through the simulator with parity and an
accuracy-vs-baseline table (ROADMAP M5).

| Id | Item | Size | Status |
|---|---|---|---|
| M5 | Real pretrained weights | L | **done** |

## Sprint 11 — Review & Retrospective

**Increment delivered (doD met):**
- `analog_llm/gpt_loader.py` — safetensors loader mapping HuggingFace GPT-2
  tensors into `TinyGPT` (Conv1D `[in,out]` -> `[out,in]` transpose, head tied
  to wte, block_size slice, fail-closed).
- `analog_llm/reference_gpt2.py` — independent pure-numpy reference forward;
  `analog_llm/tokenizer.py` — minimal byte-level BPE tokenizer.
- `scripts/run_real_model.py` — runs the real trained tiny GPT-2
  (`pszemraj/tiny-gpt2-magicprompt`, ~4 MB) through the accelerator; checkpoint
  cached under `data/gpt2-tiny`.
- pytest `tests/test_gpt_loader.py` + `tests/test_tokenizer.py`; ROADMAP M5
  items closed.

**Sprint Review (demo summary):**
- Numeric parity between `load_gpt2` forward and the independent reference is
  **exact (0.0)** on the real checkpoint (validates transpose/tying mapping).
- Full-sequence through the accelerator (tile 1024x8 x4): high-precision
  matches float exactly (agreement 1.000, logit err 0.0001); budget config
  degrades (agreement 0.385) and flips all 8 generated positions (failure
  analysis).
- Real encoded prompt: "Once upon a time," -> "… time, stairs stairs …"
  (tiny model loops; honest).

**Retrospective — what went well / to improve:**
- Well: a genuine open checkpoint now runs end-to-end with exact mapping
  parity; the independent reference caught a real residual-add bug.
- Improve: M1 g_bits-vs-error curve and M3 per-token latency (via M6 timing)
  remain; also consider a larger real model for a less degenerate demo.

---

## Current Sprint — Sprint 12
Goal: publish the weight-side accuracy-vs-cost curve (ROADMAP M1).

| Id | Item | Size | Status |
|---|---|---|---|
| M1 | g_bits vs effective-weight error curve | S | **done** |

## Sprint 12 — Review & Retrospective

**Increment delivered (doD met):**
- `scripts/gbits_sweep.py` — sweeps `g_bits` (2..14) over a dense+random weight
  grid in [-1,1], reports max |w - w_eff| normalized by the conductance span
  (as the tile does), writes `gbits.svg`.
- pytest `tests/test_gbits_sweep.py` (always); ROADMAP M1 sweep item `[x]`.

**Sprint Review (demo summary):**
- Measured max effective-weight error **exactly matches** the analytic bound
  `1/(2 (2^g_bits - 1))` and falls geometrically: 2b->0.167, 4b->0.0333,
  6b->0.00794, 8b->0.00196, 10b->0.00049.
- Modeling note: the raw error plateaus at `gmin` (=0.05) due to a DC offset
  (`w=1` -> `G+ - G- = gmax-gmin`); the tile absorbs it by the span
  normalization, so the resolution (quantization) error is what scales 2^-g_bits.

**Retrospective — what went well / to improve:**
- Well: closes M1 with a clean closed-form result; the gmin-offset vs
  quantization distinction is a useful, honest modeling point.
- Improve: the remaining milestone is M6 (energy/latency with measured-only
  assumptions) and M3 per-token latency (depends on M6 timing); the roadmap's
  simulator milestones are otherwise complete.

---

## Current Sprint — Sprint 13
Goal: close the roadmap with a system latency/energy estimate from measured-
input assumptions only (ROADMAP M6), with no GPU comparison.

| Id | Item | Size | Status |
|---|---|---|---|
| M6 | Energy / latency estimate | M | **done** |

## Sprint 13 — Review & Retrospective

**Increment delivered (doD met):**
- Ledger extended with tile **programs** (`Accelerator.programs`,
  `Metrics.programs`, shown in `report.format_report`).
- `analog_llm/latency.py` — explicit latency/energy formula from designer
  assumptions (relative units tu/eu), with validation and a disclaimer that
  nothing is measured and there is no GPU comparison.
- `scripts/energy_latency.py` (+ `latency_sensitivity.svg`) — converter /
  program / reuse accounting and the sensitivity of the latency estimate to
  tile parallelism and capacity.
- pytest `tests/test_latency.py`; ROADMAP M6 items closed.

**Sprint Review (demo summary, 1L/48D workload, 48x48 tile):**
- Accounting: 192 converters on board (2x 48 DACs + 48 ADCs), 56 tile programs
  (20 reuse), latency est. 43.2 tu (32 MVM-cycles + 11.2 program-time).
- Parallelism: tile_count 1->8 lowers cycles 56->20 and latency 67.2->31.2 tu
  but adds converters; latency plateaus once cycles floor at 20 (parallelism
  saturated => more tiles buy nothing).
- Capacity: 16->64 tile cuts programs 480->44 and latency 340->40.8 tu.
- Energy only shown because per-op values were supplied as assumptions; units
  relative, labelled not measured, no GPU comparison.

**Retrospective — what went well / to improve:**
- Well: closes M6 (and thus all simulator milestones) with an explicit,
  assumption-labelled formula that never claims a real speed/energy/GPU result.
- Improve: real numbers need actual silicon timing/energy measurements and a
  committed ledger; D1 (CI circuit sim job) remains for the book track.

---

## Current Sprint — Sprint 14
Goal: close the last backlog item — an optional CI job that runs the SPICE
circuit sims when ngspice is available (or skips cleanly).

| Id | Item | Size | Status |
|---|---|---|---|
| D1 | CI runs circuit sim when ngspice available | S | **done** |

## Sprint 14 — Review & Retrospective

**Increment delivered (doD met):**
- `.github/workflows/ci.yml` adds an optional `circuit-sim` job: installs
  `ngspice` (best-effort, `|| true`), installs `.[dev,sim]`, and runs
  `pytest tests/test_circuit_sim.py`. The SPICE tests auto-skip when PySpice or
  the ngspice shared library is missing (already the case), so the job stays
  green either way.
- ROADMAP/BACKLOG: the numeric backlog (A1-A5, B1-B6, M1-M6, D1) is now fully
  closed.

**Sprint Review:** the sim scripts' loader auto-detects
`/usr/lib/x86_64-linux-gnu/libngspice.so` on Linux (see `sim_neuron.py`), so an
Ubuntu runner with `ngspice` installed runs the 0005/0006 SPICE assertions, and
a runner without it skips them rather than failing.

**Retrospective — what went well / to improve:**
- Well: closes the last backlog item; CI now covers both the numpy suite and
  (optionally) the SPICE book track with a clean skip path.
- Improve: there is intentionally no platform with a measured silicon ledger
  yet; the whole roadmap remains a simulator until physical measurements exist.

---

## Current Sprint — Sprint 15
Goal: close the last four roadmap items — honest-framing guardrails (M4, M0)
and the two analysis items (M2 scheduler, M3 per-token latency est.).

| Id | Item | Size | Status |
|---|---|---|---|
| M4 | GPU-equivalence guardrail | S | **done** |
| M0 | Freeze error-budget + reporting format | S | **done** |
| M2 | Multi-tile / temporal-reuse scheduler analysis | S | **done** |
| M3 | Per-token latency trace (est., M6 model) | S | **done** |

## Sprint 15 — Review & Retrospective

**Increment delivered (doD met):**
- `analog_llm/guardrail.py` + `tests/test_guardrail.py` — rejects performance
  claims (faster-than / GPU-equivalent / O(1) compute·energy·latency) in code
  and reports; disclaimers ("no GPU comparison") pass; scans our .py tree.
- `docs/PRODUCT_SPEC.md` §8 — frozen v0.1 reporting format (accuracy + ledger +
  invariants); `tests/test_report_format.py` pins `format_report` fields.
- `docs/TILING.md` + `tests/test_tiling_analysis.py` — block decomposition,
  linear-scan schedule, `cycles = ceil(blocks/T)`, `rewrites = max(0, blocks-T)`,
  programming cost formula; verified against the accelerator.
- `scripts/token_trace.py` now prints a per-token latency estimate (relative
  `tu` from the M6 model) next to the ledger.
- ROADMAP M0/M2/M3/M4 items closed; the roadmap is now fully checked.

**Sprint Review (per-token latency est., P=4, tile 32x32 x4):**
- no-KV per-token latency grows with context: 187.2 -> 374.4 tu.
- KV single-position is constant 46.8 tu (8.0x lower at ctx 8).

**Retrospective — what went well / to improve:**
- Well: the roadmap is now fully complete, and the guardrail makes the
  "honest framing" rule an enforceable check rather than a guideline.
- Improve: everything remains a simulator; producing a real physical ledger
  (silicon or a real SPICE build with `measurements.csv`) is the only
  meaningful next step.
