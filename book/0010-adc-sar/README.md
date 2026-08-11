# 0010 — SAR ADC for the TIA output path

First design candidate for the ADC side of the converter signal path (R2): a
**successive-approximation (SAR) converter** whose internal reference is the
R-2R ladder of chapter 0009. It digitizes the **differential** output of the
0007 crossbar column.

## Signal chain

```
 TIA output            input front            SAR
 Vdiff = Vm - Vp  ->   Vin = VREF/2 + Vdiff/2  ->  code  ->  Vdiff_hat
 +/-2.5 V (signed)     unipolar [0, VREF]      floor(Vin/LSB)
```

- The 0007 column's differential output `Vout = Vm − Vp` is signed and can span
  `±2.5 V` around the virtual reference (the crossbar-column profile headroom).
- The R-2R reference ladder (0009) is *unipolar* `0 .. VREF`, so the input
  front level-shifts and halves the signal: `Vin = VREF/2 + Vdiff/2`. This maps
  `±2.5 V` onto `[0, 2.5 V]` exactly, one full LSB envelope for `2^N` codes.

## Units and assumptions

| Quantity | Value | Units |
|---|---|---|
| `BITS` | 4 | bits (prototype; matches 0009 ladder) |
| `VREF` | 2.5 | V (reference; matches 0005/0007/0009) |
| `LSB` | `VREF/16 = 0.15625` | V per code |
| differential envelope | `±2.5` | V (from crossbar-column-v1 headroom, derived) |
| input front gain | `1/2` (×2 for reconstruction) | V/V |
| input front offset | `+VREF/2` | V |
| comparator | VCVS gain `1e4` (ideal opamp, 0007 model) | — |

All values are simulation targets; nothing here is a measured silicon result.
The `1/2` gain and `VREF/2` offset of the input front are a *design choice*, not
yet a measured circuit — they will be validated in the output-stage (TIA→ADC
interface) work.

## Transfer model

Hand reference (mid-rise):

```text
code   = floor(Vin / LSB),              clipped to [0, 2^N - 1]
V_hat  = (code + 0.5) * LSB             unipolar reconstruction
Vdiff_hat = 2 * (V_hat - VREF/2)        differential-domain reconstruction
```

Quantization error is bounded by `LSB = 0.15625 V` in the differential domain:
the input front scales by `1/2`, so one differential code spans `2·LSB` and the
mid-rise reconstruction error is at most `2·(LSB/2) = LSB` at the extremes of
the `±VREF` envelope. (Unipolar, the bound is the familiar `LSB/2`.)

## Circuit vs functional boundary

This chapter deliberately keeps two levels separate (per AGENTS.md rule 4):

- **circuit/device** — each SAR bit trial is a real ngspice operating-point
  solve: the R-2R reference ladder node voltage versus the level-shifted input,
  decided by a VCVS comparator. `comparator_decision(Vin, code)` is SPICE.
- **functional** — the MSB-first search *algorithm* that walks the bits is
  deterministic logic in Python (`sar_search`). It consumes the SPICE decisions
  but the search itself is not a circuit.

The 0009 ladder's DC transfer is already SPICE-verified; this chapter reuses
that topology and adds the comparator decision as new circuit-level evidence.

## Verification

- **Comparator**: SPICE decision equals the hand comparison
  `Vin >= Vref(code)` on representative trials.
- **Transfer sweep**: 129 samples across `[0, VREF]`, SAR code equals hand
  `ideal_code` at every point — worst deviation 0 codes.
- **Example**: `Vdiff = +2.0 V` → `Vin = 2.25 V` → code 14 →
  `Vdiff_hat = +2.0312 V`, error 0.0312 V ≤ LSB.
- **Reference settling**: the R-2R reference at the comparator node settles
  like the 0009 ladder (`τ = 2R·CL`); SPICE matches the single-pole hand model
  within 10 ns for each bit trial at an *assumed* `CL = 1 pF`.
- **Conversion time**: 4 sequential bit trials, worst-case reference step per
  bit, sum to `140.9 ns` (SPICE) vs `138.6 ns` (hand). The `CL` value has no
  device evidence yet, so settling/conversion time is a sensitivity study only.
- **Effective resolution**: a coherent full-scale sine (odd-prime cycles over a
  power-of-two sample count, so all quantization levels are swept uniformly)
  gives `ENOB = 3.91 bits` for the 4-bit quantizer (hand upper bound 4.00);
  additive input-referred Gaussian noise at `0.05 V` degrades it to `3.46`
  (hand `3.42`). The additive-noise model mirrors `analog_llm.converters.adc`.
- **VREF supply sensitivity**: because the ladder is ratio-based and the
  comparator ideal, a VREF shift is a *pure gain error* — measured (SPICE)
  `gain_error` equals `dVREF/VREF` at ±10% to within `1e-9`. Temperature and
  process corner have **no** modelable effect on ideal resistors/VCVS by
  construction; that is documented as out of scope, not swept as fake evidence.
- **Profile**: `device_profiles/adc-sar-v1.json` (extract
  `verification/circuit/results/adc-sar-v1-extract.json`). The SPICE transfer
  gives `max_code_error_codes = 0` and `max_abs_error_v = LSB` (the
  differential-domain quantization bound); `bits`, `r_ohm`, `vref_v`, `lsb_v`,
  `input_range_v`, `quantization_error_v` are derived design choices. The
  assumed-CL settling, functional ENOB and supply-deviation studies stay in the
  extract JSON only — they carry no physical evidence and fail closed under
  `physical_claim`. Run: `python verification/circuit/extract_adc_sar.py`.
- Always-on data tests + optional engine tests in `tests/test_adc_sar.py`.

`Run: book/0010-adc-sar/sar_adc.py`

## What this chapter does NOT do yet

- TIA→ADC output-stage circuit (the `1/2` + `VREF/2` front is assumed, not
  SPICE) — next item in this chapter.
- Noise as a *device* mechanism: the ENOB study adds input-referred Gaussian
  noise functionally (matching `converters.adc`); comparator thermal/kT-C
  noise, reference noise and their spectra are not yet SPICE models.
- Temperature/process-corner sweep: the ideal resistor + VCVS models have no
  temperature or corner dependence by construction, so only the VREF-supply
  sensitivity (a pure gain error) is swept.

These are tracked as open items in the R2 gate; nothing here is promoted to a
verified physical claim.
