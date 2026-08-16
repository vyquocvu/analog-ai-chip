# 0040 — Physical Area and Process Model (Gate R8)

> **Bản tiếng Việt:** [`README.vi.md`](README.vi.md)

This chapter formalizes the **physical area model and process-node floorplan** for the analog in-memory computing accelerator where every area coefficient carries an explicit physical provenance class (`derived` or `assumed`) in **28nm CMOS** for **Gate R8 (Physical feasibility report)**.

---

## 1. Area Coefficients & Provenance

![Area and Process Model](diagrams/area-process-model-0040.svg)

| Component | Symbol | Value | Evidence Class | Physical Provenance |
|---|---|---|---|---|
| **Memristor Bit Cell** | $A_{\text{cell}}$ | $0.0064\,\mu\text{m}^2$ | `derived` | 28nm 1T1R memristor: $80\text{ nm} \times 80\text{ nm}$ cell + 1T access transistor |
| **16×18 Crossbar Core** | $A_{\text{xbar}}$ | $11.52\,\mu\text{m}^2$ | `derived` | 288 bit cells with routing pitch |
| **4-bit Input DAC** | $A_{\text{dac}}$ | $25.0\,\mu\text{m}^2$ | `assumed` | 4-bit R-2R / PWM driver (28nm standard cell chain) |
| **4-bit SAR ADC + TIA** | $A_{\text{adc}}$ | $150.0\,\mu\text{m}^2$ | `assumed` | SAR ADC + transimpedance amplifier (28nm published scaling) |
| **Affine Calibration ALU** | $A_{\text{alu}}$ | $80.0\,\mu\text{m}^2$ | `derived` | 16-wide 8-bit $\alpha \cdot y + \beta$ ALU (28nm synthesis) |
| **Calibration SRAM** | $A_{\text{cal\_sram}}$ | $40.0\,\mu\text{m}^2$ | `derived` | 16-entry $\times$ 16-bit coefficient register file |
| **32 KB SRAM Macro** | $A_{\text{sram32}}$ | $40,000\,\mu\text{m}^2$ | `derived` | 28nm standard-density SRAM macro ($0.22\,\mu\text{m}^2$/bit) |
| **32-wide SIMD Cluster** | $A_{\text{simd}}$ | $5,000\,\mu\text{m}^2$ | `assumed` | Pipelined 32-bit integer ALU (28nm synthesis estimate) |
| **2D NoC Router** | $A_{\text{noc}}$ | $2,000\,\mu\text{m}^2$ | `assumed` | 5-port 128-bit flit mesh router (28nm) |

---

## 2. Single Tile Area Breakdown

![Tile Area Breakdown](diagrams/area-tile-breakdown-0040.svg)

- **Single Tile Area**: $3,281.5\,\mu\text{m}^2$ total per tile.
- **ADC Bank Dominates**: The $18\times$ SAR ADC + TIA bank occupies $\mathbf{82.2\%}$ of tile area. ADC miniaturization is the primary area scaling lever for future process nodes.
- **Crossbar Core**: Only $11.52\,\mu\text{m}^2$ ($0.35\%$ of tile) — the memristor array itself is very compact; peripheral circuits dominate.

---

## 3. Chip-Level Floorplan (28nm CMOS)

![Chip Floorplan](diagrams/area-floorplan-0040.svg)

| Block | Area (mm²) | Fraction | Evidence |
|---|---|---|---|
| **416-Tile Crossbar Array** | $1.365\text{ mm}^2$ | $96.7\%$ | derived |
| **Shared 32 KB SRAM Macro** | $0.0400\text{ mm}^2$ | $2.8\%$ | derived |
| **SIMD Vector Cluster** | $0.0050\text{ mm}^2$ | $0.35\%$ | assumed |
| **NoC Router Fabric** | $0.0020\text{ mm}^2$ | $0.14\%$ | assumed |
| **Total Die Area** | $\mathbf{1.412\text{ mm}^2}$ | $100\%$ | — |

---

## 4. Area Efficiency & Scaling Analysis

![Area Scaling Analysis](diagrams/area-scaling-0040.svg)

- **Synapse Packing Density**: $119,808\text{ synapses}$ across $1.412\text{ mm}^2$ die.
- **Compute Throughput Density**: $\mathbf{75.6\text{ GOPS/mm}^2}$ at $1.002\text{M tokens/sec}$.
- **ADC Scaling Sensitivity**: Each additional bit of ADC resolution adds $\approx 60\,\mu\text{m}^2$ per unit. 4-bit is the Pareto-optimal operating point for area–SNR tradeoff at this tile pitch (cross-referenced with Chapter 0036).

---

## 5. Execution & Artifacts

Run the deterministic area model generator:
```bash
python book/0040-area-process-model/area_process_model.py
```
Committed extract artifact at: `verification/circuit/results/area-process-model-0040-extract.json`.
