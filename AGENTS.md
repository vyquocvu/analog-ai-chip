# Contributor instructions

This repository models an analog in-memory-computing product that runs language
models, entirely in simulation. All models are software, so any claim that
sounds like "this is faster / more efficient than a GPU" must be avoided unless
backed by a measured (not assumed) ledger.

Read `README.md`, `docs/ROADMAP.md`, `docs/PRODUCT_SPEC.md`, and the target
module + tests before editing.

For every new model or feature:

1. Start from a tiny hand-computable example and encode it in an assertion.
2. State the physical assumptions and units (voltage, conductance, bits, scale).
3. Keep three levels of claim separate:
   - *functional*: what the math does;
   - *circuit/device*: what a crossbar or converter physically does;
   - *system*: end-to-end latency / energy / accuracy of the product.
4. Simulate non-idealities explicitly. Never hide converter resolution, noise,
   clipping, or gain/offset behind a single scalar "error".
5. Use small dependencies, fixed random seeds, and fail-closed validation.
6. Never describe NumPy computation as physical analog acceleration.
7. Do not derive end-to-end `O(1)` or an energy/latency advantage from one ideal
   crossbar operation; every report must quote the physical ledger (MACs, tile
   MVM cycles, rewrites) and state its assumptions.
8. Add tests for the happy path and at least one invalid or boundary case.
9. Update `docs/ROADMAP.md` only when executable evidence exists.

Run `ruff check .` and `pytest` before submitting changes.
