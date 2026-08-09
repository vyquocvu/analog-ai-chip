# Contributor instructions

This repository designs and verifies an analog in-memory-computing accelerator from circuit primitives through language-model inference. The goal is a traceable simulation-backed feasibility case, not merely a software approximation of analog math.

Read `README.md`, `docs/ROADMAP.md`, `docs/PRODUCT_SPEC.md`, `docs/SIMULATION_STACK.md`, and the target module + tests before editing.

For every new model or feature:

1. Start from a tiny hand-computable example and encode it in an assertion.
2. State physical assumptions and units (voltage, current, conductance, bits, time, scale).
3. Keep claim levels separate:
   - *functional*: what the math/software mapping does;
   - *circuit/device*: what a schematic, converter, crossbar, or device model does in SPICE;
   - *system*: end-to-end latency, energy, area, traffic, and model accuracy.
4. Use the verification ladder in `docs/SIMULATION_STACK.md`: analytical → functional → behavioral → SPICE → variation/corners → extracted profile → architecture → model → feasibility.
5. Simulate non-idealities explicitly. Never hide resolution, noise, clipping, variation, gain/offset, IR drop, drift, or timing behind a generic scalar "error" when the mechanism is known.
6. Physical/system parameters consumed by `analog_llm/` must come from a validated `device_profiles/` entry or be explicitly labeled `assumed`.
7. `assumed` values are allowed for sensitivity studies but cannot support a physical claim. Preserve provenance: tool, source model/netlist, analysis, conditions, extraction command, units, and limitations.
8. Prefer ngspice + PySpice for reproducible circuit verification. Use Xyce when circuit/array size or parallel sweeps justify it. Use KiCad for schematic/layout design artifacts.
9. Never describe NumPy/PyTorch execution as physical analog acceleration or SPICE evidence.
10. Do not derive end-to-end `O(1)` or an energy/latency advantage from one ideal crossbar operation. Reports must quote the physical ledger and distinguish simulated, derived, assumed, and measured quantities.
11. Add deterministic tests for the happy path and at least one invalid/boundary case. Provenance validation must fail closed.
12. Update `docs/ROADMAP.md` only when executable evidence exists.

Evidence should be reproducible as source schematic/netlist/model + script + machine-readable result + generated visualization where applicable.

Run `ruff check .` and `pytest` before submitting changes.
