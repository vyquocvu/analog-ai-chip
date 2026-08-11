# Roadmap — Analog AI Machine

This roadmap tracks **implementation readiness**, not topic coverage. `docs/CURRICULUM.md` defines the canonical learning/design sequence; this file defines which evidence gate is active and what must be proven before higher-level work becomes eligible.

## Governing rule

```text
math/reference
    ↓
circuit/SPICE
    ↓
validated device profile
    ↓
profile-driven tile
    ↓
accelerator
    ↓
Transformer / LLM
    ↓
physical feasibility
```

A higher gate may contain exploratory code, but it is not considered physically verified until all lower gates it depends on are closed.

Evidence classes remain: `measured`, `spice`, `derived`, `assumed`. `assumed` is allowed for sensitivity studies but cannot support a verified physical claim.

---

## R0 — Functional and circuit foundation — COMPLETE

### Proven

- [x] Matrix convention, ideal MVM and deterministic reference arithmetic
- [x] Differential `G+ / G-` signed-weight mapping
- [x] Behavioral quantization/noise and explicit tiling/partial sums
- [x] 0005 voltage-mode weighted-sum neuron verified in ngspice/PySpice
- [x] 0005 finite-gain/offset/rail/headroom studies
- [x] 0006 many-neuron scaling ledger and small SPICE check
- [x] 0007 current-mode differential crossbar column
- [x] 0007 TIA/differential readout agrees with hand calculation (`~1e-4 V` reported chapter error)
- [x] Device-profile schema, evidence classes and fail-closed validator exist
- [x] Measurement capture/checking workflow exists for 0005; actual hardware readings remain optional/pending

### Important limitation

The repository has circuit evidence and a profile contract, but the two are not yet connected. `device_profiles/` still contains only the ideal reference profile, so the architecture simulator is not yet driven by extracted SPICE evidence.

**Exit status:** complete as a foundation, not complete as a physical product claim.

---

# R1 — Close the circuit → profile → simulator proof chain — ACTIVE

This is the only next-ready physical-verification milestone.

### WP1.1 — Extract first SPICE-backed profile

- [ ] Define machine-readable extraction outputs for 0005 and 0007
- [ ] Extract voltage/current gain, output range/headroom, offset/error and relevant settling/timing values when supported by the circuit model
- [ ] Create a versioned profile such as `device_profiles/crossbar-column-v1.json`
- [ ] Record simulator/backend, source chapter/netlist/script, supply, reference voltage, model assumptions and commit provenance
- [ ] Mark every field `spice`, `derived`, `measured`, or `assumed`

### WP1.2 — Consume the profile downstream

- [ ] Add profile → `analog_llm` configuration adapter
- [ ] Remove or explicitly label duplicate physical constants that currently bypass profile provenance
- [ ] Add deterministic tests showing the same profile produces the same tile/system configuration
- [ ] Fail closed when required physical fields are missing or only functional-only evidence is supplied

### WP1.3 — Verification summary

- [ ] Generate a machine-readable verification summary (JSON) plus readable report
- [ ] Report evidence coverage by component and claim level
- [ ] Separate `VERIFIED_BY_SPICE`, `DERIVED`, `ASSUMED`, `MEASUREMENT_PENDING`
- [ ] Link report values back to source profile/evidence artifacts

### Gate R1 exit

A single end-to-end test must demonstrate:

```text
0007 SPICE evidence
      ↓ extraction
validated crossbar-column profile
      ↓ adapter
analog_llm tile/system configuration
      ↓
reproducible verification report
```

No manual copy-paste of physical constants is allowed in the proof path.

---

# R2 — Converter signal path — QUEUED

Eligible only after R1 closes.

## 0009 — DAC architecture

- [ ] Choose a first design candidate (baseline recommendation: simple R-2R or explicit behavioral-to-transistor progression)
- [ ] Hand reference for code → voltage transfer
- [ ] ngspice DC sweep across all codes for a small-bit prototype
- [ ] Transient settling study
- [ ] Gain/offset/range extraction
- [ ] Supply sensitivity
- [ ] Monte Carlo / resistor mismatch where supported
- [ ] Publish `dac-v1` SPICE profile

## 0010 — ADC / TIA output path

- [ ] Define first ADC/output-stage architecture and input envelope
- [ ] Transfer/clipping characterization
- [ ] Settling/conversion timing model
- [ ] Noise/effective-resolution study appropriate to model detail
- [ ] Supply/temperature/corner study where supported
- [ ] Publish `adc-v1` SPICE profile

## 0011 — Converter variation

- [ ] Monte Carlo mismatch distributions
- [ ] Separate gain, offset, quantization, noise and non-linearity mechanisms
- [ ] Define calibration candidates

### Gate R2 exit

`analog_llm` can run with converter parameters sourced from validated DAC/ADC profiles rather than arbitrary normalized defaults.

---

# R3 — Small crossbar arrays — QUEUED

Depends on R1; R2 is required for full signal-path claims but not for early array-only studies.

