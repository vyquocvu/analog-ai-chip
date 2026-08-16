# Curriculum — from first principles to physical feasibility

This repository is a dependency-ordered engineering curriculum for designing and verifying an analog AI accelerator. The goal is not to jump from an ideal NumPy crossbar to a hardware claim; each layer must produce evidence that constrains the next one.

```text
Math / ideal reference
        ↓
Circuit primitives
        ↓
SPICE-verified current-mode crossbar
        ↓
Circuit-to-profile extraction
        ↓
DAC / ADC signal path
        ↓
Small crossbar arrays
        ↓
Device realism + variation
        ↓
Profile-driven tile
        ↓
Multi-tile accelerator + data movement
        ↓
Transformer / LLM mapping
        ↓
Latency / energy / area feasibility
        ↓
FPGA / PCB / silicon correlation
```

Chapter numbering below is canonical. Existing chapters keep their numbers; future work must not renumber implemented evidence.

## Part I — Math and functional reference

| # | Chapter | Verification target | Status |
|---|---|---|---|
| 0000 | What are we designing? | system boundaries, claim levels, evidence chain | done |
| 0001 | Ohm + Kirchhoff = MVM | hand-computable current sums agree with executable reference | done |
| 0002 | Signed differential weights | `G+ / G-` mapping reproduces signed weights | done |
| 0003 | DAC/ADC quantization and noise | explicit error mechanisms remain separated | done |
| 0004 | Matrix tiling | tiled partial sums match dense reference | done |

## Part II — Circuit primitives and current-mode compute

| # | Chapter | Verification target | Status |
|---|---|---|---|
| 0005 | One analog neuron | SPICE weighted-sum output matches hand arithmetic; headroom and non-ideal op-amp behavior characterized | done |
| 0006 | Many neurons / current summation | scaling ledger plus multi-output SPICE evidence | done |
| 0007 | Current-mode differential crossbar column | `I = V·G`, differential conductance, TIA readout and signed output agree with hand reference | done |
| 0008 | Circuit evidence → device profile | extract versioned SPICE-backed parameters and provenance from 0005/0007 | done |

`0008` is the bridge chapter: it proves that circuit evidence can become machine-readable parameters consumed downstream. Higher-level physical claims must not bypass this bridge.

## Part III — Converter signal path

| # | Chapter | Verification target | Status |
|---|---|---|---|
| 0009 | DAC architecture | transfer curve, range, gain/offset, settling and supply sensitivity characterized in SPICE | done |
| 0010 | ADC / TIA output path | transfer, clipping, noise, settling and effective precision characterized in SPICE | done |
| 0011 | Converter variation | Monte Carlo/corner evidence for mismatch and converter error | done |

## Part IV — Small physical crossbar arrays

| # | Chapter | Verification target | Status |
| 0012 | 2×2 differential crossbar | shared input rows and multiple columns agree with behavioral reference | done |
| 0013 | 4×4 differential crossbar | array-level MVM remains correct under circuit non-idealities | done |
| 0014 | Array timing and loading | column loading, TIA headroom and settling are bounded | done |

## Part V — Device realism

| # | Chapter | Verification target | Status |
|---|---|---|---|
| 0015 | Programmable conductance model | explicit cell/compact-model choice with `gmin/gmax` and state behavior provenance | done |
| 0016 | Programming/read variation | Monte Carlo distributions quantify mismatch and state uncertainty | done |
| 0017 | IR drop | line resistance error quantified versus array dimensions | done |
| 0018 | Parasitics | RC/settling impact extracted from circuit model | done |
| 0019 | Drift, stuck states and non-linearity | each supported mechanism modeled separately or explicitly excluded | done |
| 0020 | Crossbar-v1 profile | publish a validated profile with evidence classes, conditions and limitations | done |

## Part VI — Profile-driven accelerator architecture

| # | Chapter | Verification target | Status |
|---|---|---|---|
| 0021 | Physical tile contract | behavioral tile consumes validated DAC/ADC/crossbar profiles | done |
| 0022 | Partial sums | tiled result matches dense reference within profile-derived error | done |
| 0023 | Scheduler / temporal reuse | parallelism and rewrites are explicit and deterministic | done |
| 0024 | SRAM / buffers | capacity and traffic are accounted for | done |
| 0025 | NoC / interconnect | data movement enters timing/energy accounting | done |
| 0026 | Calibration | correction procedure improves simulated/measured error reproducibly | done |

## Part VII — Neural-network and Transformer mapping

| # | Chapter | Verification target | Status |
|---|---|---|---|
| 0027 | Linear layer | one dense layer maps exactly to the accelerator contract | done |
| 0028 | MLP | up/down projections preserve reference behavior within error budget | done |
| 0029 | Q/K/V projections | transformer projections route through the analog path correctly | done |
| 0030 | Attention boundary | static analog-friendly work and dynamic digital work are separated honestly | done |
| 0031 | KV cache | dynamic state capacity and traffic are explicitly modeled | done |
| 0032 | Transformer block | block-level error is attributable to named mechanisms | done |

## Part VIII — LLM inference and robustness

| # | Chapter | Verification target | Status |
|---|---|---|---|
| 0033 | Tiny transformer | deterministic float/reference and analog-path parity | done |
| 0034 | Full autoregressive path | token generation has complete architecture ledger | done |
| 0035 | Real pretrained checkpoint | model runs using profile-driven accelerator configuration | next |
| 0036 | Sensitivity and quantization | accuracy/cost trade-offs are reproducible with physical profiles |
| 0037 | Hardware-aware recovery | training/calibration recovery under verified non-idealities is measurable |

## Part IX — Physical feasibility

| # | Chapter | Verification target |
|---|---|---|
| 0038 | Latency ledger | timing coefficients are SPICE/derived/measured or explicitly assumed |
| 0039 | Energy / power ledger | coefficients carry evidence class and provenance |
| 0040 | Area / process model | area tied to explicit layout/process assumptions |
| 0041 | Thermal / power density | operating envelope receives sanity checks |
| 0042 | Integrated feasibility report | separates verified evidence, derived quantities and assumptions |

## Part X — Correlation with implementation

| # | Chapter | Verification target |
|---|---|---|
| 0043 | FPGA / digital shell | scheduler, buffers and control assumptions are executable independently |
| 0044 | PCB / board correlation | measured converter/crossbar behavior can replace SPICE evidence where available |
| 0045 | IC / tape-out readiness | open risks, required models, PDK/layout assumptions and missing evidence are explicit |

## Chapter completion rules

A chapter is not complete because prose or a plot exists.

- **Math / functional:** hand calculation + executable assertion + tests.
- **Circuit:** schematic/netlist/model + deterministic ngspice/PySpice or Xyce run + machine-readable result.
- **Profile bridge:** extracted values + provenance + evidence class + validator + downstream consumer test.
- **Device realism:** sweep/Monte Carlo/corner evidence + explicit model provenance.
- **Architecture:** deterministic simulator + ledger + profile-driven parameters.
- **Model:** float/reference comparison + accuracy/error report.
- **Physical feasibility:** latency/energy/area values with evidence classes and limitations.

The auditable chain is:

```text
equation → circuit → SPICE → validated profile → accelerator → LLM → feasibility report
```

See `docs/SIMULATION_STACK.md`, `docs/PRODUCT_SPEC.md`, and `docs/ROADMAP.md` for tooling and current implementation status.
