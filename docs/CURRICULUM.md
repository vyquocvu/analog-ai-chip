# Curriculum — from first principles to physical feasibility

This repository is organized as a dependency-ordered engineering curriculum. The goal is not to jump from an ideal NumPy crossbar to a hardware claim; each layer must produce evidence that constrains the next one.

```text
Math
 ↓
Ideal functional model
 ↓
Circuit design
 ↓
SPICE simulation
 ↓
Non-ideal device model
 ↓
ADC / DAC
 ↓
Crossbar tile
 ↓
Multi-tile accelerator
 ↓
Digital control + dataflow
 ↓
Transformer layer
 ↓
Small LLM
 ↓
Physical feasibility report
 ↓
FPGA / PCB / silicon prototype
```

## Part I — Physics and mathematics

| # | Chapter | Verification target |
|---|---|---|
| 0000 | What are we designing? | system boundaries, claim levels, evidence chain |
| 0001 | Ohm + Kirchhoff | hand-computable current sums agree with executable reference |
| 0002 | Analog matrix-vector multiplication | ideal crossbar MVM matches dense reference |
| 0003 | Signed weights | differential `G+ / G-` mapping reproduces signed weights |
| 0004 | Noise, precision, and error | explicit error sources remain separated and measurable |

## Part II — Circuit design

| # | Chapter | Verification target |
|---|---|---|
| 0005 | One analog neuron | SPICE output matches hand arithmetic within stated tolerance |
| 0006 | Op-amp current summation / many neurons | summing behavior, headroom, and scaling remain valid |
| 0007 | DAC design | transfer, clipping, settling, gain/offset characterized in SPICE |
| 0008 | ADC/output-stage design | transfer, noise, clipping, settling characterized in SPICE |
| 0009 | Differential crossbar cell | one signed cell has an explicit physical circuit/device model |
| 0010 | 4×4 crossbar | small array agrees with behavioral model under circuit non-idealities |

## Part III — Device realism

| # | Chapter | Verification target |
|---|---|---|
| 0011 | Conductance programming | `gmin/gmax`, levels, and programming behavior have provenance |
| 0012 | Device variation | Monte Carlo distributions quantify mismatch/program variation |
| 0013 | Drift | time-dependent conductance error is bounded or explicitly excluded |
| 0014 | IR drop | line resistance impact is quantified versus array dimensions |
| 0015 | Parasitics | RC and settling constraints are extracted from circuit models |
| 0016 | Converter non-linearity | INL/DNL or equivalent limitations are modeled when evidence exists |

## Part IV — Accelerator architecture

| # | Chapter | Verification target |
|---|---|---|
| 0017 | Tile architecture | tile contract consumes circuit-derived device profiles |
| 0018 | Partial sums | tiled result matches dense reference within profile-derived error |
| 0019 | Tile scheduler | temporal reuse and parallelism are explicit and deterministic |
| 0020 | SRAM / buffers | storage capacity and traffic are accounted for |
| 0021 | NoC / interconnect | data movement is included in timing/energy accounting |
| 0022 | Calibration | correction procedure improves measured/simulated error reproducibly |

## Part V — Neural-network mapping

| # | Chapter | Verification target |
|---|---|---|
| 0023 | Linear layer | one dense layer maps exactly onto accelerator contracts |
| 0024 | MLP | up/down projections preserve reference behavior within error budget |
| 0025 | Q/K/V projections | transformer projections route through the analog path correctly |
| 0026 | Attention | static and dynamic computations are separated honestly |
| 0027 | KV cache | dynamic state storage/traffic is explicitly modeled |
| 0028 | Transformer block | end-to-end block error is attributable to named mechanisms |

## Part VI — LLM inference

| # | Chapter | Verification target |
|---|---|---|
| 0029 | Tiny transformer | deterministic end-to-end reference and analog-path parity |
| 0030 | Full inference path | token generation has a complete architecture ledger |
| 0031 | Quantization | accuracy/cost trade-offs are reproducible |
| 0032 | Hardware-aware training | recovery under verified non-idealities is measurable |

## Part VII — Physical feasibility

| # | Chapter | Verification target |
|---|---|---|
| 0033 | Latency ledger | timing coefficients are profile-derived or explicitly assumed |
| 0034 | Power / energy ledger | energy coefficients carry evidence class and provenance |
| 0035 | Area estimate | area is tied to explicit process/layout assumptions |
| 0036 | Thermal considerations | power density and operating envelope receive sanity checks |
| 0037 | Process assumptions | device/process dependencies are documented and versioned |
| 0038 | FPGA / digital shell | scheduler/buffer/control assumptions can be tested independently |
| 0039 | Implementation / tape-out feasibility | report separates verified evidence, derived quantities, and open assumptions |

## Chapter completion rule

A chapter is not complete because prose or a plot exists. The required evidence depends on its layer:

- **Math / functional:** hand calculation + executable assertion + tests.
- **Circuit:** schematic/netlist + ngspice/PySpice or Xyce run + machine-readable extracted results.
- **Device realism:** sweep/Monte Carlo/corner evidence + explicit model provenance.
- **Architecture:** deterministic simulator + ledger + profile-driven parameters.
- **Model:** float/reference comparison + error/accuracy report.
- **Physical feasibility:** latency/energy/area quantities with evidence classes and limitations.

The evidence chain must remain auditable:

```text
equation → circuit → SPICE → device profile → accelerator → LLM → feasibility report
```

See `docs/SIMULATION_STACK.md`, `docs/PRODUCT_SPEC.md`, and `docs/ROADMAP.md` for implementation status and tooling.