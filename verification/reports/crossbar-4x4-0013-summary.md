# crossbar-4x4-0013-verification-summary

R3 gate-exit verification summary — behavioral equivalence of the 4×4 array

```text
0012/0013 SPICE arrays -> extract -> hand reference + profile-driven tile -> report
```

## Evidence

- source: `verification/circuit/results/crossbar-4x4-0013-extract.json` (plus `verification/circuit/results/crossbar-2x2-0012-extract.json` for the 2×2 regression)
- 5 deterministic (W, u) cases x 4 outputs; VREF = 2.5 V, headroom ±2.5 V

## Behavioral tile

- profile: `device_profiles/crossbar-column-v1.json` via `analog_llm.tile.CrossbarTile via analog_llm.profile_adapter`
- conductance window [0.0001, 0.0002] S; envelope ±2.5 V; bits {'g_bits': 16, 'dac_bits': 16, 'adc_bits': 16}

## Error budget (frozen)

| comparison | max (V) | rms (V) | budget (V) |
| --- | --- | --- | --- |
| SPICE vs hand | 5.50e-04 | 3.28e-04 | 2e-03 |
| tile vs hand | 3.78e-05 | 2.78e-05 | 2e-03 |
| SPICE vs tile | 5.19e-04 | 3.14e-04 | 2e-03 |

- currents: worst |SPICE − hand| 1.80e-07 A (budget 5e-06 A); max cell current 1.00e-04 A
- headroom: max |Vout| 0.500 V ≤ ±2.5 V; virtual ground within 3.00e-04 V
- 2×2 regression: scaled module reproduces 0012 to 0.0e+00 V

## Coverage

| component | what it proves |
| --- | --- |
| mvm | SPICE 4x4 MVM vs hand reference Vout = RF*GSCALE*(W @ u) |
| behavioral | profile-driven analog_llm tile vs hand reference (16-bit quantization floor) |
| currents | column currents recovered from SPICE half-stage outputs vs hand sum u*G |
| headroom | differential output envelope +/-2.5 V and virtual-ground loading |
| regression | scaled module reproduces the committed 2x2 (0012) results |

### Claim levels

- `circuit/device`: SPICE 4x4 MVM (op solves, VCVS gain 1e4)
- `circuit/device`: column currents from SPICE half-stage outputs
- `circuit/device`: virtual-ground loading and differential headroom
- `system/behavioral`: profile-driven tile error is its 16-bit quantization floor
- `system/behavioral`: no latency/energy claim: timing is 0014/R4-R8

## Measurement pending

- `op_amp_bandwidth`: ideal VCVS has no bandwidth model; settling is recorded as a data point, not a claim -- bounded settling is 0014
- `finite_driver_impedance`: input rows are ideal voltage sources; IR drop / line resistance are R4 items
- `parasitic_rc`: no parasitic RC on cells or interconnect yet (R4)

## Limitations

Ideal VCVS op-amp (no bandwidth/clipping model); ideal input sources (no driver impedance); settling recorded but not a claim; no temperature/process/Monte Carlo evidence (R4).
