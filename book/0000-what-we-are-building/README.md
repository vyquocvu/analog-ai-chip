# 0000 — What We Are Building

The goal is not to fabricate a modern AI chip in a garage. The goal is to build a small modular neural computer whose matrix-vector multiplication physically happens through voltages, conductances, and summed currents.

## The machine

```text
Host computer
    |
    | USB / serial
    v
Controller ---- calibration storage
    |
    v
DAC/input driver
    |
    v
Analog conductance tile
    |
    v
Current-to-voltage stage
    |
    v
ADC/measurement
    |
    +----> digital activation, control, and next layer
```

The first machine is hybrid. Static weights live in a resistor or programmable-resistance network. Matrix-vector multiplication is analog. Control, calibration, nonlinear activation, scheduling, and partial-sum accumulation may initially remain digital.

## What is genuinely analog

For an ideal conductance array, input voltages represent `x`, programmed conductances represent `W`, and column currents represent `W @ x`. The physical circuit performs multiplication through Ohm's law and accumulation through Kirchhoff's current law.

## What is not ReRAM yet

The first hardware uses accessible components such as precision resistors, potentiometers, analog switches, or digital potentiometers. These reproduce the conductance-mapping problem but not every property of a ReRAM cell. A future memory module may replace the conductance tile without changing the controller and software contracts.

## Modular boundary

The project separates:

- the weight-storage technology;
- the input converter;
- the analog array;
- the output converter;
- the controller;
- host-side compilation and calibration.

This lets a builder start with a fixed 2×2 array and later replace only the relevant module.

## Definition of success

Homebrew Analog AI v0.1 succeeds when a second builder can:

1. assemble the documented modules from the BOM;
2. run a self-test;
3. calibrate the tile;
4. program a small signed matrix;
5. send an input vector;
6. measure a result within the documented error bound;
7. run a tiny classifier whose physical matrix multiplications use the analog tile.

## What this project does not claim

- It is not a semiconductor fabrication tutorial.
- It is not initially an all-analog neural network.
- It is not automatically faster or more efficient than a CPU/GPU.
- One crossbar operation does not make an entire LLM constant-time.
- A resistor network is not identical to a ReRAM array.

## Before continuing

Read [`docs/SAFETY.md`](../../docs/SAFETY.md) and [`docs/MODULE_STANDARD.md`](../../docs/MODULE_STANDARD.md). Then continue to chapter 0001, where one weighted sum becomes a measurable circuit.
