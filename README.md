# Analog AI Chip

[![CI](https://github.com/vyquocvu/analog-ai-chip/actions/workflows/ci.yml/badge.svg)](https://github.com/vyquocvu/analog-ai-chip/actions/workflows/ci.yml)

Analog AI Chip is an executable book for learning ReRAM crossbars, analog in-memory computing (AIMC), and the architecture of practical AI accelerators.

The method is simple: predict the result, calculate a tiny example by hand, reproduce it in Python, then deliberately introduce a hardware non-ideality and study what changes. Assertions connect the equations in each chapter to runnable code.

> This repository models analog compute behavior; it does not claim that a digital PyTorch or NumPy operation is a transistor-level circuit simulation.

## Lessons

| # | Lesson | You compute by hand | Status |
|---|---|---|---|
| 0001 | [Ohm + Kirchhoff = matrix-vector multiplication](lessons/0001-crossbar-mvm) | A 2×2 crossbar from voltages and conductances | done |
| 0002 | [Signed weights with differential pairs](lessons/0002-differential-pairs) | Mapping positive and negative weights to G+ and G− | done |
| 0003 | [DAC, ADC, quantization, and noise](lessons/0003-converters-and-noise) | Quantization error and noisy inference | done |
| 0004 | [Tiling a matrix across physical arrays](lessons/0004-tiling) | Partial sums for a matrix larger than one crossbar | done |
| 0005 | Static LLM layers on ReRAM | GPT-style projections and MLP layers | planned |
| 0006 | Dynamic attention and KV cache | What cannot be preloaded as static conductance | planned |
| 0007 | Energy and latency ledger | ADC/DAC, memory, NoC, and accumulation costs | planned |
| 0008 | Hardware-aware fine-tuning | Recovering accuracy under non-idealities | planned |

## Run it

```bash
python -m pip install -e '.[dev]'
pytest
python lessons/0001-crossbar-mvm/train.py
python lessons/0004-tiling/train.py
```

Python 3.11+ and NumPy are sufficient for the first four lessons.

## Layout

```text
analog-ai-chip/
├── analog_ai/          reusable functional models
├── lessons/            executable chapters
├── maths/              plain-language reference shelf
├── tests/              independent checks for book arithmetic
├── docs/ROADMAP.md     curriculum and implementation roadmap
├── pyproject.toml
└── .github/workflows/  CI for lessons and package tests
```

Each completed lesson contains a readable `README.md` and a `train.py` program whose assertions reproduce the chapter's hand calculations.

## Scope

The project begins at the device/array abstraction and grows toward system architecture. It distinguishes carefully between:

- ideal crossbar MVM and end-to-end transformer latency;
- static model weights and dynamic activations/KV cache;
- functional error models and circuit-accurate simulation;
- theoretical parallelism and physical ADC/DAC/interconnect costs.

## License

MIT. See [LICENSE](LICENSE).
