# tile-v1-r5-validation-summary

**Gate verdict: `NOT_MET`** — claim level `SYSTEM_SIMULATED`.

![R5 tile validation evidence chain](tile-v1-r5-validation-summary.svg)

## Evidence chain

```text
crossbar/DAC/ADC profiles -> CrossbarTile -> 2x2/4x4 SPICE regression
                                      -> calibration profile + consumer
                                      -> tiled partial-sum rules
                                      -> frozen R5 verdict
```

## Formulas

- tile/SPICE error: `$E_max = max_(c,j) |V_tile[c,j] - V_spice[c,j]|$`
- acceptance: `$E_max <= E_ADC_budget$`
- calibration: `$a_ls = sum(y_raw*y_spice)/sum(y_raw^2)$`; `$y_cal = clip(a_ls,[a_min,a_max])*y_raw$`
- partial sums: `$y_i = sum_(j=0)^(K_c-1) TileForward(W_ij,x_j)$`
- accumulator: `$B_acc >= B_ADC + ceil(log2(K_c))$`

## Deterministic evidence

| item | result | status |
| --- | --- | --- |
| 2×2/4×4 SPICE equivalence | 10 cases / 30 outputs; max 0.150124 V ≤ 0.156250 V | PASS |
| calibration | RMS 0.079836 V → 0.075799 V (5.06%); max not degraded | PASS |
| partial sums | `B_acc >= B_adc + ceil(log2(K_c))`; Kc=16 requires 8 bits | PASS |

## Profile coverage

- crossbar fields: 35
- directly consumed configuration fields: g0_s, gscale_s_per_w
- other unconsumed fields: 33
- required nonidealities still not applied:
  - `mvm_error_16x16_1ohm_pct` — IR drop
  - `sigma_prog_rel` — programming variation
  - `sigma_read_rel` — read variation
  - `drift_exponent_nu_min` — temporal drift
  - `p_stuck_hrs` — stuck-at-HRS faults
  - `p_stuck_lrs` — stuck-at-LRS faults
  - `iv_non_linearity_beta` — I-V non-linearity

## Gate criteria

| criterion | result |
| --- | --- |
| three_profile_configuration | PASS |
| small_array_spice_budget | PASS |
| profile_driven_calibration | PASS |
| partial_sum_rules_explicit | PASS |
| all_required_crossbar_nonidealities_consumed | FAIL |
| physical_claim_supported | FAIL |

## Blockers

- `unconsumed_crossbar_nonidealities`: Apply each mechanism in the tile/accelerator path from its profile field, with deterministic attribution and boundary tests.
- `physical_claim_not_supported`: Keep physical_claim=False until assumed inputs are replaced or the claim is narrowed to supported evidence; add held-out/corner calibration evidence.

## Verdict

R5 report is frozen, but gate exit is NOT_MET: the current tile is a profile-configured behavioral converter/MVM model, not yet a calibrated abstraction of all proposed crossbar-v1 nonidealities.
