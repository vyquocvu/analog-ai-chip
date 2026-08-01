# 0001 — Build One Analog Neuron

Status: design chapter. Component selection and measured evidence are not complete yet.

## Goal

Build and measure a low-voltage circuit that computes a weighted sum:

```text
y = w1*x1 + w2*x2 + b
```

The first revision may omit the bias input and add it after the two-input weighted sum is validated.

## Learning result

By the end of this chapter, the builder should be able to explain and measure:

- how a voltage represents an input value;
- how a resistance/conductance represents a weight;
- how currents add at a summing node;
- how an op-amp converts summed current into output voltage;
- why sign, gain, headroom, offset, and saturation matter;
- why measured output differs from ideal arithmetic.

## Proposed build blocks

```text
Input x1 -- conductance G1 --+
                            +-- summing node -- op-amp -- Vout
Input x2 -- conductance G2 --+
```

The tested schematic must use a topology compatible with the selected single-supply op-amp and virtual reference. Do not copy a dual-supply textbook inverting summer directly onto a 5 V breadboard without accounting for input common-mode range and output headroom.

## Hand calculation contract

The chapter will freeze one small example before the circuit is finalized. A candidate is:

```text
x = [0.5, 1.0]
w = [0.5, 0.25]
ideal weighted sum = 0.5
```

The physical mapping must document:

- value-to-voltage scale;
- weight-to-conductance scale;
- feedback resistance;
- polarity;
- expected output voltage;
- acceptable error interval.

## Required deliverables

- `schematic/` source and exported PDF/PNG;
- `breadboard.md` with pin-by-pin wiring;
- `bom.csv` with exact manufacturer part and substitutes;
- `measurements.csv` from the tested build;
- `verify.py` reproducing the expected arithmetic;
- test-point table for supply, reference, inputs, summing node, and output;
- calibration and power-down procedure;
- photos or diagrams matching the tested revision.

## Bring-up sequence

1. Read the safety guide.
2. Build and measure the power/reference stage only.
3. Confirm the selected op-amp pinout from its datasheet.
4. Power the op-amp with no signal and verify quiescent conditions.
5. Add one input branch and compare one measured point.
6. Add the second input branch.
7. Sweep several inputs inside the safe range.
8. Record expected and measured output.
9. Deliberately approach saturation and document the failure.
10. Power down before changing component values.

## Measurements to record

| Measurement | Expected | Actual | Unit | Instrument |
|---|---:|---:|---|---|
| Supply | TBD |  | V | multimeter |
| Analog reference | TBD |  | V | multimeter |
| Input 1 | TBD |  | V | multimeter |
| Input 2 | TBD |  | V | multimeter |
| Output | TBD |  | V | multimeter/scope |
| Output noise | TBD |  | mV RMS | scope |

## Experiments

- replace 1% resistors with 5% resistors;
- warm one resistor gently with normal handling and observe drift;
- repeat the same input 100 times;
- increase input until the output clips;
- compare multimeter and oscilloscope measurements;
- calculate ideal, component-tolerance, and measured error separately.

## What this build does not prove

A successful weighted-sum circuit does not demonstrate ReRAM storage, large-array scalability, competitive energy efficiency, neural-network accuracy, or faster inference than digital hardware. It proves that a real analog circuit can encode and measure a small weighted sum, which is the physical primitive the later machine will scale and automate.
