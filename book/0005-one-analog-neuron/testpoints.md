# Test points — 0005 analog neuron

Measure with a multimeter against the common gnd rail. Record `Expected` and
`Actual`; accept within the `Tol` column.

| # | Test point | Where | Expected | Tol | Unit | Instrument |
|---|---|---:|---|---:|---|---|
| TP1 | Supply VCC | +5 V rail (pin 8) | 5.0 | ±0.1 | V | multimeter |
| TP2 | Ground | gnd rail (pin 4) | 0.0 | ±0.01 | V | multimeter |
| TP3 | Reference divider | node REF (pin 3) | 2.5 | ±0.05 | V | multimeter |
| TP4 | Buffered VREF | OUT1 = pin 1 = pin 5 | 2.5 | ±0.05 | V | multimeter |
| TP5 | Summing node n | pin 6 | 2.5 | ±0.05 | V | multimeter |
| TP6 | Input x1 | x1 source | as applied | ±0.01 | V | multimeter |
| TP7 | Input x2 | x2 source | as applied | ±0.01 | V | multimeter |
| TP8 | Output Vout | pin 7 | 2.5 ± w·x swing | compute | V | multimeter/scope |
| TP9 | Output noise | pin 7 (AC) | < 5 | ±5 | mV RMS | scope |

## Expected output check

For inputs `x1, x2` and `w = [0.50, 0.25]` (Rf/R1, Rf/R2):

```text
Vout = 2.5 − (0.50·(x1 − 2.5) + 0.25·(x2 − 2.5))
```

A quick example with `x1 = x2 = 2.5` gives `Vout = 2.5` (no swing). With the
hand contract `x1 = 2.5 + 0.5`, `x2 = 2.5 + 1.0`:

```text
Vout = 2.5 − (0.50×0.5 + 0.25×1.0) = 2.5 − 0.5 = 2.0 V   (swing 0.5 V)
```
