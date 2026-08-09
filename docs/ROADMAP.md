# Roadmap — Analog AI Machine (design + simulation verification)

The project designs a hybrid analog-digital accelerator and verifies it from circuit primitives through LLM inference. A milestone is done only when backed by executable evidence; prose or an illustrative plot alone is not completion.

The governing chain is:

```text
math → functional model → circuit/SPICE → variation → extracted profile
     → architecture → model inference → physical-feasibility report
```

See `docs/SIMULATION_STACK.md`.

## V0 — Verification contract and provenance

- [x] Define functional/circuit/system claim levels
- [x] Define ngspice + PySpice as the default circuit-verification path
- [x] Define Xyce as the large-array/parallel SPICE backend
- [x] Add `device_profiles/` provenance contract
- [x] Add fail-closed validation preventing assumed/functional-only profiles from supporting physical claims
- [x] Define verification evidence layout under `verification/`
- [ ] Add generated machine-readable verification summary/report format
- [ ] Tag every existing physical/system constant in `analog_llm/` as profile-derived or assumed

Exit: no parameter can silently cross from architecture software into a physical claim.

## Book track — current circuit evidence

- [x] Verify the 0005 weighted-sum circuit in ngspice/PySpice against hand arithmetic
- [x] Ship schematic and runnable `sim_neuron.py`
- [x] Add non-ideal op-amp model with finite gain, offset and rail saturation
- [x] DC sweep showing linear region and clip points
- [x] Virtual-ground and rail-headroom analysis
- [x] BOM/wiring/test-point/calibration artifacts for 0005
- [x] Chapter 0006 scaling from one neuron to many-neuron layer, including 2-neuron SPICE check
- [ ] Extract the verified 0005/0006 circuit quantities into a versioned device profile
- [ ] Make downstream behavioral/system tests consume that profile

Exit: book-level circuit results become reusable machine-readable evidence rather than isolated chapter plots.

## V1 — Converter circuit design

- [ ] Specify DAC architecture and design envelope
- [ ] ngspice DC/transient simulation for DAC transfer and settling
- [ ] Extract range, gain/offset, resolution/ENOB-equivalent metrics and settling into a `spice` profile
- [ ] Specify ADC/output-stage architecture and design envelope
- [ ] ngspice/Xyce simulation for transfer, clipping, settling and noise where the model supports it
- [ ] Extract ADC profile with provenance
- [ ] Add parameter sweeps for supply and temperature
- [ ] Add Monte Carlo variation for component/device mismatch where models permit

Exit: architecture-level DAC/ADC parameters no longer rely only on arbitrary normalized values.

## V2 — Crossbar/device realism

- [ ] Select explicit conductance-cell abstraction/compact model for the first physical design candidate
- [ ] Validate `gmin/gmax` and state/resolution behavior with SPICE/compact-model sweeps
- [ ] Add programming/read variation model backed by named simulation or cited device assumptions
- [ ] Add line resistance / IR-drop study
- [ ] Add parasitic RC / settling study
- [ ] Add drift/stuck-state experiments when supported by the device model
- [ ] Use Xyce for array sizes where ngspice becomes impractical
- [ ] Publish `crossbar-v1` profile with limitations and conditions

Exit: crossbar non-idealities used downstream trace to an explicit device/circuit model.

## M0 — Functional contracts

- [x] Define matrix convention and unit conventions
- [x] Behavioral DAC/ADC bits, clipping, noise, gain/offset
- [x] Differential conductance weight model with finite resolution
- [x] Fail-closed validation on invalid inputs
- [ ] Freeze error-budget and reporting format (ledger + token agreement + provenance)

Exit: mathematical mapping is stable and clearly separated from physical evidence.

## M1 — Crossbar and tile

- [x] Weight normalization and differential encoding
- [x] Single programmable tile with converter non-idealities
- [x] Hand-computable tile tests
- [x] Sweep conductance bits vs effective-weight error
- [ ] Add profile-driven tile configuration path
- [ ] Compare behavioral tile output against SPICE-derived small-array cases

Exit: tile behavior is both functionally correct and calibratable to circuit evidence.

## M2 — Accelerator and tiling

- [x] Split logical matrix into physical tiles with digital partial sums
- [x] Pad edge blocks
- [x] Physical ledger: MACs, tile cycles, rewrites, tiles used
- [x] Multi-tile demo
- [ ] Multi-tile parallelism model and temporal-reuse scheduler analysis
- [ ] Add converter settling and profile-derived timing into cycle model
- [ ] Add SRAM/buffer and interconnect traffic accounting

Exit: architecture costs are explicit rather than inferred from ideal crossbar parallelism.

## M3 — Tiny transformer on accelerator

- [x] Deterministic nanoGPT-style model
- [x] Hybrid forward: linears through tiles, nonlinear/control operations digital
- [x] Autoregressive generation
- [x] Float baseline and unified report
- [x] KV-cache path
- [x] Per-token ledger trace
- [ ] Per-token latency trace driven by profile-derived or explicitly assumed component timing

Exit: the model runs end to end with traceable architecture assumptions.

## M4 — Accuracy / sensitivity

- [x] High-precision and budget-constrained configurations
- [x] Per-non-ideality ablation
- [x] Bit sweeps / accuracy-vs-cost curves
- [ ] Repeat sensitivity studies using SPICE-derived converter/crossbar profiles
- [ ] Add guardrail in reports preventing GPU-equivalence claims from functional ledgers

Exit: accuracy degradation is attributable to named physical mechanisms and evidence classes.

## M5 — Real pretrained checkpoint

- [x] Loader for real checkpoint weights
- [x] Tokenizer + numeric reference parity
- [x] Map a real small model through tiles and report full sequence
- [x] Failure analysis for constrained configuration
- [ ] Run the same checkpoint using the first circuit-derived device profile

Exit: real-model feasibility is evaluated using traceable proposed-device parameters.

## M6 — Latency / energy / area feasibility

- [x] Model converter count, tile programming and reuse in ledger
- [x] Relative latency sensitivity to tile capacity and parallelism
- [x] No GPU comparison without measured physical assumptions
- [ ] Replace relative timing with SPICE-derived settling/conversion timing where available
- [ ] Add energy model whose coefficients are tagged `spice`, `derived`, `measured`, or `assumed`
- [ ] Add area model with explicit process/layout assumptions
- [ ] Add thermal/power-density sanity checks
- [ ] Generate a feasibility report separating verified evidence from assumptions

Exit: the project can state a simulation-backed physical-feasibility case with an auditable evidence chain.

## M7 — Toward implementation

- [ ] KiCad reference schematics for the selected board-level prototype path
- [ ] FPGA/digital-shell model for scheduler, buffers and data movement
- [ ] Correlate FPGA/board measurements with simulator when hardware exists
- [ ] Upgrade relevant profile evidence classes from `spice`/`assumed` to `measured`
- [ ] Define criteria for any future IC/layout/tape-out exploration

Exit: simulation predictions can be compared directly with real hardware measurements rather than treated as final truth.
