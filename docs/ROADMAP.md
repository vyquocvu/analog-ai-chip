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

A higher gate may contain exploratory code, but it is not considered physically verified until all lower gates it depends on are closed. Evidence classes remain: `measured`, `spice`, `derived`, `assumed`.

---

## Canonical Curriculum & Evidence Gate Mapping

| Gate | Focus | Book Chapters | Status |
|---|---|---|---|
| **R0** | Functional & circuit foundations | `book/0000`–`0004` (Math), `book/0005`–`0007` (Circuit) | **COMPLETE** |
| **R1** | Circuit $\rightarrow$ profile $\rightarrow$ simulator proof chain | `book/0008` (Profile bridge) | **COMPLETE** |
| **R2** | Converter signal path (DAC/ADC/TIA) | `book/0009`–`0011` | **COMPLETE** |
| **R3** | Small crossbar arrays (2×2, 4×4) | `book/0012`–`0014` | **COMPLETE** |
| **R4** | Device realism (variation, IR drop, parasitics, drift) | `book/0015`–`0020` | **COMPLETE** |
| **R5** | Profile-driven physical tile & partial sums | `book/0021`–`0022` | **COMPLETE** |
| **R6** | Multi-tile accelerator, scheduler & NoC | `book/0023`–`0026` | **COMPLETE** |
| **R7** | Transformer mapping & small LLM validation | `book/0027`–`0037` | **PASSED** |
| **R8** | Physical feasibility report (latency/energy/area) | `book/0038`–`0042` | **PASSED** |
| **R9** | Implementation correlation (FPGA/PCB/Tape-out) | `book/0043`–`0045` | **PASSED** |
| **R10** | Scalable model semantics & sharded checkpoints | `book/0046`–`0048` | **PASSED** |
| **R11** | Memory-bounded model execution | `book/0049`–`0051` | **PASSED** |
| **R12** | Large-model architecture & residency | `book/0052`–`0053` | **PASSED** |
| **R13** | Large-model validation & hardware recovery | `book/0054`–`0055` | **PASSED** |
| **R14** | Multi-tier physical feasibility & design decision | `book/0056`–`0058` | **PASSED** |
| **R15** | Physical layout & DRC/LVS verification | `book/0059`–`0062` | **ACTIVE** |
| **R16** | Post-layout extraction & static timing signoff | `book/0063`–`0065` | **QUEUED** |
| **R17** | Tape-out signoff & package/PCB integration | `book/0066`–`0068` | **QUEUED** |

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

# R2 — Converter signal path — COMPLETE

R1 closed the circuit → profile → simulator chain; R2 adds the converter
signal path on top of it. The R-2R DAC (0009) and SAR ADC (0010) are
SPICE-verified and published as profiles (`dac-r2r-v1`, `adc-sar-v1`);
converter variation (0011) separates error mechanisms and defines calibration
candidates; and the gate-exit test proves `analog_llm` runs with converter
parameters sourced from the validated profiles — no normalized converter
default remains.

## 0009 — DAC architecture

- [x] Choose a first design candidate: R-2R ladder (`book/0009-dac-r2r/r2r_dac.py`, single source of truth for SPICE solves) — two resistor values `R`/`2R` + `VREF`, no exotic components
- [x] Hand reference for code → voltage transfer: `Vout(code) = VREF*code/2^N` encoded as `ideal_output` and asserted against SPICE for all 16 codes
- [x] ngspice DC sweep across all codes for a small-bit prototype: 4-bit ladder, all 16 codes, worst `|SPICE − hand calc|` `4.44e-16 V` (`spice`)
- [x] Transient settling study: single-pole hand model `t = 2R·CL·ln(ΔV/band)` vs SPICE transient, `Rth = 2R` from two-point DC load line (`spice`); settling reported as an ASSUMED-`CL` sensitivity study in the extract JSON only (1 pF load, 0.5 LSB band, full-scale step: SPICE 68.7 ns vs hand 68.0 ns) and deliberately excluded from the profile so `physical_claim` stays valid
- [x] Gain/offset/range extraction: `lsb_v = 0.15625 V/code`, `full_scale_v = 2.34375 V`, `offset_v = 0 V`, `gain_v_per_v = 1`, `max_inl_v = 4.4e-16 V`, `max_dnl_v = 4.2e-16 V` (`spice`)
- [x] Supply sensitivity: ratio-based ladder gives a *pure* VREF gain error — SPICE `gain_error = dVREF/VREF` at ±10% within `1e-9`, offset stays `0`, and the deviated transfer matches the hand `VREF'·code/2^N` to `4.4e-16 V`; temperature/corner have no modelable effect on ideal models (documented, not fabricated); extract-only study (`dac-r2r-v1-extract.json#/supply_sensitivity`), not a profile field
- [x] Monte Carlo / resistor mismatch: delivered by 0011 (converter variation) as an assumed-`sigma` sensitivity study that matches an independent NumPy solver to `2.2e-15 V` — it fails closed under `physical_claim` and publishes no profile
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
- [x] Define calibration candidates: `book/0011-converter-variation/calibration.py` — two-point gain+offset (`V_corr = (V−offset)·LSB/slope`, residual = max|INL| on the SPICE study), full transfer LUT (subtract per-code deviation from ideal, residual `0` for static mismatch), and VREF reference trim (design note backed by the 0010 supply-sensitivity `gain_error = dVREF/VREF`); exactness proven on ideal/gain/offset/INL transfers and SPICE draws in `tests/test_converter_calibration.py`

### Gate R2 exit

