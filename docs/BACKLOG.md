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

### B1 — Bit sweep: accuracy-vs-cost with the simulator  `[S]`
**As a** designer, **I want** a `scripts/bit_sweep.py` that sweeps
`g_bits`/`adc_bits` and reports the accuracy-vs-cost curve.
**AC:** a runnable script + a small report; closes ROADMAP M4.

### B2 — Per-non-ideality ablation  `[S]`
**AC:** toggle each non-ideality independently and report each one's
contribution to logit error.

### B3 — Multi-tile demo  `[M]`
**AC:** a demo runs a matrix larger than one physical tile and reports the
ledger with `tile_count > 1`; closes ROADMAP M2.

### B5 — KV-cache path in the transformer  `[M]`
**AC:** generation no longer recomputes full context each step.

### B6 — Per-token ledger trace  `[S]`
**AC:** a report traces MACs/cycles per generated token through a layer.

### D1 — CI runs the circuit sim when ngspice is available  `[S]`
**AC:** CI's optional job exercises `sim_neuron*.py` (or skips cleanly).

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

## Current Sprint — Sprint 4
Goal: give chapter 0005 **concrete build files** so it is breadboardable.

| Id | Item | Size | Status |
|---|---|---|---|
| A4 | Breadboard wiring + BOM + test points | M | **done** |

## Sprint 4 — Review & Retrospective

**Increment delivered (doD met):**
- `bom.csv`, `breadboard.md`, `testpoints.md`, `calibration.md`,
  `diagrams/full_schematic.svg` — full single-supply LM358 build (2.5 V
  reference buffer + inverting summer, w = [0.50, 0.25]).
- data-file pytest `tests/test_chapter_files.py` (validates BOM/docs/SVGs,
  no engine required); chapter 0005 (EN + VI) updated with a "Build files"
  section and status.

**Sprint Review (demo summary):**
- All build data files present and machine-checked; designators consistent
  (`U1`); BOM = 12 lines.
- This satisfies the last "design-only" gap in 0005 aside from an actual
  physical build + measurements.

**Retrospective — what went well / to improve:**
- Well: A4 closes chapter 0005's concrete-deliverable gap; the no-engine
  data test keeps DoD measurable without ngspice.
- Improve: the only remaining 0005 step is a **real build + `measurements.csv`**
  (physical evidence), which needs hardware — a new non-sim sprint (or
  acceptance by a builder).
