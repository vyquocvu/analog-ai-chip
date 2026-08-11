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

# R1 — Close the circuit → profile → simulator proof chain — COMPLETE

The circuit → profile → simulator chain is closed with SPICE-backed evidence and a
reproducible verification report.

### WP1.1 — Extract first SPICE-backed profile

- [x] Define machine-readable extraction outputs for 0005 and 0007: `verification/circuit/extract_crossbar_column.py` emits `verification/circuit/results/crossbar-column-v1-extract.json` (raw measurements) and `device_profiles/crossbar-column-v1.json`
- [x] Extract voltage/current gain, output range/headroom, offset/error: transimpedance gain `10020 ohm` and gain `0.9995 V/V per weight` (`spice`), max `|SPICE - hand calc|` `8.0e-4 V` over 5 deterministic cases (`spice`), headroom `±2.5 V` derived from `VDD=5 V`/`VREF=2.5 V` (`derived`); settling not extracted — DC OP-only model, documented as limitation
- [x] Create a versioned profile: `device_profiles/crossbar-column-v1.json` (name `crossbar-column-v1`, version `0.1.0`)
- [x] Record simulator/backend, source chapter/netlist/script, supply, reference voltage, model assumptions and commit provenance, in `provenance` (`ngspice` via PySpice, `op`, sources, command, conditions `{supply_v: 5.0, vref_v: 2.5}`, limitations)
- [x] Mark every field `spice`, `derived`, `measured`, or `assumed`: all 10 fields carry per-field `evidence_class`; validator `_validate_fields` enforces this and fails closed on missing/invalid/`assumed` field evidence for physical claims

### WP1.2 — Consume the profile downstream

- [x] Add profile → `analog_llm` configuration adapter: `analog_llm/profile_adapter.py` maps validated profile `fields` to `CrossbarTile` kwargs (`gmin = g0_s`, `gmax = g0_s + gscale_s_per_w`, envelopes from rail headroom) and legacy `dac/crossbar/adc` sections for the functional reference; exposed via `build_tile_factory`/`tile_config_from_profile`
- [x] Remove or explicitly label duplicate physical constants that currently bypass profile provenance: `scripts/run_llm_sim.py` now builds tiles only through the adapter (SPICE profile for the physical run, `ideal.json` for the functional run); `CrossbarTile`/`map_differential` docstrings label their defaults as functional reference values mirrored by `device_profiles/ideal.json`
- [x] Add deterministic tests showing the same profile produces the same tile/system configuration: `tests/test_profile_adapter.py` and `tests/test_profile_consumer.py` (identical config from repeated calls, identical tile forward outputs, identical TinyGPT token sequences with fixed seeds)
- [x] Fail closed when required physical fields are missing or only functional-only evidence is supplied: missing `REQUIRED_FIELDS` -> `ValueError`; `ideal.json` cannot drive a physical tile (`assumed`/`FUNCTIONAL_ONLY`); bits must be explicit

### WP1.3 — Verification summary

- [x] Generate a machine-readable verification summary (JSON) plus readable report: `verification/reports/generate_crossbar_column_summary.py` emits `crossbar-column-v1-summary.json` (machine-readable) and `crossbar-column-v1-summary.md` (readable); deterministic, no timestamps, reads only committed artifacts
- [x] Report evidence coverage by component and claim level: JSON `coverage` gives counts per bucket and per component (`readout`, `differential_mapping`, `conductance_cell`, `rail_headroom`) plus separate `circuit/device` vs `system` claim levels
- [x] Separate `VERIFIED_BY_SPICE`, `DERIVED`, `ASSUMED`, `MEASUREMENT_PENDING`: 3 `VERIFIED_BY_SPICE` (transimpedance gain, unit-weight gain, dc error), 7 `DERIVED`, 0 `ASSUMED` in circuit/device; system-level `assumed` bits are explicit programming choices; pending items (hardware readout, transient settling, noise/temperature/Monte Carlo) listed explicitly
- [x] Link report values back to source profile/evidence artifacts: every evidence entry carries `source` pointing at `device_profiles/crossbar-column-v1.json#/fields/<name>`; `_crosscheck` fails closed if any profile value diverges from the raw extract result; tile config is produced by `profile_adapter`, not hand-copied

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

R1 gate evidence: `tests/test_verification_summary.py` — 9 always-on tests prove the
committed profile matches the extract, the adapter derives the tile config from profile
fields, the summary is deterministic, every value links back to its profile artifact,
the generator writes the committed JSON/markdown, and functional-only profiles fail
closed. R1 is complete (WP1.1 + WP1.2 + WP1.3 closed).

---

# R2 — Converter signal path — ACTIVE

R1 is closed; the first DAC slice (below) is eligible.

## 0009 — DAC architecture