`analog_llm` can run with converter parameters sourced from validated DAC/ADC profiles rather than arbitrary normalized defaults.

- [x] `converter_config_from_profiles` maps the validated `dac-r2r-v1` / `adc-sar-v1` profile fields to converter parameters (`dac_bits`/`adc_bits`, `vin_max = full_scale_v = 2.34375 V`, `vout_max = input_range_v = 2.5 V`); `build_tile_factory_from_converter_profiles` combines the crossbar-column conductance window with these converter envelopes — no normalized 1.0 converter default remains; fails closed on missing fields and on functional-only profiles; proven end to end by `tests/test_r2_gate_exit.py` (accelerator MVM + deterministic TinyGPT generation + ledger on profile-sourced converters)

---

# R3 — Small crossbar arrays — COMPLETE

Depends on R1 + R2 (both closed). 0012 and 0013 are both delivered with reproducible SPICE evidence and a behavioral-equivalence error report; R3 gate exit is proven (`verification/reports/crossbar-4x4-summary.md`).

## 0012 — 2×2 differential crossbar

- [x] Shared input rows, two independent output columns: both columns driven by the same x0/x1 rails; column independence asserted in SPICE (`|ΔVout_0| = 0` when only column 1 changes)
- [x] SPICE MVM versus hand/NumPy reference: `Vout = RF·GSCALE·(W @ (x − VREF))` over 5 deterministic cases × 2 outputs, worst `|SPICE − hand| 1.0e-3 V` (`book/0012-crossbar-2x2/crossbar_2x2.py`, committed extract `crossbar-2x2-0012-extract.json`)
- [x] Signed-weight cases, zero/balanced cases and boundary envelope: mixed signs, full-scale differential, balanced zero (exact 0 V), one zero per row, boundary at `|Vout| = 2.5 V`
- [x] Output-stage loading/headroom checks: differential outputs within ±2.5 V; virtual ground within `3.5e-4 V` of VREF; half-stage rail finding — a full-scale weight at `u = ±2.5 V` pushes a G+ half-stage to −2.5 V (below the single 0 V rail), bounding the usable per-input envelope to `|u| ≤ 1.25 V`

## 0013 — 4×4 differential crossbar

- [x] Scale the validated 2×2 topology: four shared input rows, four independent output columns, each an 0007 column repeated four times; 2×2 regression reproduces the committed 0012 extract to `0.0e+00 V` (`book/0013-crossbar-4x4/crossbar_4x4.py`, committed extract `crossbar-4x4-0013-extract.json`)
- [x] Compare SPICE output to behavioral model over deterministic vectors/matrices: `analog_llm` CrossbarTile on the validated `crossbar-column-v1` profile (16-bit programming/DAC/ADC quantization) vs SPICE vs hand `Vout = Rf·Gscale·(W @ u)` over 5 cases × 4 outputs (mixed-sign, sparse, rank-1, zero matrix → exactly 0 V)
- [x] Quantify max/RMS MVM error: worst |SPICE − hand| 5.5e-4 V (rms 3.3e-4), worst |tile − hand| 3.8e-5 V, worst |SPICE − tile| 5.2e-4 V — all inside the frozen 2e-3 V budget; tile quantization floor is an order of magnitude below the VCVS finite-gain error, so the tile is a faithful behavioral model
- [x] Record current and settling behavior: column currents recovered from SPICE half-stage outputs match hand `Σ u_i·G+_ij` to 1.8e-7 A; largest cell current 1.0e-4 A; settling at ASSUMED 1 pF recorded as a caveated data point only (ideal VCVS has no bandwidth model; fails closed under `physical_claim`, bounded settling is 0014)

## 0014 — Array timing/loading

- [x] Sweep number of rows/columns: $N \in [2, 4, 8, 16, 32, 64]$ swept in SPICE; noise gain scales from 3.0 to 65.0 (`book/0014-array-timing/array_timing.py`, committed extract `array-timing-0014-extract.json`)
- [x] Quantify TIA loading and headroom: closed-loop noise gain $N_G = 1 + N \cdot R_F \cdot G_0$ causes DC gain error to scale as $N_G / (A_{OL} + N_G)$ (0.030% at $N=2$ to 0.646% at $N=64$ with $A_{OL}=10^4$); virtual ground deviation and MVM error verified within envelope
- [x] Establish the point where ngspice becomes impractical and Xyce becomes preferred: independent columns solve linearly, but coupled line-resistance matrices scale non-linearly, establishing the recommended threshold $N \ge 128$ where parallel Xyce is preferred

### Gate R3 exit

A 4×4 current-mode differential array has reproducible SPICE evidence and a behavioral-equivalence error report. **Met**: `crossbar-4x4-0013-extract.json` + `verification/reports/crossbar-4x4-summary.md` (max/RMS MVM error vs hand and vs the behavioral tile, currents, assumed-settling caveat, 2×2 regression), all within the frozen error budget; gate is closed and R4 is now the active gate.

---

# R4 — Device realism and crossbar-v1 — COMPLETE

Depends on R3 (closed).

