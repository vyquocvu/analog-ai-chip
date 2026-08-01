# Roadmap — Build an Analog AI Machine at Home

## Product definition

The project builds a safe, modular, low-voltage hybrid analog-digital neural computer from accessible parts. Version 0.x uses resistors or digital potentiometers as programmable conductances. ReRAM is an optional research backend, not a prerequisite.

## M0 — Contracts and safety

- [x] Define system boundary and honest claims
- [x] Define chapter format
- [x] Add low-voltage safety rules
- [ ] Freeze voltage, conductance, matrix orientation, and signed-weight conventions
- [ ] Define module electrical and communication interfaces

Exit: simulator, diagrams, and future hardware use the same units and conventions.

## M1 — One analog neuron

- [ ] Select accessible op-amp and component values
- [ ] Publish schematic and breadboard wiring
- [ ] Publish BOM with acceptable substitutes
- [ ] Build weighted sum `y = w1*x1 + w2*x2 + b`
- [ ] Add expected measurement table and Python verifier
- [ ] Measure resistor tolerance, offset, saturation, and noise

Exit: two independent builders can reproduce the circuit and remain within the documented error bound.

## M2 — Fixed 2×2 crossbar

- [ ] Build unsigned 2×2 conductance array
- [ ] Add current summing/transimpedance stage
- [ ] Compare measured MVM with hand calculation and simulator
- [ ] Document loading, virtual-ground, and op-amp limitations

Exit: measured outputs reproduce at least four documented input vectors.

## M3 — Signed weights

- [ ] Implement differential `G+ - G-` encoding
- [ ] Add differential output stage
- [ ] Calibrate zero weight and gain mismatch
- [ ] Measure common-mode and subtraction error

Exit: tile represents positive, zero, and negative weights reproducibly.

## M4 — Digital control

- [ ] Choose controller board
- [ ] Define USB/serial protocol
- [ ] Add DAC input module
- [ ] Add ADC output module
- [ ] Implement `detect`, `measure`, and `self-test`

Exit: a host program sends vectors and receives timestamped measurements.

## M5 — Programmable 4×4 tile

- [ ] Evaluate digital potentiometer or resistor-switch network
- [ ] Implement weight programming
- [ ] Store per-cell calibration coefficients
- [ ] Add clipping and range validation
- [ ] Publish PCB-ready schematic

Exit: software loads a 4×4 signed matrix without manual resistor replacement.

## M6 — Calibration and experiments

- [ ] Automated offset/gain calibration
- [ ] Noise-floor and repeatability experiment
- [ ] Temperature-drift experiment
- [ ] ADC/DAC precision experiment
- [ ] Machine-readable experiment manifests and CSV results

Exit: every inference result can be traced to a calibration record and hardware revision.

## M7 — Tiny neural network

- [ ] Map one linear layer to the tile
- [ ] Perform activation digitally first
- [ ] Run a two-layer tiny classifier
- [ ] Compare accuracy against float and quantized software baselines
- [ ] Publish failure analysis, not only best-case results

Exit: end-to-end inference uses the physical analog tile for matrix-vector multiplication.

## M8 — Modular stack

- [ ] Define backplane power, addressing, and analog signal rules
- [ ] Implement tile discovery
- [ ] Add matrix tiling and partial-sum scheduler
- [ ] Validate multi-tile accumulation

Exit: two or more tiles execute a matrix larger than one physical array.

## M9 — Reproducible PCB kit

- [ ] KiCad source
- [ ] Gerbers and manufacturing notes
- [ ] BOM and approved substitutions
- [ ] Assembly and bring-up guide
- [ ] Enclosure and test jig

Exit: Homebrew Analog AI v0.1 is reproducible without relying on the original breadboard.

## M10 — Research modules

- [ ] FPGA digital shell
- [ ] MOSFET/floating-gate programmable conductance
- [ ] Memristor/ReRAM evaluation module
- [ ] Hardware-aware training
- [ ] Energy and latency ledger with measured assumptions

These milestones must never block the accessible home-build path.

## Definition of done

A hardware milestone is complete only when it includes schematics, BOM, assembly instructions, expected measurements, actual measurements, calibration, software verification, failure modes, safety notes, and a precise limitations statement.