- [x] Choose a first design candidate: R-2R ladder (`book/0009-dac-r2r/r2r_dac.py`, single source of truth for SPICE solves) — two resistor values `R`/`2R` + `VREF`, no exotic components
- [x] Hand reference for code → voltage transfer: `Vout(code) = VREF*code/2^N` encoded as `ideal_output` and asserted against SPICE for all 16 codes
- [x] ngspice DC sweep across all codes for a small-bit prototype: 4-bit ladder, all 16 codes, worst `|SPICE − hand calc|` `4.44e-16 V` (`spice`)
- [x] Transient settling study: single-pole hand model `t = 2R·CL·ln(ΔV/band)` vs SPICE transient, `Rth = 2R` from two-point DC load line (`spice`); settling reported as an ASSUMED-`CL` sensitivity study in the extract JSON only (1 pF load, 0.5 LSB band, full-scale step: SPICE 68.7 ns vs hand 68.0 ns) and deliberately excluded from the profile so `physical_claim` stays valid
- [x] Gain/offset/range extraction: `lsb_v = 0.15625 V/code`, `full_scale_v = 2.34375 V`, `offset_v = 0 V`, `gain_v_per_v = 1`, `max_inl_v = 4.4e-16 V`, `max_dnl_v = 4.2e-16 V` (`spice`)
- [ ] Supply sensitivity (deferred)
- [ ] Monte Carlo / resistor mismatch (deferred)
- [x] Publish SPICE profile: `device_profiles/dac-r2r-v1.json` (name `dac-r2r-v1`, version `0.1.0`), 11 fields all carrying `evidence_class` (incl. `rth_ohm = 20000 ohm`, `spice`), emitted by `verification/circuit/extract_dac_r2r.py`

## 0010 — ADC / TIA output path

- [x] Define first ADC/output-stage architecture and input envelope: 4-bit SAR ADC with the 0009 R-2R ladder as internal reference and a VCVS comparator (`book/0010-adc-sar/sar_adc.py`); input front `Vin = VREF/2 + Vdiff/2` maps the TIA differential `±2.5 V` envelope (crossbar-column-v1 headroom, derived) onto the ladder's unipolar `[0, VREF]`
- [x] Transfer/clipping characterization: hand `code = floor(Vin/LSB)` clipped to `[0, 15]`; SPICE comparator decision == hand `Vin >= Vref(code)` on representative trials; 129-sample transfer sweep reproduces the hand code at every point (worst deviation 0 codes); differential-domain quantization bound `LSB = 0.15625 V` (front gain 1/2 doubles the unipolar LSB/2 bound)
- [x] Settling/conversion timing model: R-2R reference settles as `τ = 2R·CL` (`spice` matches single-pole hand within 10 ns per bit trial); SAR conversion time = sum over 4 bit trials of worst-case reference steps, SPICE `140.9 ns` vs hand `138.6 ns` at ASSUMED `CL = 1 pF` (sensitivity study only, no device evidence yet)
- [x] Noise/effective-resolution study appropriate to model detail: coherent full-scale sine (`cycles` odd-prime over power-of-two sample count) gives `ENOB = 3.91 bits` vs hand upper bound `4.00`; additive input-referred Gaussian noise (`converters.adc`-compatible) degrades ENOB to `3.46` at `0.05 V` (hand `3.42`); deterministic (seed 7), measured tracks hand within 0.5 bits
- [x] Supply/temperature/corner study where supported: ratio ladder + ideal comparator give a *pure* VREF gain error — SPICE `gain_error = dVREF/VREF` at ±10% within 1e-9; temperature/corner have no modelable effect on ideal models (documented, not fabricated)
- [x] Publish `adc-v1` SPICE profile: `device_profiles/adc-sar-v1.json` from `verification/circuit/extract_adc_sar.py` — SPICE transfer gives `max_code_error_codes = 0` and `max_abs_error_v = LSB` (differential-domain quantization bound); derived design fields (`bits`, `r_ohm`, `vref_v`, `lsb_v`, `input_range_v`, `quantization_error_v`); assumed-CL settling / functional ENOB / supply-deviation studies live in the extract JSON only (fail closed under `physical_claim`); committed extract + always-on/engine-gated tests in `tests/test_adc_sar_profile.py`

## 0011 — Converter variation

- [x] Monte Carlo mismatch distributions: `book/0011-converter-variation/variation.py` — fixed seed draws one set of per-resistor relative mismatch vectors (assumed Gaussian `sigma = 1%`, `R=10k/2R=20k/VREF=2.5/BITS=4`) driving BOTH the mismatched SPICE ladder and an independent NumPy conductance-matrix solver; agreement `2.2e-15 V` over 1024 (sample×code) pairs; statistics (endpoint gain error mean −1.1e-5, std 7.2e-4; max|INL| mean 6.3e-3 V; max|DNL| mean 1.1e-2 V) match the hand solver to 1e-12; `sigma=0` reproduces the ideal ladder (fail-closed); 1-bit closed form `Vout = VREF*a/(a+c)` asserted as the anchor; committed extract `converter-variation-0011-extract.json` + always-on/engine-gated tests (`tests/test_converter_variation.py`); sigma is assumed, so it is a sensitivity study that fails closed under `physical_claim` and publishes no profile
- [x] Separate gain, offset, quantization, noise and non-linearity mechanisms: `book/0011-converter-variation/decomposition.py` — DAC endpoint-fit split `V = offset + slope·code + INL` is exact (`reconstruct_max_v = 0`), SPICE mismatch budget offset `0` / gain mean −1.1e-5 / `max|INL| 1.5e-2 V`; ADC error power separates as `P_total = P_quant(LSB²/12) + P_noise(noise_std²)`, measured tracks hand within sampling tolerance (deterministic, always-on tests in `tests/test_converter_decomposition.py`)
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