## 0012 — 2×2 differential crossbar

- [ ] Shared input rows, two independent output columns
- [ ] SPICE MVM versus hand/NumPy reference
- [ ] Signed-weight cases, zero/balanced cases and boundary envelope
- [ ] Output-stage loading/headroom checks

## 0013 — 4×4 differential crossbar

- [ ] Scale the validated 2×2 topology
- [ ] Compare SPICE output to behavioral model over deterministic vectors/matrices
- [ ] Quantify max/RMS MVM error
- [ ] Record current and settling behavior

## 0014 — Array timing/loading

- [ ] Sweep number of rows/columns
- [ ] Quantify TIA loading and headroom
- [ ] Establish the point where ngspice becomes impractical and Xyce becomes preferred

### Gate R3 exit

A 4×4 current-mode differential array has reproducible SPICE evidence and a behavioral-equivalence error report.

---

# R4 — Device realism and crossbar-v1 — QUEUED

Depends on R3.

- [ ] Select explicit programmable-conductance abstraction / compact model
- [ ] Establish `gmin`, `gmax`, state count/resolution and programming assumptions
- [ ] Programming/read variation Monte Carlo
- [ ] IR-drop / line resistance versus array dimensions
- [ ] Parasitic RC and settling
- [ ] Drift, stuck states and non-linearity where supported
- [ ] Temperature/process/model corners where meaningful
- [ ] Publish `crossbar-v1` profile with limitations

### Gate R4 exit

Every crossbar non-ideality used by the architecture simulator traces to a named model/evidence source or is explicitly marked assumed.

---

# R5 — Profile-driven physical tile — QUEUED

Depends on R2 + R4.

- [ ] Tile configuration consumes `dac-v1`, `adc-v1`, `crossbar-v1`
- [ ] Behavioral tile reproduces small-array SPICE cases within a frozen error budget
- [ ] Calibration flow consumes profile evidence
- [ ] Partial-sum precision and clipping rules are explicit
- [ ] Freeze tile-level validation report

### Gate R5 exit

The tile simulator is a calibrated abstraction of the proposed circuit/device stack, not an independent collection of hand-chosen parameters.

---

# R6 — Accelerator architecture and data movement — QUEUED

Depends on R5.

Existing functional work (tiling, multi-tile demo, ledgers, KV cache) is useful evidence but must be revalidated with profile-driven timing/error parameters.

- [ ] Freeze tile parallelism / temporal-reuse scheduler
- [ ] SRAM/buffer capacity model
- [ ] NoC/interconnect traffic model
- [ ] Profile-derived converter/tile timing in per-token trace
- [ ] Programming/rewrite costs
- [ ] End-to-end architecture ledger with provenance

### Gate R6 exit

For any layer, the simulator can state where time, storage, traffic, rewrites and error come from.

---

# R7 — Transformer and LLM validation — QUEUED

Depends on R6.

Existing TinyGPT, checkpoint loader, KV cache, ablations and real-model mapping are functional foundations.

- [ ] Re-run linear/MLP/QKV mappings with R5/R6 physical profiles
- [ ] Explicit analog/digital boundary report for attention
- [ ] Full transformer-block error attribution
- [ ] Tiny transformer profile-driven parity/error study
- [ ] Real pretrained checkpoint using physical profiles
- [ ] Hardware-aware calibration/training recovery experiment

### Gate R7 exit

Model accuracy degradation is attributable to named circuit/device/architecture mechanisms rather than generic noise knobs.

---

# R8 — Physical feasibility report — QUEUED

Depends on R7 and evidence from R2–R6.

- [ ] Latency model with evidence-tagged timing coefficients
- [ ] Energy/power model with evidence-tagged coefficients
- [ ] Area model with explicit topology/process/layout assumptions
- [ ] Thermal/power-density sanity checks
- [ ] Sensitivity ranges for all still-assumed parameters
- [ ] No GPU/ASIC superiority claim without comparable measured evidence
- [ ] Generate integrated feasibility report

The strongest status available without fabricated hardware is:

**SIMULATION-BACKED PHYSICAL FEASIBILITY**

not silicon verification.

---

# R9 — Implementation correlation — FUTURE

- [ ] FPGA/digital-shell prototype for scheduler/buffer/control
- [ ] KiCad board/reference circuits when useful for correlation
- [ ] Replace SPICE evidence with measured profiles where hardware exists
- [ ] SPICE-vs-measured correlation report
- [ ] Define PDK/layout/device requirements for any IC exploration
- [ ] Tape-out readiness review only after required evidence exists

---

## Work-selection rule

When choosing the next task:

1. Select the first incomplete work package in the **Active** gate whose dependencies are proven.
2. Do not implement a queued physical claim merely because higher-level functional code already exists.
3. One PR should close one meaningful vertical slice with deterministic evidence.
4. If a required simulator/model is unavailable, record the blocker; do not replace missing evidence with a silent assumption.
5. Update this roadmap only after the evidence exists in the repository.
