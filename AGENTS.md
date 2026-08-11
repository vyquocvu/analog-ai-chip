# Contributor instructions

This repository designs and simulates an analog in-memory-computing machine from first principles through LLM inference. The canonical dependency order is `docs/CURRICULUM.md`; implementation readiness is tracked by evidence gates in `docs/ROADMAP.md`.

Read `README.md`, `docs/CURRICULUM.md`, `docs/ROADMAP.md`, `docs/SIMULATION_STACK.md`, `docs/PRODUCT_SPEC.md`, and the target module + tests before editing.

## Work selection

1. Select the first incomplete work package in the **Active** roadmap gate whose dependencies are proven.
2. Do not start a queued physical-verification gate merely because higher-level functional code already exists.
3. One PR should close one meaningful vertical slice with deterministic evidence.
4. If the required circuit/device model or simulator evidence is unavailable, report the blocker or label the parameter `assumed`; never silently promote it to verified evidence.
5. Existing higher-level code may be used as a consumer/reference, but it does not satisfy missing lower-level gates.

## Engineering rules

For every new model or feature:

1. Work in dependency order. Do not introduce a higher-level physical claim before its lower-level evidence exists or is explicitly marked as assumed.
2. Start from a tiny hand-computable example and encode it in an assertion.
3. State physical assumptions and units: voltage, current, conductance, resistance, bits, scale, temperature/supply/process where relevant.
4. Keep three levels of claim separate:
   - *functional*: what the math/software does;
   - *circuit/device*: what SPICE, compact models, or measurements support;
   - *system*: end-to-end latency, energy, area, traffic and model accuracy.
5. Simulate non-idealities explicitly. Never hide known converter resolution, noise, clipping, gain/offset, variation, IR drop, drift or parasitics behind one generic scalar error.
6. Physical/system parameters must carry provenance through `device_profiles/`: `measured`, `spice`, `derived`, or `assumed`.
7. `assumed` and functional-only profiles may be used for sensitivity studies but must fail closed when used to support a verified physical claim.
8. Prefer the stack in `docs/SIMULATION_STACK.md`: KiCad artifacts → ngspice/PySpice → Xyce when scaling demands it → extracted machine-readable profiles → NumPy/PyTorch architecture/model simulation.
9. Use small dependencies, fixed random seeds, deterministic sweeps, and fail-closed validation.
10. Never describe NumPy/PyTorch execution as physical analog acceleration.
11. Do not derive end-to-end `O(1)` or an energy/latency advantage from one ideal crossbar operation; every report must quote the physical ledger and state assumptions/evidence classes.
12. Add tests for the happy path and at least one invalid or boundary case.
13. A plot alone is not verification evidence. Prefer source schematic/netlist/model + deterministic script + machine-readable result + generated figure + validated profile + downstream consumer test.
14. Update `docs/ROADMAP.md` only after evidence exists; update `docs/CURRICULUM.md` only when the canonical dependency structure changes.

Run `ruff check .` and `pytest` before submitting changes.