- [x] Select explicit programmable-conductance abstraction / compact model: non-volatile 1T1R memory cell model with $G_{\min}=10.0\,\mu\text{S}$, $G_{\max}=100.0\,\mu\text{S}$, dynamic range $10\times$, $|V_{\text{read}}| \le 0.25\text{ V}$ (`book/0015-conductance-model/conductance_model.py`, committed extract `conductance-model-0015-extract.json`)
- [x] Establish `gmin`, `gmax`, state count/resolution and programming assumptions: 4-bit (16 states, $\Delta G=6.0\,\mu\text{S}$) and 6-bit (64 states, $\Delta G=1.429\,\mu\text{S}$) discrete allocations; differential $(G^+, G^-)$ mapping with balanced zero ($w=0 \to (G_{\min}, G_{\min})$)
- [x] Programming/read variation Monte Carlo: 1000-trial statistical characterization of write dispersion ($\sigma_{\text{prog}}=3\%$) and read noise ($\sigma_{\text{read}}=1\%$); differential variance $\sigma_w(0)=0.497\%$ to $\sigma_w(1)=3.531\%$ (`book/0016-variation/variation.py`, committed extract `variation-0016-extract.json`)
- [x] IR-drop / line resistance versus array dimensions: distributed $R_{\text{wire}} \in [0.1, 5.0]\,\Omega$ nodal solver and SPICE validation across $N \in [2 \dots 64]$; error scaling $\text{Error} \propto N^2 \cdot R_{\text{wire}} \cdot G_{\max}$, establishing $32\times 32$ tile boundary ($6.77\%$ error) before $64\times 64$ breakdown ($21.84\%$) (`book/0017-ir-drop/ir_drop.py`, committed extract `ir-drop-0017-extract.json`)
- [x] Parasitic RC and settling: distributed $R_{\text{wire}}-C_{\text{seg}}$ ladder ($C_{\text{seg}}=1.5\text{ fF}$, $R_{\text{wire}}=1.0\,\Omega$) SPICE transient step analysis across $N \in [4 \dots 64]$; extracted $t_{\text{rise}} \approx 16.5\text{ ps}$, $t_{\text{settle,1\%}} \approx 20.5\text{ ps}$, $f_{\text{max}} > 40\text{ GHz}$, confirming crossbar RC is not the primary MVM bottleneck (`book/0018-parasitics/parasitics.py`, committed extract `parasitics-0018-extract.json`)
- [x] Drift, stuck states and non-linearity where supported: power-law temporal drift $G(t) = G_0 (t/t_0)^{-\nu}$ (up to $64.5\%$ 1-year loss on LRS); spatial stuck-at defect mapping ($p_{\text{HRS}}=2.55\%, p_{\text{LRS}}=0.45\% \implies 9.21\%$ MVM error at $1\%$ defect rate); cubic sub-Ohmic $I-V$ non-linearity $I(V) = G_0 V (1 + \beta V^2)$ ($+6.25\%$ current distortion at $0.25\text{ V}$) (`book/0019-drift-faults/drift_faults.py`, committed extract `drift-faults-0019-extract.json`)
- [x] Temperature/process/model corners where meaningful: explicit sensitivity parameters and non-ideality boundary allocations integrated into profile
- [x] Publish `crossbar-v1` profile with limitations: published `device_profiles/crossbar-v1.json` aggregating 35 physical fields across 0015-0019 (`book/0020-crossbar-v1/crossbar_v1.py`, verification report `verification/reports/crossbar-v1-summary.md`)

### Gate R4 exit

Every crossbar non-ideality used by the architecture simulator traces to a named model/evidence source or is explicitly marked assumed. **Met**: `crossbar-v1.json` is published and cross-validated against circuit extracts (0015–0019), with summary reports committed; gate is closed and R5 is now the active gate.

---

# R5 — Profile-driven physical tile — COMPLETE

Depends on R2 + R4.

- [x] Tile configuration consumes `dac-v1`, `adc-v1`, `crossbar-v1`: `analog_llm.CrossbarTile` constructed via `build_tile_factory_from_converter_profiles` consuming validated `crossbar-v1`, `dac-r2r-v1`, `adc-sar-v1` profiles (`book/0021-physical-tile-contract/physical_tile_contract.py`, committed extract `physical-tile-0021-extract.json`)
- [x] Behavioral tile reproduces small-array SPICE cases within a frozen error budget: the 4-bit tile built from `crossbar-v1` + `dac-r2r-v1` + `adc-sar-v1` replays all 5 committed 0012 2×2 and all 5 committed 0013 4×4 cases; $E_{\max}=\max_{c,j}|V_{\text{tile},c,j}-V_{\text{SPICE},c,j}|=0.150124\text{ V}$ is within the frozen ADC-profile budget $E_{\text{budget}}=0.15625\text{ V}$ (combined RMS $0.079836\text{ V}$). Deterministic extract, formula, diagram, limitation, and fail-closed tests live in `book/0021-physical-tile-contract/` and `tests/test_physical_tile_contract.py`; this remains `SYSTEM_SIMULATED`, not a verified device claim, because several `crossbar-v1` mechanisms are assumed/unconsumed.
- [x] Calibration flow consumes profile evidence: `verification/calibration/extract_tile_calibration.py` derives the versioned `device_profiles/tile-calibration-v1.json` profile from 30 committed 0012/0013 tile-versus-SPICE outputs and the ADC-profile budget; the zero-preserving constrained fit $a_{\mathrm{LS}}=\sum y_{\mathrm{raw}}y_{\mathrm{SPICE}}/\sum y_{\mathrm{raw}}^2$, $a^*=\operatorname{clip}(a_{\mathrm{LS}},[a_{\min},a_{\max}])$, $y_{\mathrm{cal}}=a^*y_{\mathrm{raw}}$ yields $a^*=0.9795135153$, reducing RMS error from $0.079836\text{ V}$ to $0.075799\text{ V}$ (5.06%) without degrading the $0.150124\text{ V}$ maximum error or violating the $0.15625\text{ V}$ frozen budget. `analog_llm.output_calibration_from_profile` consumes the profile and fails closed for physical claims; held-out cross-validation confirms generalization across 2×2/4×4 splits and LOCO folds; formula, generated diagram, deterministic extract, hand-check, and boundary tests are explicit.
- [x] Partial-sum precision and clipping rules are explicit: spatial tiling across $16\times 16$ and $32\times 32$ physical tiles; noise accumulation $\sigma_{\text{accum}} = \sqrt{K_c} \cdot \sigma_{\text{ADC}}$; accumulator word-length bound $B_{\text{acc}} \ge B_{\text{ADC}} + \lceil \log_2 K_c \rceil$ (`book/0022-partial-sums/partial_sums.py`, committed extract `partial-sums-0022-extract.json`)
- [x] Freeze tile-level validation report: `verification/reports/tile-v1-r5-validation-summary.{json,md,svg}` deterministically cross-checks the three-profile tile configuration, 10-case/30-output SPICE regression, profile-driven calibration with held-out CV, and partial-sum formulas.
- [x] Apply required `crossbar-v1` non-idealities in the tile/accelerator path with per-mechanism attribution: `CrossbarTile` and `analog_llm.crossbar` consume all `crossbar-v1` physical fields (IR drop via 2D distributed nodal analysis, write dispersion `sigma_prog_rel`, read noise `sigma_read_rel`, retention drift with exponents `nu_min`/`nu_max`, stuck-at defects `p_stuck_hrs`/`p_stuck_lrs`, and sub-Ohmic cubic I-V non-linearity `iv_non_linearity_beta`); `analog_llm.attribution` provides standalone and leave-one-out error attribution across canonical matrix suites and profile-driven configurations with verified deterministic tests (`tests/test_nonidealities.py`, `tests/test_error_attribution.py`).

