# Analog AI Machine

[![CI](https://github.com/vyquocvu/analog-ai-chip/actions/workflows/ci.yml/badge.svg)](https://github.com/vyquocvu/analog-ai-chip/actions/workflows/ci.yml)

**Design and simulate an analog AI accelerator from first principles — from Ohm's law and SPICE circuits to crossbar tiles and language-model inference.**

The repository is built around one engineering question:

> Can the proposed analog AI architecture plausibly operate as a physical device, and can every system-level parameter be traced back to circuit/device evidence or an explicitly labeled assumption?

The project does not claim silicon verification. It builds a reproducible proof chain:

```text
equation
  ↓
functional reference
  ↓
circuit design
  ↓
ngspice / Xyce
  ↓
variation + parameter extraction
  ↓
device_profiles
  ↓
analog_llm architecture simulator
  ↓
Transformer / LLM inference
  ↓
physical feasibility report
```

## Simulation stack

- **KiCad** — schematic and later PCB/layout design artifacts.
- **ngspice** — default SPICE backend for circuit verification, sweeps, transient/noise analysis and compact models.
- **PySpice** — Python automation, assertions, extraction and reproducible experiment orchestration.
- **Xyce** — large-array / parallel SPICE backend when ngspice becomes impractical.
- **NumPy / PyTorch** — functional references, architecture simulation, model mapping and accuracy studies.

See [`docs/SIMULATION_STACK.md`](docs/SIMULATION_STACK.md) for the verification ladder and evidence rules.

---

## Track 1 — Sequential design book (`book/`)

The book builds the machine in dependency order. Early chapters establish the math and behavioral model; later chapters turn those assumptions into circuit simulations and increasingly realistic device/array/system models.

| # | Topic | Path |
|---|---|---|
| 0000 | System and verification boundaries | `book/0000-what-we-are-building/` |
| 0001 | Ohm + Kirchhoff = MVM | `book/0001-crossbar-mvm/` |
| 0002 | Signed differential weights | `book/0002-differential-pairs/` |
| 0003 | DAC/ADC, quantization, noise | `book/0003-converters-and-noise/` |
| 0004 | Tiling a matrix across arrays | `book/0004-tiling/` |
| 0005 | One analog neuron — SPICE | `book/0005-one-analog-neuron/` |
| 0006 | Many neurons: a layer | `book/0006-many-neurons/` |

Chapter 0005 already verifies the weighted-sum circuit with PySpice + ngspice and explores non-ideal op-amp behavior, rail clipping and headroom. The next design work should progressively replace normalized/assumed parameters with circuit-derived profiles.

> **Tiếng Việt:** each book chapter has `README.vi.md` beside the English `README.md` where available.

```bash
python book/0001-crossbar-mvm/train.py
python book/0002-differential-pairs/train.py
python book/0003-converters-and-noise/train.py
python book/0004-tiling/train.py
```

## Track 2 — Analog LLM architecture simulator (`analog_llm/`)

A decoder-only transformer runs end to end in software. Dense matrix-vector operations are routed through simulated crossbar tiles; layer norm, softmax, GELU, residual/bias operations and embeddings remain digital.

```text
tokens ─► embedding
          └─► [LN ─► QKV ─► attention ─► out ─► LM]
                    └► [LN ─► MLP up ─► GELU ─► MLP down]
                                │
                         dense linears via
                     DAC → crossbar → ADC
```

The architecture simulator is not the source of physical truth. For physical/system claims it should consume validated entries from [`device_profiles/`](device_profiles) whose values are extracted from SPICE, derived from traceable evidence, or explicitly marked as assumptions.

```bash
python scripts/run_llm_sim.py
```

## Device profiles and provenance

`device_profiles/` is the bridge between circuit simulation and the product simulator.

Evidence classes:

- `measured` — physical hardware measurement;
- `spice` — extracted from a named circuit simulation;
- `derived` — calculated from traceable evidence;
- `assumed` — sensitivity-study input only.

The validator intentionally rejects an `assumed` or `FUNCTIONAL_ONLY` profile when code attempts to use it as support for a physical claim.

## Verification evidence

Use [`verification/`](verification) for reproducible evidence grouped by level: functional, circuit, Monte Carlo, corners, architecture, model accuracy and generated reports.

Preferred artifact chain:

```text
source schematic/netlist/model
      + deterministic script
      + machine-readable result
      + generated figure
      + validated device profile
```

A plot without reproducible source/result data is not sufficient evidence.

## Install and verify

```bash
python -m pip install -e '.[dev]'
pytest
ruff check .
python scripts/run_llm_sim.py
```

Optional circuit automation:

```bash
python -m pip install -e '.[sim]'
# install ngspice separately; install Xyce when large-circuit runs need it
```

## Honesty principles

- Keep *functional*, *circuit/device*, and *system* claims separate.
- Never describe NumPy/PyTorch execution as physical analog acceleration.
- Never infer end-to-end `O(1)` latency from one resident crossbar operation.
- Never turn an assumed ADC/crossbar parameter into a verified hardware claim.
- Every feasibility report must identify what is simulated, derived, assumed, and measured.

Until physical measurements exist, the strongest supported status is **simulation-backed physical feasibility**, not silicon verification.

## License

MIT. See [LICENSE](LICENSE).
