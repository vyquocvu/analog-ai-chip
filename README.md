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
validated device profiles
  ↓
profile-driven accelerator
  ↓
Transformer / LLM inference
  ↓
physical feasibility report
```

## Current status

The repository has completed the functional foundations and its first SPICE-verified current-mode compute primitive:

```text
0005 voltage-mode weighted sum ─┐
0006 multi-neuron scaling       ├─► circuit foundation
0007 differential crossbar col ┘
                                  ↓
                         NEXT: extract SPICE profile
                                  ↓
                            analog_llm consumes it
```

`book/0007-crossbar-column/` is the first circuit chapter that matches the current-mode differential conductance architecture modeled by `analog_llm`: conductance cells generate `I = V·G`, column currents sum, and TIA/differential readout produces the signed result.

The **active roadmap gate is R1: close the circuit → profile → simulator proof chain**. See [`docs/ROADMAP.md`](docs/ROADMAP.md).

## Engineering hierarchy

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

See [`docs/CURRICULUM.md`](docs/CURRICULUM.md) for the canonical chapter sequence and [`docs/ROADMAP.md`](docs/ROADMAP.md) for implementation gates.

## Simulation stack

- **KiCad** — schematic and later PCB/layout design artifacts.
- **ngspice** — default SPICE backend for circuit verification, sweeps, transient/noise analysis and compact models.
- **PySpice** — Python automation, assertions, extraction and reproducible experiment orchestration.
- **Xyce** — large-array / parallel SPICE backend when ngspice becomes impractical.
- **NumPy / PyTorch** — functional references, architecture simulation, model mapping and accuracy studies.

See [`docs/SIMULATION_STACK.md`](docs/SIMULATION_STACK.md).

---

## Track 1 — Sequential design book (`book/`)

| # | Topic | Status | Path |
|---|---|---|---|
| 0000 | System and verification boundaries | done | `book/0000-what-we-are-building/` |
| 0001 | Ohm + Kirchhoff = MVM | done | `book/0001-crossbar-mvm/` |
| 0002 | Signed differential weights | done | `book/0002-differential-pairs/` |
| 0003 | DAC/ADC quantization and noise | done | `book/0003-converters-and-noise/` |
| 0004 | Tiling a matrix across arrays | done | `book/0004-tiling/` |
| 0005 | One analog neuron — SPICE | done | `book/0005-one-analog-neuron/` |
| 0006 | Many neurons / scaling | done | `book/0006-many-neurons/` |
| 0007 | Current-mode differential crossbar column | done | `book/0007-crossbar-column/` |
| 0008 | Circuit evidence → device profile | **next** | planned |
| 0009 | DAC architecture | queued | planned |
| 0010 | ADC / TIA output path | queued | planned |
| 0012 | 2×2 differential crossbar | queued | planned |
| 0013 | 4×4 differential crossbar | queued | planned |

> **Tiếng Việt:** chapters include `README.vi.md` beside the English `README.md` where available.

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

Existing transformer/LLM code is a functional architecture foundation. It is **not yet the source of physical truth**. Physical/system claims become eligible only when the simulator consumes validated profiles extracted from circuit/device evidence.

```bash
python scripts/run_llm_sim.py
```

## Device profiles and provenance

`device_profiles/` is the bridge between circuit simulation and the architecture simulator.

Evidence classes:

- `measured` — physical hardware measurement;
- `spice` — extracted from a named circuit simulation;
- `derived` — calculated from traceable evidence;
- `assumed` — sensitivity-study input only.

The current repository contains the profile contract and an ideal reference profile. The next milestone is to publish the first **SPICE-backed crossbar-column profile** from 0007 and make `analog_llm` consume it.

## Verification evidence

Preferred evidence chain:

```text
source schematic/netlist/model
      + deterministic script
      + machine-readable result
      + generated figure
      + validated device profile
      + downstream consumer test
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
# install ngspice separately; use Xyce when circuit scale requires it
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