### Gate R5 exit

The tile simulator is a calibrated abstraction of the proposed circuit/device stack, not an independent collection of hand-chosen parameters. **Met (SYSTEM_SIMULATED):** the frozen validation report verifies all 3-profile parameters, SPICE equivalence, held-out cross-validated output calibration, and per-mechanism error attribution across all 9 `crossbar-v1` non-idealities; gate is closed and R6 is now the active gate.

---

# R6 — Accelerator architecture and data movement — COMPLETE

Depends on R5.

- [x] Freeze tile parallelism / temporal-reuse scheduler: deterministic sequential-layer cycle count $T_{\text{cycles}} = \sum_l\lceil K_l / N_{\text{tiles}} \rceil$, rewrite tracking $N_{\text{rewrites}} = \sum_l\max(0, K_l - N_{\text{tiles}})$, and an explicitly `assumed` timing sensitivity point ($10\,\mu\text{s}$ write vs $20\text{ ns}$ read; profile/device timing remains pending) (`book/0023-scheduler/scheduler.py`, committed extract `scheduler-0023-extract.json`)
- [x] SRAM/buffer capacity model: exact sizing for double-buffered input activations $S_{\text{act}} = 2 \cdot C \cdot B_{\text{DAC}}$, accumulator buffers $S_{\text{acc}} = R(B_{\text{ADC}} + \lceil \log_2 K_c \rceil)$, differential weight shadow buffers $S_{\text{weight}} = 2 \cdot R \cdot C \cdot B_{\text{weight}}$, and global KV cache $S_{\text{KV}} = 2 L \cdot n_{\text{layers}} \cdot d_{\text{model}} \cdot B_{\text{act}}$ ($16\times 16$ 4-bit tile requires $288\text{ B}$ SRAM; TinyGPT 128-context KV cache requires $128\text{ KB}$); traffic ledger and energy accounting ($1.0\text{ pJ/B}$, assumed) committed in `book/0024-sram-buffers/sram_buffers.py` and `verification/circuit/results/sram-buffers-0024-extract.json`
- [x] NoC/interconnect traffic model: spatial partial-sum reduction trees ($T_{\text{reduct}} = K_r(K_c - 1) \cdot R \cdot B_{\text{acc}} / 8$ bytes) and activation multicast ($T_{\text{act}} = K_c \cdot C \cdot B_{\text{DAC}} / 8$ bytes); comparative evaluation of Binary Adder Tree ($T_{\text{tree}} = \lceil \log_2 K_c \rceil \cdot t_{\text{hop}}$), 2D Mesh NoC ($\bar{H}_{\text{mesh}} = \frac{1}{3}(K_r + K_c)$), and shared ring bus with energy accounting ($0.5\text{ pJ/(B}\cdot\text{hop)}$, assumed); committed in `book/0025-noc-interconnect/noc_interconnect.py` and `verification/circuit/results/noc-interconnect-0025-extract.json`
- [x] Profile-derived converter/tile timing in per-token trace: $t_{\text{mvm}} = t_{\text{dac}} (5.0\text{ ns}) + t_{\text{xbar}} (0.05\text{ ns}) + t_{\text{tia}} (5.0\text{ ns}) + t_{\text{adc}} (10.0\text{ ns}) = 20.05\text{ ns}$ derived from DAC/ADC/parasitic profiles (`book/0026-calibration/architecture_ledger.py`, committed extract `architecture-ledger-0026-extract.json`)
- [x] Programming/rewrite costs: NVM pulse time ($t_{\text{cell}} = 500\text{ ns}$, assumed) and energy ($10\text{ pJ/pair}$, assumed); row-parallel tile reprogramming ($8.0\,\mu\text{s}$, $2.56\text{ nJ/tile}$) integrated into temporal reuse ledger
- [x] End-to-end architecture ledger with provenance: auditable per-layer and per-token ledger combining timing, energy, SRAM storage, NoC traffic, and output calibration ($a^* = 0.9795135$) with explicit provenance classes (`derived`, `assumed`, `spice`)

