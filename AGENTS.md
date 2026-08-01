# Contributor instructions

Read `README.md`, `docs/ROADMAP.md`, the target lesson, and the relevant package/tests before editing.

For every lesson:

1. Start from a tiny hand-computable example.
2. State physical assumptions and units.
3. Keep functional, circuit, and system-level claims separate.
4. Add deterministic code with assertions matching the written arithmetic.
5. Add tests for the happy path and at least one invalid or boundary case.
6. Never describe NumPy/PyTorch execution as physical analog acceleration.
7. Do not claim end-to-end `O(1)` complexity from one ideal crossbar operation.
8. Update `docs/ROADMAP.md` only when executable evidence exists.

Use small dependencies, fixed random seeds, and fail-closed validation. Run `ruff check .` and `pytest` before submitting changes.
