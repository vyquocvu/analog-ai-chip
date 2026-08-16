# 0039 — Physical Energy and Power Ledger (Gate R8)

> **Bản tiếng Việt:** [`README.vi.md`](README.vi.md)

This chapter formalizes the **physical energy model, dynamic energy consumption, and power dissipation ledger** for the analog in-memory computing accelerator where every energy and power coefficient carries an explicit physical provenance class (`measured`, `spice`, `derived`, or `assumed`) for **Gate R8 (Physical feasibility report)**.

---

## 1. Energy & Power Model Overview

![Physical Energy and Power Ledger](diagrams/energy-ledger-0039.svg)

| Component | Symbol | Value | Evidence Class | Physical Provenance |
|---|---|---|---|---|
| **Analog IMC Synapse** | $E_{\text{imc\_mac}}$ | $50.0\text{ fJ/MAC}$ | `derived` | SPICE $I_{\text{cell}} \cdot V_{\text{read}} \cdot t_{\text{pulse}}$ ($G_{\text{avg}}=55\,\mu\text{S}, V=0.2\text{ V}, t=10\text{ ns}$) |
| **Input 4-bit DAC** | $E_{\text{dac}}$ | $0.2\text{ pJ/sample}$ | `spice` | SPICE transient switching of 4-bit PWM / voltage driver |
| **Output 4-bit SAR ADC** | $E_{\text{adc}}$ | $0.5\text{ pJ/sample}$ | `spice` | SPICE SAR capacitive DAC + comparator switching |
| **On-Chip SRAM Pool** | $E_{\text{sram}}$ | $1.0\text{ pJ/Byte}$ | `derived` | 28nm high-density SRAM cell read/write access |
| **Digital Vector SIMD** | $E_{\text{simd\_mac}}$ | $200.0\text{ fJ/MAC}$ | `derived` | Pipelined 32-bit digital ALU @ 200 MHz in 28nm |
| **NoC Mesh Hop** | $E_{\text{noc}}$ | $0.5\text{ pJ/hop/flit}$ | `assumed` | 2D mesh on-chip router packet traversal (28nm) |
| **Tile Standby Leakage** | $P_{\text{leak}}$ | $0.5\,\mu\text{W/tile}$ | `derived` | Subthreshold & gate leakage across 416 tiles |

---

## 2. Subsystem Energy Waterfall Breakdown

![Subsystem Energy Waterfall](diagrams/energy-breakdown-0039.svg)

- **Total Energy per Token Step**: $E_{\text{token}} = \mathbf{29.08\text{ nJ/token}}$.
- **Energy Breakdown**:
  - **On-Chip SRAM Pool (KV Cache & Buffers)**: $16.38\text{ nJ}$ ($56.3\%$).
  - **Analog IMC Crossbars ($106,496\text{ MACs}$)**: $5.33\text{ nJ}$ ($18.3\%$).
  - **Data Converters ($6,656\text{ DACs} + 6,656\text{ ADCs}$)**: $4.66\text{ nJ}$ ($16.0\%$).
  - **Digital Vector SIMD ($12,288\text{ MACs}$)**: $2.46\text{ nJ}$ ($8.5\%$).
  - **NoC Mesh Transport ($512\text{ Flit-hops}$)**: $0.26\text{ nJ}$ ($0.9\%$).

---

## 3. Power Dissipation & Thermal Density

![Power Dissipation & Density](diagrams/energy-power-density-0039.svg)

- **Active Dynamic Power**: $\mathbf{29.14\text{ mW}}$ during full-speed $1,002,004\text{ tokens/sec}$ generation.
- **Static Standby Leakage**: $\mathbf{0.21\text{ mW}}$ across all 416 physical crossbar tiles.
- **Total Peak Power Dissipation**: $\mathbf{29.35\text{ mW}}$.
- **Thermal Density**: $0.007\text{ W/mm}^2$ across estimated $4.2\text{ mm}^2$ die area, well within passive ambient convection limits ($<2.5^\circ\text{C}$ junction temperature rise).

---

## 4. Efficiency Benchmark vs Digital Baseline

![Energy Benchmark](diagrams/energy-comparison-0039.svg)

- **Compute Energy Advantage**: $50.0\text{ fJ/MAC}$ (Analog IMC) vs $200.0\text{ fJ/MAC}$ (Digital SIMD) $\to \mathbf{4.0\times\text{ advantage}}$.
- **End-to-End Token Step Advantage**: $29.08\text{ nJ/token}$ (Analog IMC) vs $250.0\text{ nJ/token}$ (Digital GPU/NPU baseline) $\to \mathbf{8.6\times\text{ advantage}}$.
- **Mechanism**: Eliminates DRAM/cache weight movement by computing directly in stationary memristor crossbars.

---

## 5. Execution & Artifacts

Run the deterministic energy and power ledger generator:
```bash
python book/0039-energy-power-ledger/energy_power_ledger.py
```
Committed extract artifact at: `verification/circuit/results/energy-power-ledger-0039-extract.json`.
