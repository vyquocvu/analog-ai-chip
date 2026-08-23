# 0026 — End-to-End Architecture & Calibration Ledger (Gate R6 Exit)

> **Bản tiếng Việt:** [`README.vi.md`](README.vi.md)

This chapter delivers the **unified end-to-end architecture execution ledger, profile-derived timing/energy breakdowns, and multi-tile output calibration flow** that satisfies the exit criteria for **Gate R6 (Accelerator architecture and data movement)**.

---

## 1. Profile-Derived Timing Model

![End-to-End Architecture Ledger](diagrams/architecture-ledger-0026.svg)

Every component of the analog MVM execution step traces to validated circuit/device evidence:
- **DAC Settling**: $t_{\text{dac}} = 5.0\text{ ns}$ (`derived` from $R$-$2R$ ladder RC, `device_profiles/dac-r2r-v1.json`).
- **Crossbar Settling**: $t_{\text{xbar}} = 0.05\text{ ns}$ (`derived` from distributed line parasitics, Chapter 0018).
- **TIA Settling**: $t_{\text{tia}} = 5.0\text{ ns}$ (`derived` from closed-loop noise gain and op-amp bandwidth, Chapter 0014).
- **SAR ADC Conversion**: $t_{\text{adc}} = B_{\text{ADC}} \times 2.5\text{ ns} = 10.0\text{ ns}$ (`derived` from `device_profiles/adc-sar-v1.json`).
- **Analog MVM Step Time**:
  $$t_{\text{mvm}} = t_{\text{dac}} + t_{\text{xbar}} + t_{\text{tia}} + t_{\text{adc}} = 20.05\text{ ns}$$

---

## 2. Complete Energy & Storage Hierarchy

### Energy Coefficients & Provenance:
- **Analog MVM Compute**: $e_{\text{analog\_mac}} \approx 50.0\text{ fJ/MAC}$ (`derived` from SAR ADC + crossbar current ledger).
- **SRAM Access Energy**: $e_{\text{sram\_byte}} \approx 1.0\text{ pJ/byte}$ (`assumed`, planar 28nm SRAM).
- **NoC Hop Energy**: $e_{\text{noc\_byte\_hop}} \approx 0.5\text{ pJ/(byte}\cdot\text{hop)}$ (`assumed`, 28nm 5-port router).
- **NVM Cell Programming**: $E_{\text{pair\_prog}} \approx 10.0\text{ pJ/pair}$ (`assumed`, RRAM filament set/reset).

### Sized Storage Components:
- **Per-Tile SRAM**: $288\text{ B}$ / physical $16\times 16$ tile (Chapter 0024).
- **Spatial Reduction Accumulators**: $B_{\text{acc}} = B_{\text{ADC}} + \lceil \log_2 K_c \rceil$ (Chapter 0022).
- **Global KV Cache**: $S_{\text{KV}} = 2 L \cdot n_{\text{layers}} \cdot d_{\text{model}} \cdot B_{\text{act}}$ ($128\text{ KB}$ for TinyGPT, $1.00\text{ GB}$ for LLaMA-7B).

---

## 3. Workload Comparison: Weight-Stationary vs Temporal Reuse

### TinyGPT QKV Projection ($192 \times 64$, $48$ physical $16\times 16$ tiles):

| Metric | Weight-Stationary ($N_{\text{tiles}}=64$) | Temporal-Multiplexed ($N_{\text{tiles}}=16$) | Impact of Stationarity |
|---|---|---|---|
| **MVM Execution Cycles** | $1\text{ cycle}$ | $3\text{ cycles}$ | $3\times$ fewer compute cycles |
| **Tile Reprogramming Events** | **$0\text{ rewrites}$** | **$32\text{ rewrites}$** | **Zero rewrite overhead** |
| **Programming Latency Overhead** | **$0.0\,\mu\text{s}$** | **$256.0\,\mu\text{s}$** | $11,500\times$ faster execution |
| **Total Layer Latency** | **$0.022\,\mu\text{s}$** | **$256.06\,\mu\text{s}$** | Critical for real-time decoding |
| **Total Layer Energy** | **$1.17\text{ nJ}$** | **$83.56\text{ nJ}$** | **$71.2\times$ lower energy** |

---

## 4. Multi-Tile Calibration Integration

The calibrated output voltage $y_{\text{cal}}$ applies the zero-preserving least-squares gain $a^* = 0.9795135$ (Chapter 0021 / `device_profiles/tile-calibration-v1.json`) following spatial partial-sum reduction:
$$y_{\text{cal}} = a^* \cdot \sum_{j=0}^{K_c - 1} y_{i,j}$$
This reduces residual RMS error by $5.06\%$ while preserving the balanced differential zero.

---

## 5. Gate R6 Exit Proof

> **Gate R6 Exit Criterion**: For any layer, the simulator can state where time, storage, traffic, rewrites and error come from.
>
> **Status: MET (SYSTEM_SIMULATED)**
> - **Time**: Traced to profile DAC ($5.0\text{ ns}$), SPICE/RC crossbar ($0.05\text{ ns}$), TIA ($5.0\text{ ns}$), ADC ($10.0\text{ ns}$), and NoC hop tree ($1.0\text{ ns/hop}$).
> - **Storage**: Exact double-buffered SRAM ($288\text{ B/tile}$) + KV cache ($128\text{ KB}$).
> - **Traffic**: Multicast activations ($K_c \cdot C \cdot B_{\text{DAC}} / 8$) + spatial tree partial-sum reduction ($K_r(K_c - 1) \cdot R \cdot B_{\text{acc}} / 8$).
> - **Rewrites**: Exact temporal scheduler tracking ($N_{\text{rewrites}}$) + NVM pulse energy ledger.
> - **Error**: All 9 `crossbar-v1` non-idealities + Chapter 0021 post-ADC output calibration.

Run the deterministic ledger generator:
```bash
python book/0026-calibration/architecture_ledger.py
```
Output committed at: `verification/circuit/results/architecture-ledger-0026-extract.json`.
Tested by: [`tests/test_architecture_ledger.py`](../../tests/test_architecture_ledger.py).
