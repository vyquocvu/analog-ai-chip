# Product Specification — Analog LLM Accelerator (simulation-verified design)

Status: draft for v0.1. The product is a hybrid analog-digital accelerator concept for running a decoder-only language model. The repository aims to establish simulation-backed physical feasibility by tracing system parameters to circuit/device evidence wherever possible.

Nothing here is a claim of fabricated silicon performance.

## 1. Purpose

Dense matrix-vector multiplications — attention QKV, attention output, MLP up/down, and the head — are mapped onto programmable-conductance crossbar tiles. Layer norm, softmax, GELU, residual/bias adds, control, and embedding lookup remain digital unless a later design explicitly replaces them.

The design is verified at multiple levels:

1. analytical and NumPy functional reference;
2. behavioral non-ideal model;
3. SPICE circuit simulation;
4. variation/corner analysis;
5. circuit/device parameter extraction;
6. architecture and model-level simulation;
7. feasibility reporting.

See `docs/SIMULATION_STACK.md`.

## 2. Matrix convention

For every linear layer compute `y = W @ x` with:

- each input element driving one crossbar row through a DAC/input stage;
- each output collected from one crossbar column through an output stage/ADC;
- weights stored as `[output, input]`.

Signed weights use differential encoding:

```text
W_eff ∝ G_pos - G_neg
```

The proportionality, conductance window, converter ranges and gain stages must be explicit in any physical profile.

## 3. Circuit-to-system profile contract

Physical/system parameters must not be silently embedded as convenient constants. `analog_llm/` should consume validated entries from `device_profiles/` for any run intended to represent a proposed physical implementation.

Evidence classes:

| Class | Meaning | May support physical claim? |
|---|---|---|
| `measured` | extracted from real hardware | yes |
| `spice` | extracted from named circuit/device simulation | yes, simulation-backed |
| `derived` | computed from traceable inputs | yes, with derivation |
| `assumed` | design/sensitivity assumption | no |

Each profile records tool, source model/netlist, analysis, conditions, extraction command, units and limitations.

## 4. Non-ideal component model

Target mechanisms include:

| Block | Non-idealities / quantities |
|---|---|
| Weight storage | `gmin/gmax`, finite states, programming variation, read variation, drift, stuck states |
| Input DAC | resolution/ENOB, range, clipping, offset/gain error, INL/DNL when modelled, settling |
| Crossbar/interconnect | differential subtraction, line resistance, IR drop, parasitic capacitance, sneak/current-path effects where applicable |
| Output stage / ADC | range, resolution/ENOB, clipping, noise, offset/gain error, settling, bandwidth |
| Supply / environment | supply variation, temperature and device/process-model corners |

A mechanism may be absent from an early milestone, but its absence must be explicit. Unknown behavior is not zero behavior.

## 5. Simulation tools

- KiCad: schematic and later layout/PCB design artifacts.
- ngspice: default small/medium circuit backend.
- PySpice: Python automation and machine-readable extraction.
- Xyce: larger arrays and parallel SPICE workloads.
- NumPy/PyTorch: functional, architecture and model-level simulation.

SPICE and external binaries are installed separately from the Python package.

## 6. Signal envelope

Normalized values may be used for functional studies. A run intended to support physical feasibility must instead obtain voltage/conductance/current/time ranges from a validated profile.

The current functional reference uses values such as:

- normalized input range around `[-1, 1]`;
- configurable differential conductance resolution;
- configurable DAC/ADC bit depth and clipping;
- configurable output-stage noise/gain/offset.

These are not hardware properties unless backed by profile provenance.

## 7. Physical ledger

Every architecture run must report at minimum:

- useful MACs;
- physical tile MVM operations/cycles under stated parallelism;
- tile programming / rewrites;
- tiles used;
- digital partial-sum operations.

As the design matures, add:

- converter operations and settling assumptions;
- SRAM/buffer capacity and traffic;
- NoC/interconnect traffic;
- estimated latency;
- estimated energy;
- area and thermal assumptions.

Every number must be tagged or traceable as measured, SPICE-derived, derived, or assumed.

## 8. Module boundary

| Module | Scope |
|---|---|
| `converters` | behavioral DAC/ADC model |
| `crossbar` | weight-to-conductance mapping and MVM |
| `tile` | one physical-array abstraction |
| `accelerator` | tiling, scheduling, partial sums, reuse and ledger |
| `device_profile` | provenance validation for circuit/device parameters |
| `transformer` | TinyGPT / imported-model hybrid forward |
| `report` | configuration, accuracy and physical-ledger reporting |

## 9. Verification status

Reports should use explicit status language:

- `FUNCTIONAL_ONLY`
- `CIRCUIT_SIMULATED`
- `VARIATION_SIMULATED`
- `SYSTEM_SIMULATED`
- `HARDWARE_MEASURED`

A system-level simulation built from `assumed` component values remains a sensitivity study; it is not promoted to circuit-verified simply because an LLM executes successfully.

## 10. Acceptance

- `pytest` and `ruff check .` pass.
- A high-precision, noiseless accelerator reproduces the float baseline
  (token agreement ~1.0, logit error ~0) on the tiny model — this validates
  correct tiling and mapping, not a fabrication claim.
- A budget-constrained accelerator shows monotone, bounded degradation so the
  sensitivity to each non-ideality is visible.
- Every reported metric states its assumptions and units.

## 8. Frozen v0.1 reporting format

The report format below is frozen for v0.1 so every claim is comparable,
auditable, and honest. A report must state at minimum:

**Accuracy (vs float baseline, fixed seed):**
- `token agreement`: fraction of generated positions matching the float model;
- `max |logißt error|`: max absolute logit difference over the traced sequence.

**Physical ledger (per run):**
- `macs`: resolved differential conductance cells executed (only `G+ - G-`);
- `tile cycles`: lower bound on sequential block-MVM cycles,
  `ceil(blocks / tile_count)` per MVM, summed;
- `rewrites`: number of physical tiles re-programmed (temporal reuse);
- `programs`: number of weight blocks programmed onto tiles (`>= rewrites`).

**Invariants (enforced by `analog_llm/guardrail.py` and the demo scripts):**
- Every number is a *simulation* quantity in its stated units; no wall-clock or
  energy value may be presented as measured; the system estimate uses relative
  units (`tu`/`eu`) from supplied assumptions, never a GPU comparison.
- No performance claim (faster-than / GPU-equivalent / O(1) compute/energy)
  may appear without a measured, committed ledger + explicit disclaimer.
- Every run is deterministic (fixed seed) and fail-closed on invalid inputs.
