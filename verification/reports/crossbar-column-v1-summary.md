# crossbar-column-v1-verification-summary

R1 gate-exit verification summary — closes the proof chain

```text
0007 SPICE evidence -> extraction -> validated profile -> adapter -> tile config
```

## Profile

- name/version: `crossbar-column-v1` `0.1.0`
- status: `CIRCUIT_SIMULATED` (evidence class `spice`)
- source: `device_profiles/crossbar-column-v1.json`
- spice tool/analysis: `PySpice/ngspice` / `op`
- validation: `passed (physical_claim=True, fail-closed)`

## Coverage

| bucket | count |
| --- | --- |
| VERIFIED_BY_SPICE | 3 |
| DERIVED | 7 |
| ASSUMED | 0 |

### By component (circuit/device)

| component | VERIFIED_BY_SPICE | DERIVED |
| --- | --- | --- |
| readout | 2 | 1 |
| differential_mapping | 1 | 1 |
| conductance_cell | 0 | 2 |
| rail_headroom | 0 | 3 |

### Claim levels

- circuit/device: evidence-backed profile fields
- system: tile configuration derived from the profile; `assumed` bits are explicit programming choices pending a converter profile

## Evidence

| field | value | unit | bucket | source |
| --- | --- | --- | --- | --- |
| transimpedance_gain_ohm | 10020 | ohm | VERIFIED_BY_SPICE | device_profiles/crossbar-column-v1.json#/fields/transimpedance_gain_ohm |
| gain_v_per_v_per_unit_weight | 0.9995 | V/V per weight | VERIFIED_BY_SPICE | device_profiles/crossbar-column-v1.json#/fields/gain_v_per_v_per_unit_weight |
| dc_error_v_max | 0.00079968 | V | VERIFIED_BY_SPICE | device_profiles/crossbar-column-v1.json#/fields/dc_error_v_max |
| rf_nominal_ohm | 10000 | ohm | DERIVED | device_profiles/crossbar-column-v1.json#/fields/rf_nominal_ohm |
| differential_mapping_error_s_max | 6.77626e-21 | S | DERIVED | device_profiles/crossbar-column-v1.json#/fields/differential_mapping_error_s_max |
| g0_s | 0.0001 | S | DERIVED | device_profiles/crossbar-column-v1.json#/fields/g0_s |
| gscale_s_per_w | 0.0001 | S | DERIVED | device_profiles/crossbar-column-v1.json#/fields/gscale_s_per_w |
| vref_v | 2.5 | V | DERIVED | device_profiles/crossbar-column-v1.json#/fields/vref_v |
| output_headroom_up_v | 2.5 | V | DERIVED | device_profiles/crossbar-column-v1.json#/fields/output_headroom_up_v |
| output_headroom_down_v | 2.5 | V | DERIVED | device_profiles/crossbar-column-v1.json#/fields/output_headroom_down_v |

## Adapter-derived tile configuration

- consumer: `analog_llm.crossbar.CrossbarTile via analog_llm.profile_adapter`
- source adapter: `analog_llm/profile_adapter.py`

| kwarg | value | derivation |
| --- | --- | --- |
| g_bits | 6 | explicit programming choices |
| dac_bits | 8 | explicit programming choices |
| adc_bits | 8 | explicit programming choices |
| gmin | 0.0001 | g0_s |
| gmax | 0.0002 | g0_s + gscale_s_per_w |
| vin_max | 2.5 | min(headroom_up, headroom_down) |
| vout_max | 2.5 | min(headroom_up, headroom_down) |

## Measurement pending

- `hardware_readout`: physical measurement of the 0007 column readout (breadboard workflow)
- `transient_settling`: DC operating-point solves only; no transient/settling evidence
- `noise_temperature_variation`: no noise, temperature corner or Monte Carlo evidence yet

## Limitations

DC operating-point solves only; no transient/settling, noise, temperature or Monte Carlo evidence yet. Rail limits taken from the 0005 non-ideal model; headroom is derived from VDD and VREF, not measured on the 0007 column directly.
