# 0009 — R-2R ladder DAC

First design candidate for the converter signal path (R2): a **binary-weighted
R-2R ladder** DAC. The activation path needs `x (digital) → V (analog)`, and the
ladder realizes it with only two resistor values, `R` and `2R`.

## Why an R-2R ladder

- Uses exactly two resistor values regardless of resolution (`R`, `2R`) — a
  real, manufactureable building block.
- Output depends only on resistor **ratios** and `VREF`, so gain and range are
  set by design, not by an exotic component.
- Its hand model is simple and exact under ideal switches:

  ```text
  Vout(code) = VREF * code / 2^N ,   code = Σ bit_i · 2^i
  ```

## Units and assumptions

| Quantity | Value | Units |
|---|---|---|
| `BITS` | 4 | ladder width (prototype) |
| `VREF` | 2.5 | V (reference; matches 0007/0005 reference) |
| `R` | 10 | kΩ (unit resistor) |
| `2R` | 20 | kΩ (bit-leg / termination resistor) |
| full scale | `VREF·15/16 = 2.34375` | V (code 15) |
| LSB | `VREF/16 = 0.15625` | V per code |

All values are simulation targets; nothing here is a measured silicon result.

## Circuit

```
n0 --R-- n1 --R-- n2 --R-- n3 --R-- n4          (series chain)
|        |        |        |
2R       2R       2R       2R                    (bit legs)
|        |        |        |
GND     sw(bit0) sw(bit1) sw(bit2)  + 2R to GND terminates at n0
```

- Each node `n_i` has a `2R` leg switched between `VREF` (bit = 1) and ground
  (bit = 0). Bit 0 is at the terminated end; the output is taken at `n4`.
- The ladder divides current exponentially, so each bit contributes
  `VREF · 2^i / 2^N` at the output.

`Run: book/0009-dac-r2r/r2r_dac.py`

## Verification

- **SPICE vs hand**: all 16 codes, `worst |SPICE − ideal| = 4.44e-16 V` (DC
  operating-point solves with ideal switch sources).
- `Vout(0) = 0`, monotonic by construction, `Vout(15) = 2.34375 V`.
- Always-on data tests + optional engine tests in `tests/test_dac_r2r_profile.py`.

## What this chapter does NOT do yet

- Transient settling (switch/ladder RC time constant) — deferred study.
- Resistor mismatch / Monte Carlo — R-2R's whole point is ratio tolerance; the
  numeric sensitivity is a separate chapter.
- Supply sensitivity of `VREF` — deferred.
- Non-zero switch resistance — real switches add offset and INL; ideal sources
  are the DC model here.

These are tracked as open items in the R2 gate.