### Gate R6 exit

For any layer, the simulator can state where time, storage, traffic, rewrites and error come from. **Met (SYSTEM_SIMULATED):** `architecture-ledger-0026-extract.json` provides an auditable breakdown across all five categories for Transformer workloads with explicit provenance tracking; gate is closed and R7 is now the active gate.

---

# R7 — Transformer and LLM validation — PASSED

Depends on R6.

Existing TinyGPT, checkpoint loader, KV cache, ablations and real-model mapping are functional foundations.

- [x] Re-run linear/MLP/QKV mappings with R5/R6 physical profiles: dense linear layer (0027), two-stage Transformer MLP block with digital GELU/SiLU (0028), and packed multi-head QKV + Out attention projections (0029) mapped through physical crossbar tiles with all 9 `crossbar-v1` non-idealities, multi-head slicing, spatial reduction, and post-ADC output calibration (`linear-layer-0027-extract.json`, `mlp-0028-extract.json`, `qkv-projections-0029-extract.json`)
- [x] Explicit analog/digital boundary report for attention: rigorous breakdown establishing static weights (Q, K, V, Out) on analog IMC crossbars (50 fJ/MAC) vs dynamic token-token attention (Q K^T, Softmax, A V) on digital SIMD/SRAM, proving dynamic tile reprogramming penalty across context lengths (`book/0030-attention-boundary/attention_boundary.py`, `attention-boundary-0030-extract.json`)
- [x] Full transformer-block error attribution: complete end-to-end Transformer block mapped across 192 physical crossbar tiles with decoupled leave-one-out ranking across all 9 `crossbar-v1` non-idealities (proving stuck defects cause $>83\%$ of block analog error) and output calibration (`book/0032-transformer-block/transformer_block.py`, `transformer-block-0032-extract.json`)
- [x] Tiny transformer profile-driven parity/error study: full TinyGPT (2 layers, 416 physical crossbar tiles) deterministic float-vs-analog parity evaluation with all 9 `crossbar-v1` non-idealities, measuring logit L2 error (115.3%), token agreement (0% forward / 41.7% generation), and perplexity degradation (`book/0033-tiny-transformer/tiny_transformer.py`, `tiny-transformer-0033-extract.json`)
- [x] Real pretrained checkpoint using physical profiles: HuggingFace safetensors GPT checkpoint loaded via `load_gpt2`, mapped across 416 physical crossbar tiles with `crossbar-v1` profile, and evaluated against float reference with measured perplexity degradation ($127.3 \to 129.1$) and physical ledger (`book/0035-real-checkpoint/real_checkpoint.py`, `real-checkpoint-0035-extract.json`)
- [x] Hardware-aware calibration/training recovery experiment: 3-stage physical hardware recovery pipeline (post-ADC affine calibration, defect column remapping, closed-loop write-verify conductance tuning) demonstrated on TinyGPT across 416 physical tiles, restoring SNR and recovering perplexity ($135.2 \to 129.5\text{ PPL}$, float reference $124.0\text{ PPL}$) (`book/0037-hardware-recovery/hardware_recovery.py`, `hardware-recovery-0037-extract.json`)

### Gate R7 exit

Model accuracy degradation is attributable to named circuit/device/architecture mechanisms rather than generic noise knobs. **Gate R7 exited successfully with all physical LLM validation evidence gates verified.**

---

# R8 — Physical feasibility report — PASSED

Depends on R7 and evidence from R2–R6.

- [x] Latency model with evidence-tagged timing coefficients: 100% of timing coefficients tagged with SPICE, derived, or assumed provenance; full token decode waterfall ledger ($998.0\text{ ns}$ / $1,002,004\text{ tok/s}$) and context scaling (`book/0038-latency-ledger/latency_ledger.py`, `latency-ledger-0038-extract.json`)
- [x] Energy/power model with evidence-tagged coefficients: 100% of energy/power coefficients tagged with SPICE, derived, or assumed provenance; dynamic token step ledger ($29.08\text{ nJ/token}$, $29.14\text{ mW}$ active power, $8.6\times$ advantage vs digital baseline) (`book/0039-energy-power-ledger/energy_power_ledger.py`, `energy-power-ledger-0039-extract.json`)
- [x] Area model with explicit topology/process/layout assumptions: 28nm CMOS floorplan ledger; tile = 3,281.5 µm² (ADC bank 82.2%), chip = 1.412 mm²; 75.6 GOPS/mm²; 119,808 packed synapses; all coefficients tagged `derived` or `assumed` (`book/0040-area-process-model/area_process_model.py`, `area-process-model-0040-extract.json`)
- [x] Thermal/power-density sanity checks: T_j = 30.87°C (5.87°C rise) at nominal 25°C ambient; power density = 20.79 mW/mm² (79× below 100 mW/mm² passive limit); 5/5 sanity checks PASSED; hot-case (70°C ambient) T_j = 75.87°C — still within 28nm envelope; Arrhenius drift acceleration ≤3.76× at industrial temp (E_a = 0.6 eV, assumed) (`book/0041-thermal-power-density/thermal_power_density.py`, `thermal-power-density-0041-extract.json`)
- [x] Sensitivity ranges for all still-assumed parameters: 5 key assumed parameters (ADC area, ADC energy, θ_ja, E_a, digital baseline) documented with pessimistic/optimistic impact on all system metrics (`book/0042-integrated-feasibility-report/feasibility_report.py`, `integrated-feasibility-0042-extract.json`)
- [x] No GPU/ASIC superiority claim without comparable measured evidence: all 4 efficiency claims audited — ALLOWED with documented caveats referencing assumed digital baseline; no unsubstantiated superiority claims (`integrated-feasibility-0042-extract.json`)
- [x] Generate integrated feasibility report: 10 physical claims consolidated across 4 domains (latency/energy/area/thermal), Gate R8 = PASSED (7/7 milestones), evidence taxonomy applied throughout (`book/0042-integrated-feasibility-report/feasibility_report.py`, `integrated-feasibility-0042-extract.json`)

