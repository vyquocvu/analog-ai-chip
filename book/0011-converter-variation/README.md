# 0011 — Converter variation: R-2R resistor mismatch

Real silicon resistors are not exact: every resistor carries a relative
mismatch `delta ~ N(0, sigma)`. The 0009/0010 chapters verified the *nominal*
R-2R ladder; this chapter measures how mismatch propagates into the converter
transfer as gain error, INL and DNL — with one independent hand reference
proving the Monte Carlo.

## Two solvers, one set of deterministic draws

A fixed seed (`7`) draws one set of relative mismatch vectors (one entry per
ladder resistor: `bits` series `R`, `1` termination `2R`, `bits` bit-switch
legs `2R`). Each vector drives **both** solvers:

- **SPICE** (`mismatched_output`): a copy of the 0009 ladder netlist whose
  resistor values are `nominal * (1 + delta)`, solved by ngspice.
- **hand** (`hand_output`): the same resistive network solved as a conductance
  matrix `G·V = b` in NumPy, with bit switches as ideal `VREF`/`0` sources —
  identical idealization to the SPICE netlist.

The network is linear, so both solvers must return identical voltages for every
(code, sample) pair. That equality is the core assertion: the SPICE mismatched
ladder and the hand model agree to **`2.2e-15 V`** over all 1024
(sample × code) pairs of the 64-sample study.

## Tiny hand-computable anchor

For a 1-bit ladder (series `b`, termination `a`, leg `c`) with code 1 the exact
output is

```
Vout = VREF * a / (a + c)
```

(KCL at `n0` with `Vout = Vn0`; `b` carries no load current and drops out —
checked by perturbing `b` by 99% and confirming no effect). The closed form is
asserted in `tests/test_converter_variation.py` as the anchor for the whole
mismatch model.

## Monte Carlo statistics

Per sample, over all `2^N` codes, measured from the endpoint-fit line:

| Quantity | mean | std |
|---|---|---|
| offset | `0` | `0` (all legs ground at code 0) |
| gain error (endpoint slope / LSB − 1) | `−1.1e-5` | `7.2e-4` |
| max \|INL\| | `6.3e-3 V` | `3.1e-3 V` |
| max \|DNL\| | `1.1e-2 V` | `6.5e-3 V` |

For `sigma = 0` the study reproduces the ideal ladder (fail-closed sanity
check), and the statistics computed from SPICE transfers match the hand-solver
statistics to `1e-12`.

## Units and assumptions

- `R = 10 kΩ`, `2R = 20 kΩ`, `VREF = 2.5 V`, `BITS = 4` (matches 0009/0010).
- `sigma = 1%` relative mismatch, Gaussian, **assumed** — no measurement
  backing. This is a sensitivity study: it proves the model propagates mismatch
  deterministically and matches an independent solver, but it does **not**
  publish a device profile and would fail closed under `physical_claim`.
- Mismatch is applied to resistors only; switch resistance, comparator offset,
  and temperature remain out of scope.

## Separating error mechanisms

A measured transfer mixes independent error sources; `decomposition.py`
separates them and proves the split exact.

**DAC** (`decompose_dac_transfer`): the endpoint-fit line
`L(code) = offset + slope·code` captures offset + gain; everything left is
non-linearity (`INL = V − L`). On the 64-sample SPICE mismatch study the
separation gives offset `0`, gain error mean `−1.1e-5` (std `7.2e-4`), and
`max|INL| = 1.5e-2 V`, with `V == line + INL` to `1e-12` — the decomposition
is exact by construction.

**ADC** (`separate_adc_error`): a full-scale sine through the 4-bit quantizer
plus input-referred Gaussian noise accumulates error power from two
uncorrelated mechanisms, `P_total = P_quant + P_noise` with `P_quant =
LSB²/12`. Measured power tracks the hand sum (e.g. `noise_std = 0.05 V`:
measured `4.25e-3` vs hand `4.54e-3 V²`, sampling tolerance).

## Calibration candidates

Mismatch is static per chip, so it is correctable. `calibration.py` defines
and exercises three candidates on the SPICE mismatch draws:

| Candidate | Correction | Residual on 64-sample SPICE study |
|---|---|---|
| raw (uncorrected) | — | `1.6e-2 V` |
| two-point (gain + offset) | fit endpoints, `V_corr = (V−offset)·LSB/slope` | `1.5e-2 V` = max\|INL\| (scaled) |
| full transfer LUT | subtract per-code deviation from ideal | `0.0 V` (static mismatch) |
| reference trim (VREF) | digital gain factor (from 0010: `gain_error = dVREF/VREF`) | design note, not re-measured |

The two-point scheme removes the gain/offset share and leaves exactly the
non-linearity; the full LUT zeroes static mismatch entirely. Both are proven
exact in `tests/test_converter_calibration.py`.

## Artifacts

- `book/0011-converter-variation/variation.py` — single source of truth for the
  SPICE solves (run `python book/0011-converter-variation/variation.py`).
- `book/0011-converter-variation/decomposition.py` — separates error mechanisms
  (run `python book/0011-converter-variation/decomposition.py`).
- `book/0011-converter-variation/calibration.py` — defines calibration
  candidates (run `python book/0011-converter-variation/calibration.py`).
- `verification/circuit/extract_converter_variation.py` — deterministic
  extraction; emits
  `verification/circuit/results/converter-variation-0011-extract.json`
  (raw transfers for both solvers + statistics).
- `tests/test_converter_variation.py` — always-on hand-model tests + engine-gated
  SPICE agreement and extract reproducibility tests.
