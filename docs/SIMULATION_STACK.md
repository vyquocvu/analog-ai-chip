# Simulation & Verification Stack

The project designs and verifies an analog AI accelerator from first principles. The goal is not merely to reproduce matrix multiplication in NumPy; it is to build an evidence chain showing that a proposed circuit and architecture can plausibly operate as physical hardware.

## Toolchain

```text
KiCad schematic / circuit design
          ↓
SPICE netlist
          ↓
PySpice automation
   ├── ngspice   default circuit simulator
   └── Xyce      large-array / parallel SPICE
          ↓
parameter extraction + sweeps + Monte Carlo
          ↓
device_profiles/*.json
          ↓
analog_llm architecture simulator
          ↓
Transformer / LLM inference
          ↓
verification report
```

### KiCad

Use KiCad for reproducible schematics and, later, PCB/layout artifacts. A schematic is a design artifact; it is not evidence until its operating points and relevant analyses have been simulated.

### ngspice

ngspice is the default circuit simulator for small and medium blocks: weighted summers, DAC/ADC front ends, op-amp stages, crossbar cells, small arrays, DC sweeps, transient response, AC/noise analysis, and compact-device models.

### PySpice

PySpice is the automation layer. Python scripts should generate or load netlists, run deterministic sweeps, extract machine-readable measurements, compare them with analytical/NumPy references, and emit profile data. SPICE plots alone are insufficient evidence when the same values can be asserted automatically.

### Xyce

Use Xyce when array size, parasitics, Monte Carlo volume, or circuit scale make ngspice impractical. Xyce is an alternate backend, not a different source of truth: the extracted quantities and profile schema remain the same.

### NumPy / PyTorch

Use NumPy/PyTorch for functional references, architecture-level simulation, model mapping, sensitivity studies, and LLM inference. These tools do not establish circuit feasibility by themselves.

## Verification ladder

1. **Analytical** — hand-computable equation and units.
2. **Functional** — deterministic NumPy reference.
3. **Behavioral analog** — quantization, clipping, conductance limits and explicit non-idealities.
4. **Circuit** — SPICE operating point/DC/transient/noise evidence.
5. **Variation** — parameter sweeps, Monte Carlo and temperature/supply/device corners when models permit.
6. **Extracted profile** — circuit/device results serialized with provenance.
7. **Architecture** — tile count, scheduling, partial sums, buffers, traffic and physical ledger.
8. **Model** — logits, token agreement, perplexity/accuracy against a digital baseline.
9. **Feasibility** — latency, energy, area and thermal estimates with assumptions explicitly separated from measurements.

Passing a higher level never retroactively proves a missing lower level.

## Provenance rule

A parameter used for a physical or system-level claim must be one of:

- `measured`: from real hardware measurement;
- `spice`: extracted from a named circuit simulation and model;
- `derived`: computed from cited measured/SPICE inputs;
- `assumed`: an explicit design assumption used only for sensitivity analysis.

`assumed` values must never be presented as verified hardware properties.

Every reusable device profile must record its source files, simulator, analysis type, environment/corners, extraction script or command, and evidence class. See `device_profiles/README.md`.

## Circuit-to-system contract

The architecture simulator should consume extracted profiles rather than inventing physical values inline. For example:

```text
SPICE ADC model
  → ENOB / range / offset / gain error / noise / settling
  → device_profiles/adc-*.json
  → analog_llm converter configuration
  → model-accuracy and latency sensitivity
```

The same applies to conductance ranges, programming variation, read noise, drift, IR drop approximations, output-stage headroom and settling.

## What counts as evidence

A completed verification item should include, where applicable:

- source schematic/netlist or compact model;
- deterministic simulation script;
- asserted expected quantities and tolerances;
- raw or summarized machine-readable results;
- plots/diagrams generated from those results;
- a profile with provenance;
- a downstream test demonstrating that the architecture simulator consumed the profile.

The final status language should distinguish at least:

- `FUNCTIONAL_ONLY`
- `CIRCUIT_SIMULATED`
- `VARIATION_SIMULATED`
- `SYSTEM_SIMULATED`
- `HARDWARE_MEASURED`

Until physical measurements exist, the project may claim simulation-backed feasibility, never silicon verification.