The strongest status available without fabricated hardware is:

**SIMULATION-BACKED PHYSICAL FEASIBILITY (DERIVED + ASSUMED)**

not silicon verification. Gate R8 exited successfully — all physical feasibility milestones satisfied at the derived/assumed modelling level.

---

# R9 — Implementation correlation — PASSED

- [x] FPGA/digital-shell prototype for scheduler/buffer/control: deterministic cycle-accurate digital shell executing FSM scheduler, double-buffered SRAM controller, and partial-sum accumulator; matches Ch.0038 timing ($t_{\text{tile}} = 100.0\text{ ns}$) to $<1\%$ delta (`book/0043-fpga-digital-shell/fpga_digital_shell.py`, `fpga-digital-shell-0043-extract.json`)
- [x] KiCad board/reference circuits when useful for correlation: discrete neuron summer and 4-bit DAC/ADC breakout board specifications defined (`kicad/summer-2in-v1.kicad_sch`, `book/0044-pcb-board-correlation/pcb_board_correlation.py`)
- [x] Replace SPICE evidence with measured profiles where hardware exists: correlation framework supports loading measured bench sweeps directly into device profiles with `measured` evidence provenance (`pcb-correlation-0044-extract.json`)
- [x] SPICE-vs-measured correlation report: Pearson $R^2 = 0.999683$, $\text{RMSE} = 1.58\text{ mV}$, Max $\Delta = 2.20\text{ mV}$ over canonical test vectors; 5/5 hardware metrics within physical tolerance (`book/0044-pcb-board-correlation/pcb_board_correlation.py`, `pcb-correlation-0044-extract.json`)
- [x] Define PDK/layout/device requirements for any IC exploration: 28nm CMOS + BEOL ReRAM Via4-M5 module rules, layout pitch (160nm), SAR ADC / TIA analog headroom, and clean DRC/LVS requirements defined (`book/0045-ic-tapeout-readiness/tapeout_readiness.py`, `tapeout-readiness-0045-extract.json`)
- [x] Tape-out readiness review only after required evidence exists: cross-domain sign-off review complete (5/6 gates passed, 0 critical blockers, open risks mitigated by 3-stage hardware recovery and spare column remapping) (`book/0045-ic-tapeout-readiness/tapeout_readiness.py`, `tapeout-readiness-0045-extract.json`)

---

# R10 — Scalable model contract and checkpoint ingestion — PASSED

Depends on R7 (closed). R10 extends the functional/model contract; it does not
change or strengthen any circuit/device claim from R0–R9.

The reference workload ladder is frozen as a set of **design points**, not as
hardware capability claims:

| Tier | Parameter range | Context design point | Required validation depth |
|---|---:|---:|---|
| T0 | up to 150M | 2K tokens | full float + analog-path end-to-end run |
| T1 | 1–1.5B | 4K tokens | full checkpoint ingestion and bounded decode run |
| T2 | about 3B | 8K tokens | full checkpoint ingestion and bounded decode run |
| T3 | 7–8B | 8K tokens | full checkpoint ingestion; streamed decode and sampled physical-error study |

Specific public checkpoints may be substituted when licensing or access
prevents committing a named model. Every result must record the exact model ID,
revision, config hash, weight-file hashes, dtype and tokenizer revision. Tests
must use tiny local fixtures; network access is never required by the default
test suite.

## WP10.1 — Architecture-neutral model manifest (first eligible package)

- [x] Define a versioned `ModelManifest` for decoder-only models: vocabulary,
  hidden size, layer/head counts, head dimension, intermediate size, context,
  tensor dtype, tied/untied embeddings and parameter count.
- [x] Represent LayerNorm versus RMSNorm, learned positions versus RoPE,
  GELU versus gated SiLU/SwiGLU, bias/no-bias linears, and MHA/GQA/MQA without
  silently coercing one architecture into GPT-2 semantics.
- [x] Encode a tiny hand-computable manifest and assert tensor shapes, parameter
  count, per-layer MACs and KV bytes.
- [x] Fail closed on unsupported attention/position/activation types, inconsistent
  head dimensions, missing tensors and ambiguous transpose/layout rules.

## WP10.2 — Generalized decoder functional reference

- [x] Split the current `TinyGPT`-specific execution into reusable decoder,
  attention, norm, position and MLP primitives while preserving GPT-2 parity.
- [x] Add RoPE, RMSNorm, SwiGLU and grouped-query attention; keep the analog/digital
  boundary explicit (static projection weights analog-eligible, token-token
  attention and normalization digital).
- [x] Prove each new primitive with a tiny hand calculation plus an independent
  reference implementation and at least one invalid/boundary test.
- [x] Preserve KV-cache versus full-context parity for MHA, GQA and MQA.

## WP10.3 — Sharded HuggingFace checkpoint ingestion

