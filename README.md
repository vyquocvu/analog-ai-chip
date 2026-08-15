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

The repository has closed the first five evidence gates:

```text
R0 functional + circuit foundation ── COMPLETE
R1 circuit → profile → simulator   ── COMPLETE  (crossbar-column-v1)
R2 converter signal path           ── COMPLETE  (dac-r2r-v1, adc-sar-v1)
R3 small crossbar arrays           ── COMPLETE  (0012 2×2 + 0013 4×4, behavioral-equivalence report)
R4 device realism + crossbar-v1    ── COMPLETE  (crossbar-v1, 2D mesh, variation, IR drop, RC settling, drift/faults)
```

The circuit → profile → simulator chain is closed: `device_profiles/crossbar-column-v1.json` and `device_profiles/crossbar-v1.json` are extracted from SPICE solves and distributed 2D nodal analyses, and `analog_llm` builds its tiles through `profile_adapter` — no hand-copied physical constants. The converter path is closed by the SPICE-verified R-2R DAC (`dac-r2r-v1`) and SAR ADC (`adc-sar-v1`) profiles, consumed through `converter_config_from_profiles`.

`book/0007-crossbar-column/` and `book/0020-crossbar-v1/` are the circuit chapters matching the current-mode differential conductance architecture modeled by `analog_llm`: conductance cells generate `I = V·G`, column currents sum, and TIA/differential readout produces the signed result.

The **active roadmap gate is R5: profile-driven physical tile** — multi-tile partial sums, spatial scheduling, and SRAM/interconnect traffic accounting on calibrated device profiles. See [`docs/ROADMAP.md`](docs/ROADMAP.md).

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
| 0008 | Circuit evidence → device profile | done | `verification/circuit/` + `device_profiles/` |
| 0009 | DAC architecture | done | `book/0009-dac-r2r/` |
| 0010 | ADC / TIA output path | done | `book/0010-adc-sar/` |
| 0011 | Converter variation | done | `book/0011-converter-variation/` |
| 0012 | 2×2 differential crossbar | done | `book/0012-crossbar-2x2/` |
| 0013 | 4×4 differential crossbar | done | `book/0013-crossbar-4x4/` |
| 0014 | Array timing and loading | done | `book/0014-array-timing/` |
| 0015 | Programmable conductance compact model | done | `book/0015-conductance-model/` |
| 0016 | Programming and read variation | done | `book/0016-variation/` |
| 0017 | IR drop and line resistance | done | `book/0017-ir-drop/` |
| 0018 | Parasitic capacitance and RC settling | done | `book/0018-parasitics/` |
| 0019 | Drift, stuck states and non-linearity | done | `book/0019-drift-faults/` |
| 0020 | Crossbar-v1 profile and Gate R4 close | done | `book/0020-crossbar-v1/` |

> **Tiếng Việt:** every chapter has a `README.vi.md` beside the English `README.md`.

## Track 2 — Analog LLM architecture simulator (`analog_llm/`)

A decoder-only transformer runs end to end in software. Dense matrix-vector operations are routed through simulated crossbar tiles; layer norm, softmax, GELU, residual/bias operations and embeddings remain digital.

```text
Prompt tokens
     ↓
Token embedding (digital table)
     ↓
┌────────────────────────────────────────────────────────┐
│ Transformer layer × N                                  │
│   ├── RMSNorm / LayerNorm (digital FP32)               │
│   ├── QKV projection (analog CrossbarTiles)            │
│   ├── Scaled dot-product attention + KV cache (digital)│
│   ├── Output projection (analog CrossbarTiles)         │
│   ├── Residual addition (digital FP32)                 │
│   ├── RMSNorm / LayerNorm (digital FP32)               │
│   ├── MLP / Feed-Forward up+gate (analog CrossbarTiles)│
│   ├── GELU / SiLU activation (digital FP32)            │
│   ├── MLP down projection (analog CrossbarTiles)       │
│   └── Residual addition (digital FP32)                 │
└────────────────────────────────────────────────────────┘
     ↓
Final norm + LM head (analog or digital)
     ↓
Greedy / top-p sampler → next token
```

## Track 3 — Device profiles (`device_profiles/`)

Every physical claim made by the simulator must consume a machine-readable profile derived from KiCad/ngspice/Xyce verification, a validated analytical derivation, or an explicitly stated sensitivity-study assumption.

Evidence classes:

- `measured` — physical hardware measurement;
- `spice` — extracted from a named circuit simulation;
- `derived` — calculated from traceable evidence;
- `assumed` — sensitivity-study input only.

The repository contains the validated SPICE-backed profiles `crossbar-column-v1`, `crossbar-v1`, `dac-r2r-v1` and `adc-sar-v1`, all consumed by `analog_llm` through `profile_adapter` (fail-closed: `assumed`/functional-only evidence cannot support a physical claim). The next milestone is multi-tile architecture integration on calibrated profiles (roadmap R5).

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

## Python Environment Setup Guide

### 1. Prerequisites
- **Python 3.9+** (`python3 --version`)
- **Git** (`git --version`)
- *(Optional for circuit SPICE sweeps)*: `ngspice` / `libngspice`

### 2. Step-by-Step Installation

#### Step 1: Clone the repository
```bash
git clone https://github.com/vyquocvu/analog-ai-chip.git
cd analog-ai-chip
```

#### Step 2: Create and activate a virtual environment
- **macOS / Linux**:
  ```bash
  python3 -m venv .venv
  source .venv/bin/activate
  ```
- **Windows (PowerShell)**:
  ```powershell
  python -m venv .venv
  .venv\Scripts\Activate.ps1
  ```

#### Step 3: Install Python dependencies

Choose the target configuration for your workflow:

- **Core & Development** (Unit tests, linter, NumPy, model simulation):
  ```bash
  pip install --upgrade pip
  pip install -e '.[dev]'
  ```

- **Full Simulation Stack** (Adds PySpice for circuit simulation and extraction):
  ```bash
  pip install -e '.[dev,sim]'
  ```

#### Step 4: (Optional) Install `ngspice` for Circuit Simulation
If running or extracting SPICE netlists (`book/0005`–`0014`, `verification/circuit/`):

- **macOS (Homebrew)**:
  ```bash
  brew install libngspice ngspice
  ```
  *(The codebase automatically detects `/opt/homebrew/lib/libngspice.dylib` or `/usr/local/lib/libngspice.dylib`)*

- **Ubuntu / Debian**:
  ```bash
  sudo apt-get update && sudo apt-get install -y libngspice0-dev ngspice
  ```

### 3. Verify Installation

Run the test suite and quality checks:
```bash
# 1. Run all unit tests (233 tests across math, circuits, profiles, and LLM)
pytest

# 2. Run code style & static analysis
ruff check .

# 3. Execute the profile-driven TinyGPT analog accelerator simulation
python scripts/run_llm_sim.py
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
