# 0062 — Top-Level Monolithic Full-Chip Assembly & Gate R15 Signoff

> **Bản tiếng Việt:** [`README.vi.md`](README.vi.md)

This chapter concludes **Gate R15 (Physical Layout & DRC/LVS Verification)** by executing the **top-level physical assembly of the complete monolithic silicon die** ($18.334\text{ mm} \times 18.334\text{ mm} = 336.14\text{ mm}^2$), routing the **2D mesh NoC backbone**, placing the **FCBGA-676 flip-chip I/O pad ring with integrated ESD clamps**, building the **global balanced clock H-tree**, and achieving formal **Gate R15 exit signoff**.

---

## 1. Monolithic Die Floorplan & Compute Cluster Hierarchy

![Top-Level Full-Chip Assembly](diagrams/full-chip-assembly.svg)
![Monolithic Full-Chip Layout Mask](diagrams/full-chip-mask.svg)

- **Monolithic Single-Die Integration**:
  - **Tape-Out Target**: `T0_GPT2_124M` analog accelerator on 28nm BEOL Via4-M5 ReRAM.
  - **Die Dimensions**: $18.334\text{ mm} \times 18.334\text{ mm}$ (**$336.14\text{ mm}^2$**, within the $\le 400.0\text{ mm}^2$ reticle budget).
  - **Compute Cluster Hierarchy**: $4 \times 4$ array of major TPU compute clusters interconnected by a high-throughput 2D mesh on-chip network (NoC) on Metal 7.
  - **Seal Ring & Scribe Line**: $100\ \mu\text{m}$ perimeter stress-relief seal ring protecting active circuitry against dicing micro-cracks and moisture penetration.

---

## 2. FCBGA-676 Flip-Chip I/O Pad Ring & ESD Clamps

| Parameter | Specification | Physical Implementation | Verification Status |
|---|---|---|---|
| **Package Type** | FCBGA-676 ($21.0\text{ mm} \times 21.0\text{ mm}$) | $26 \times 26$ Flip-Chip BGA Grid | ✓ PASS |
| **Bump Pitch / Size** | $650\ \mu\text{m}$ pitch / $120\ \mu\text{m}$ diameter | Metal 8 Octagonal Opening | ✓ PASS |
| **I/O Protocols** | PCIe Gen5 x8 Host, LPDDR5/HBM, JTAG | 276 Peripheral Bump Pads | ✓ PASS |
| **ESD HBM Rating** | $\ge 2.0\text{ kV}$ Human Body Model | Dual-Diode + ggNMOS Snapback Clamp | ✓ PASS ($> 2.0\text{ kV}$) |
| **ESD CDM Rating** | $\ge 500\text{ V}$ Charged Device Model | Low-Capacitance RC-Triggered Clamp | ✓ PASS ($> 500\text{ V}$) |

---

## 3. Global Balanced Clock H-Tree Network

To distribute the system clock ($1.0\text{ GHz}$ NoC / $50\text{ MHz}$ IMC sample clock) across the $18.3\text{ mm}$ die with minimal phase variance:

- **Topology**: Symmetric 4-level balanced H-tree routed on thick top-metal **Metal 8**.
- **Global Clock Skew**: **$11.4\text{ ps}$** (Significantly below the signoff budget of $\le 15.0\text{ ps}$).
- **Shielding**: Differential coplanar clock traces bounded by grounded $V_{\text{SS}}$ shield lines to eliminate cross-talk jitter.

---

## 4. Gate R15 Comprehensive Signoff Matrix

| Work Package | Chapter & Milestone Title | Key Evidence & Metric | Signoff Status |
|---|---|---|---|
| **WP15.1** | 0059: 28nm BEOL ReRAM Macro Layout & DRC | $16 \times 16$ array, $160\text{ nm}$ pitch, 1,008 checks, 0 violations | **✓ PASSED** |
| **WP15.2** | 0060: Mixed-Signal SAR ADC / DAC Layout & LVS | 2D common-centroid, $0.0\text{ nm}$ offset, 258 devices, 0 discrepancies | **✓ PASSED** |
| **WP15.3** | 0061: Core Tile Floorplan & Power Grid IR Drop | $3,283.3\ \mu\text{m}^2$ ($100.1\%$ match), $\Delta V_{\text{IR}} = 0.51\text{ mV} \le 30\text{ mV}$ | **✓ PASSED** |
| **WP15.4** | 0062: Top-Level Full-Chip Monolithic Assembly | $336.14\text{ mm}^2$, FCBGA-676, ESD $> 2\text{ kV}$, clock skew $11.4\text{ ps}$ | **✓ PASSED** |
| **GATE R15** | **Physical Layout & DRC/LVS Verification** | **Zero DRC Violations, Zero LVS Discrepancies** | **✓ PASSED (CLOSED)** |

---

## 5. Execution & Artifacts

Run the standalone chapter verification script:
```bash
python book/0062-top-level-chip-assembly/full_chip_assembly.py
```

Run test suite:
```bash
pytest tests/test_layout_full_chip.py
```

Deterministic extract artifact:
`verification/layout/results/full-chip-0062-extract.json`