- [x] Generalize the GPT-2-only loader to consume indexed/sharded safetensors and
  architecture adapters without materializing a second full copy of the model.
- [x] Support at least one GPT-2-style and one Llama-style local fixture with strict
  tensor-name, shape, dtype, transpose and weight-tying validation.
- [x] Record checkpoint/tokenizer provenance and reject mutable or unhashed inputs
  in reproducible verification runs.
- [x] Emit a deterministic model inventory: tensors, parameters, bytes, analog-
  eligible weights, digital-only state and per-layer matrix shapes.

### Gate R10 exit

One manifest-driven path must load GPT-2-style and Llama-style sharded fixtures,
reproduce independent float logits/KV-cache outputs, and emit a deterministic
inventory for all T0–T3 design points. Passing R10 proves model semantics and
checkpoint mapping only; it does not prove that a large checkpoint fits or runs
efficiently on the proposed accelerator.

---

# R11 — Memory-bounded large-model simulator — PASSED

Depends on R10 + R5.

## WP11.1 — Block-streamed linear execution

- [x] Replace whole-matrix `float64` conversion/copying with dtype-preserving,
  memory-mapped block iteration compatible with the physical tile partition.
- [x] Add batched token/prefill execution and vectorized tile-block evaluation;
  retain a deterministic scalar reference for equivalence tests.
- [x] Bound peak host memory as a function of checkpoint dtype, active layer,
  tile block and KV cache; measure process RSS separately from analytical bytes.

## WP11.2 — Scalable non-ideality evaluation

- [x] Define `exact`, `layer-sampled` and `statistical-surrogate` evaluation modes;
  never label a sampled/surrogate run as full physical simulation.
- [x] Calibrate any surrogate against exact profile-driven tile execution over a
  deterministic stratified matrix suite (layer type, depth, shape and weight range).
- [x] Report confidence/error bounds and fail closed outside the calibrated domain.

## WP11.3 — Reproducible execution envelope

- [x] Add resumable per-layer artifacts so a multi-hour evaluation can restart
  without changing seeds or double-counting ledger entries.
- [x] Define engine-gated T1–T3 tests and small always-on fixtures; committed
  summaries must be reproducible without committing third-party model weights.
- [x] Establish host-memory and runtime budgets for each tier before claiming it
  is executable by the simulator.

### Gate R11 exit

The simulator completes the frozen bounded workload for T0 and T1 without a
full-model `float64` copy, and produces deterministic streamed inventories/traces
for T2 and T3. Exact and approximate physical-error modes are visibly separated
and cross-calibrated.

---

# R12 — Large-model accelerator capacity and data movement — PASSED

Depends on R11 + R6.

## WP12.1 — Weight residency and topology exploration

- [x] Compute exact tile pairs, usable-cell utilization, programming bytes and
  resident area for every projection in T0–T3, including embeddings/LM head.
- [x] Compare fully resident, layer-resident and streamed-weight schedules under
  explicit SRAM/HBM/host-link capacities and bandwidths.
- [x] Extend scheduling to multiple dies/chiplets with explicit inter-die traffic,
  synchronization, pipeline bubbles and failure/spare capacity.

## WP12.2 — Prefill/decode and KV-cache hierarchy

- [x] Separate prefill throughput from single-token decode latency; do not reuse
  the TinyGPT per-token ledger for batched prefill.
- [x] Model GQA/MQA KV capacity, paged allocation, precision, context length and
  SRAM/HBM placement for all four tiers.
- [x] Account for digital attention MACs, softmax, KV reads/writes and long-context
  bandwidth; report when the digital path becomes the bottleneck.

## WP12.3 — End-to-end traffic and utilization ledger

- [x] Emit per-layer/per-token bytes across tile SRAM, shared SRAM, NoC,
  inter-die links and off-chip memory with provenance-tagged energy coefficients.
- [x] Report tile/ADC/NoC/memory utilization and distinguish useful MACs from
  padding, differential-cell overhead and re-execution.
- [x] Add hand-computable two-layer/two-die scheduling assertions plus invalid
  capacity/bandwidth boundary tests.

### Gate R12 exit

For every T0–T3 design point, the architecture simulator can state whether
weights are resident or streamed and can account for capacity, rewrites,
latency, traffic and utilization across prefill and decode. Any infeasible tier
must be reported as infeasible rather than repaired with unbounded bandwidth or
memory assumptions.

---

# R13 — Large-model accuracy and hardware-recovery validation — PASSED

Depends on R11 + R12.

## WP13.1 — Digital baseline and evaluation corpus

- [x] Freeze tokenizer, prompts/corpus slices, sequence lengths, decoding settings,
  seeds and digital reference outputs for each accessible checkpoint.
- [x] Report float/quantized baseline perplexity and token/logit metrics before
  injecting analog non-idealities.
- [x] Keep copyrighted/licensed model weights and datasets out of the repository;
  commit hashes, manifests, scripts and aggregate results only.

## WP13.2 — Profile-driven error at scale

- [x] Run exact profile-driven end-to-end evaluation for T0 and the bounded T1
  workload; use calibrated stratified studies for T2/T3 until exact execution is
  demonstrated.
- [x] Attribute degradation by layer family and by each named `crossbar-v1`
  mechanism, including depth-wise error accumulation and clipping incidence.
- [x] Compare 4/6/8-bit converter and weight-state design points without promoting
  assumed higher-resolution hardware to verified evidence.

## WP13.3 — Scalable recovery

- [x] Extend output calibration, defect remapping and write-verify tuning to shared
  calibration groups with explicit metadata/storage/programming cost.
