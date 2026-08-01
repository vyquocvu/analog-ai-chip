# Analog AI Machine

[![CI](https://github.com/vyquocvu/analog-ai-chip/actions/workflows/ci.yml/badge.svg)](https://github.com/vyquocvu/analog-ai-chip/actions/workflows/ci.yml)

**Build a modular analog neural computer at home, one circuit at a time.**

This repository is an executable DIY book for learning analog AI by building real low-voltage hardware: first one weighted sum, then a crossbar tile, then a USB-controlled modular machine capable of running tiny neural networks.

The project starts with breadboards, resistors, op-amps, ADCs, DACs, and microcontrollers. Actual ReRAM and custom silicon are advanced research modules, not prerequisites.

> The initial machine is a hybrid analog-digital educational accelerator. It demonstrates real analog matrix-vector multiplication, but it is not a fabricated ReRAM chip and does not claim to outperform GPUs.

## What you will build

```text
Laptop / Raspberry Pi
        │ USB / Serial
        ▼
Controller → DAC → Analog crossbar → Current summing → ADC
                          │
                    stackable tiles
```

The target machine is modular:

- a safe 5 V power and reference module;
- a microcontroller-based controller;
- DAC input channels;
- fixed-resistor and programmable-conductance crossbar tiles;
- transimpedance/current-summing outputs;
- ADC measurement channels;
- optional analog activation modules;
- a backplane for stacking multiple tiles;
- Python software for calibration, weight mapping, execution, and verification.

## Build path

| # | Build | Physical result | Status |
|---|---|---|---|
| 0000 | [Define the machine](book/0000-what-we-are-building) | System boundaries, modules, and safety rules | done |
| 0001 | [Build one analog neuron](book/0001-one-analog-neuron) | A breadboard weighted-sum circuit | started |
| 0002 | Build a 2×2 fixed crossbar | Real Ohm/Kirchhoff matrix-vector multiplication | planned |
| 0003 | Add signed weights | Differential G+ / G− paths | planned |
| 0004 | Add a microcontroller | Automated input and measurement | planned |
| 0005 | Add DAC and ADC modules | Repeatable digital-to-analog inference | planned |
| 0006 | Build a programmable 4×4 tile | Software-programmable weights | planned |
| 0007 | Calibrate the machine | Offset, gain, noise, and clipping correction | planned |
| 0008 | Run a tiny neural network | Hybrid analog-digital inference | planned |
| 0009 | Stack multiple tiles | Tiled layers and partial sums | planned |
| 0010 | Design the first PCB kit | Reproducible modular hardware | planned |
| 0011 | Experimental memory modules | Memristor/ReRAM evaluation devices | research |

The existing executable lessons under [`lessons/`](lessons) remain the mathematical and software foundation. The new [`book/`](book) path turns those ideas into physical builds.

## Repository layout

```text
analog-ai-chip/
├── book/               step-by-step DIY chapters
├── hardware/           schematics, KiCad projects, BOMs, assembly guides
├── firmware/           controller firmware and wire protocol
├── software/           host tools, compiler, calibration, and CLI
├── analog_ai/          reusable functional models
├── lessons/            executable theory and simulation lessons
├── experiments/        measured hardware results
├── maths/              plain-language reference shelf
├── tests/              deterministic software checks
└── docs/               architecture, module standard, safety, roadmap
```

## Chapter discipline

Every hardware chapter must include:

1. what is being built;
2. why the circuit works;
3. schematic and wiring diagram;
4. bill of materials;
5. expected voltages/currents;
6. firmware and host commands;
7. Python verification;
8. calibration procedure;
9. common failure modes;
10. measurements to record;
11. experiments to try;
12. an explicit statement of what the build does not prove.

## First target

The first complete release is **Homebrew Analog AI v0.1**:

- one USB-connected controller;
- one 4×4 signed-weight tile;
- low-voltage operation;
- automated calibration;
- Python CLI;
- a reproducible tiny classifier demo;
- open schematics, firmware, BOM, and measurement data.

## Safety and scope

The project is intentionally limited to low-voltage circuits powered from USB or a current-limited bench supply. Do not connect breadboards directly to mains electricity. See [`docs/SAFETY.md`](docs/SAFETY.md).

The project distinguishes carefully between:

- resistor/digital-pot crossbars and actual ReRAM devices;
- functional models and circuit simulation;
- one resident crossbar operation and end-to-end model latency;
- educational measurements and competitive accelerator benchmarks.

## Run the software foundation

```bash
python -m pip install -e '.[dev]'
pytest
python lessons/0001-crossbar-mvm/train.py
```

## License

MIT. See [LICENSE](LICENSE).
