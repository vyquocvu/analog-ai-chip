# `crossbar-v1` Verification Summary Report

> **Profile:** [`device_profiles/crossbar-v1.json`](../../device_profiles/crossbar-v1.json)
> **Status:** `VARIATION_SIMULATED` | **Evidence Class:** `spice`

## 1. Physical Verification Evidence Ledger

| Physical Parameter | Field | Value | Unit | Evidence Class | Source |
|---|---|---|---|---|---|
| **Conductance Dynamic Range (gmax/gmin)** | `dynamic_range_ratio` | `10.0000` | `1` | `derived` | [`dynamic_range_ratio`](../../device_profiles/crossbar-v1.json#/fields/dynamic_range_ratio) |
| **Zero Weight Noise Floor (std)** | `zero_weight_noise_floor_std` | `0.0050` | `1` | `derived` | [`zero_weight_noise_floor_std`](../../device_profiles/crossbar-v1.json#/fields/zero_weight_noise_floor_std) |
| **Full Scale Weight Std Dev** | `full_scale_weight_std` | `0.0353` | `1` | `derived` | [`full_scale_weight_std`](../../device_profiles/crossbar-v1.json#/fields/full_scale_weight_std) |
| **MVM Error @ 16x16 (1.0 Ohm)** | `mvm_error_16x16_1ohm_pct` | `1.8698` | `%` | `derived` | [`mvm_error_16x16_1ohm_pct`](../../device_profiles/crossbar-v1.json#/fields/mvm_error_16x16_1ohm_pct) |
| **MVM Error @ 32x32 (1.0 Ohm)** | `mvm_error_32x32_1ohm_pct` | `6.7726` | `%` | `derived` | [`mvm_error_32x32_1ohm_pct`](../../device_profiles/crossbar-v1.json#/fields/mvm_error_32x32_1ohm_pct) |
| **1% Settling Time (16x16)** | `t_settle_1pct_ps` | `20.5000` | `ps` | `spice` | [`t_settle_1pct_ps`](../../device_profiles/crossbar-v1.json#/fields/t_settle_1pct_ps) |
| **Max Retention Drift Loss (1 Year)** | `max_drift_loss_1year_pct` | `64.5104` | `%` | `derived` | [`max_drift_loss_1year_pct`](../../device_profiles/crossbar-v1.json#/fields/max_drift_loss_1year_pct) |
| **MVM Error @ 1.0% Stuck Faults** | `mvm_error_1pct_faults_pct` | `9.2097` | `%` | `derived` | [`mvm_error_1pct_faults_pct`](../../device_profiles/crossbar-v1.json#/fields/mvm_error_1pct_faults_pct) |
| **Peak I-V Non-Linear Distortion** | `max_iv_distortion_pct` | `6.2500` | `%` | `derived` | [`max_iv_distortion_pct`](../../device_profiles/crossbar-v1.json#/fields/max_iv_distortion_pct) |

## 2. Gate R4 Verification Exit Status

- [x] Compact model & discretization (0015): $G_{\min}=10.0\,\mu\text{S}, G_{\max}=100.0\,\mu\text{S}, 10\times$ on/off.
- [x] Stochastic programming & read variation (0016): $\sigma_{\text{prog}}=3\%, \sigma_{\text{read}}=1\%$.
- [x] IR drop & interconnect line resistance (0017): $R_{\text{wire}}=1.0\,\Omega$, $32\times 32$ tile boundary ($6.77\%$ error).
- [x] RC parasitics & dynamic settling (0018): $C_{\text{seg}}=1.5\text{ fF}, t_{\text{settle}}=20.5\text{ ps}, f_{\max}>40\text{ GHz}$.
- [x] Temporal drift, stuck faults & non-linearity (0019): $\nu \in [0.02, 0.06]$, $p_{\text{fault}}=1\% \to 9.21\%$ error, $\beta=1.0\text{ V}^{-2}$.

**Gate R4 is fully satisfied and closed.**