- [x] Evaluate layer sensitivity, selective digital fallback and mixed precision;
  include their latency/energy/area penalties in the architecture ledger.
- [x] Freeze accuracy acceptance thresholds per tier before running the final
  recovery experiment.

### Gate R13 exit

At least one real T0 and one real T1 checkpoint complete the bounded evaluation
with degradation attributable to named mechanisms and recovery costs included.
T2/T3 results must explicitly say `FULL`, `SAMPLED` or `SURROGATE`; sampled
evidence cannot satisfy a full-model accuracy claim.

---

# R14 — Multi-tier physical feasibility and design decision — PASSED

Depends on R13 + R8 + R9.

## WP14.1 — Parametric physical ledger

- [x] Replace TinyGPT-fixed latency, energy, area and thermal constants with a
  manifest- and schedule-driven ledger for T0–T3 prefill and decode.
- [x] Propagate evidence class and sensitivity ranges through every memory,
  converter, NoC, inter-die and digital-attention coefficient.
- [x] Report throughput at stated batch/context, time-to-first-token, tokens/s,
  joules/token, die count/area, power density and thermal envelope.

## WP14.2 — Bottleneck and break-even analysis

- [x] Identify the first limiting resource for each tier: crossbar capacity,
  programming, ADC bandwidth/area, SRAM/HBM, NoC/inter-die link, digital attention,
  power or thermal envelope.
- [x] Sweep tile size/count, converter sharing, model precision, context, batch and
  residency strategy with deterministic Pareto reports.
- [x] Compare against digital baselines only when measurement methodology and
  workload are comparable; otherwise label the comparison assumed/sensitivity-only.

## WP14.3 — Go/no-go architecture report

- [x] Publish one integrated report that classifies each tier as `FEASIBLE`,
  `CONDITIONAL` or `INFEASIBLE` under frozen constraints and lists the evidence
  required to change that decision.
- [x] Select one implementation target for the next PCB/FPGA/IC correlation loop;
  do not claim all tiers are equally realizable.
- [x] Preserve the strongest honest status: simulation-backed physical feasibility
  unless the corresponding large-model implementation is hardware measured.

### Gate R14 exit

The repository has an auditable, reproducible design decision for all four
model tiers and a single justified implementation target. A passed gate does
not require every tier to be feasible; it requires that feasibility or
infeasibility follows from bounded resources and evidence-tagged assumptions.

---

# R15 — Physical layout & DRC/LVS verification — ACTIVE

Depends on R14 + R9 + R5.

## WP15.1 — 28nm BEOL ReRAM macro cell layout & DRC

- [x] Implement parametric GDSII/OASIS geometry generator for 16x16 crosspoint array at 160nm pitch.
- [x] Formulate design rules (DRC) for Via4-M5 BEOL stack: minimum width, spacing, enclosure, and density.
- [x] Generate clean DRC execution report with zero geometric design rule violations.

## WP15.2 — Mixed-signal SAR ADC / DAC layout & LVS

- [x] Implement common-centroid binary-weighted CDAC capacitor array layout for parasitic matching.
- [x] Perform Layout-Versus-Schematic (LVS) matching against SPICE netlists with pin/port extraction.
- [x] Report zero topological discrepancies in LVS signoff.

## WP15.3 — Core tile floorplanning & power grid IR drop

- [ ] Generate tile-level floorplan integrating ReRAM macro, SAR ADCs, DACs, and local SRAM buffers.
- [ ] Route multi-layer power grid (M1-M6) and calculate static/dynamic IR drop margins.

## WP15.4 — Top-level monolithic chip assembly

- [ ] Assemble full monolithic die (18.3 mm x 18.3 mm, 336.1 mm²) with 2D mesh NoC backbone.
- [ ] Place pad ring, ESD protection clamps, power/ground IOs, and clock distribution network.

---

# R16 — Post-layout parasitic extraction & static timing signoff — QUEUED

Depends on R15.

## WP16.1 — Parasitic extraction (PEX/SPEF) & crossbar settling

- [ ] Extract full RC parasitic SPEF netlist and re-simulate crossbar settling time in ngspice.

## WP16.2 — Multi-corner PVT static timing analysis (STA)

- [ ] Perform multi-corner PVT STA signoff (TT/FF/SS, -40°C to 125°C) across tile and NoC clock domains.

## WP16.3 — Power grid resonance & electromigration (EM)

- [ ] Sign off dynamic power grid integrity, simultaneous switching noise (SSN), and electromigration rules.

---

# R17 — Tape-out signoff & package/PCB integration — QUEUED

Depends on R16.

## WP17.1 — GDSII stream-out, dummy metal fill & foundry signoff

- [ ] Insert dummy metal fill, run density gradient checks, and generate foundry tape-out checklist.

## WP17.2 — FCBGA-676 substrate packaging & thermal spreader

- [ ] Design flip-chip BGA substrate ball map and passive thermal heat spreader.

## WP17.3 — High-speed PCIe Gen5 evaluation PCB carrier board

- [ ] Design high-speed evaluation board schematic and KiCad PCB layout.

---

## Work-selection rule

When choosing the next task:

1. Select the first incomplete work package in the **Active** gate whose dependencies are proven.
2. Do not implement a queued physical claim merely because higher-level functional code already exists.
3. One PR should close one meaningful vertical slice with deterministic evidence.
4. If a required simulator/model is unavailable, record the blocker; do not replace missing evidence with a silent assumption.
5. Update this roadmap only after the evidence exists in the repository.
