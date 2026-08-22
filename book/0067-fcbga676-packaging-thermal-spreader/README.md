# 0067 — FCBGA-676 Substrate Packaging & Thermal Heat Spreader (Gate R17)

> **Bản tiếng Việt:** [`README.vi.md`](README.vi.md)

This chapter advances **Gate R17 (Tape-Out Signoff & Package/PCB Integration)** by formalizing the **FCBGA-676 flip-chip packaging substrate**, routing the **4-2-4 organic buildup layer stackup**, allocating the **$26 \times 26$ BGA ball map**, and verifying the **integrated nickel-plated copper heat spreader** under peak $23.2\text{ W}$ TDP workload.

---

## 1. FCBGA-676 Package Architecture & C4 Bump Matrix

![FCBGA-676 Packaging](diagrams/fcbga676-packaging.svg)

- **Flip-Chip Package Dimensions**:
  - **Body Dimensions**: $27.0\text{ mm} \times 27.0\text{ mm}$ ($1.00\text{ mm}$ BGA ball pitch).
  - **Silicon Die Assembly**: $18.334\text{ mm} \times 18.334\text{ mm}$ ($336.14\text{ mm}^2$ monolithic die).
  - **C4 Micro-Bump Matrix**: $1,296\text{ solder micro-bumps}$ at $150\ \mu\text{m}$ pitch on top organic buildup layer.
  - **Underfill Encapsulant**: High-modulus epoxy underfill mitigating coefficient of thermal expansion (CTE) mismatch between silicon ($2.6\text{ ppm/K}$) and organic substrate ($15.0\text{ ppm/K}$).

---

## 2. 4-2-4 Organic Buildup Substrate Stackup

![Substrate Stackup and Thermal Network](diagrams/substrate-stackup-thermal.svg)

| Layer Index | Layer Function | Copper Thickness | Dielectric Thickness | Impedance Role |
|---|---|---|---|---|
| **L1 (Top)** | C4 Bump Pads / Microstrip | $15\ \mu\text{m}$ | $30\ \mu\text{m}$ | High-density escape routing |
| **L2** | $V_{\text{SS}}$ Reference Plane | $15\ \mu\text{m}$ | $30\ \mu\text{m}$ | Return current shielding |
| **L3** | Stripline Signals (PCIe Gen5) | $15\ \mu\text{m}$ | $30\ \mu\text{m}$ | $85.0\ \Omega$ Differential ($32\text{ GT/s}$) |
| **L4** | $V_{\text{DD\_DIG}}$ ($0.9\text{V}$) Plane | $15\ \mu\text{m}$ | $30\ \mu\text{m}$ | Low-impedance core power |
| **Core (L5-L6)**| Rigid Glass Core Plate | **$35\ \mu\text{m}$** | **$800\ \mu\text{m}$** | Mechanical rigidity & through-core vias |
| **L7** | $V_{\text{DD\_ANA}}$ ($1.0\text{V}$) Plane | $15\ \mu\text{m}$ | $30\ \mu\text{m}$ | Analog power distribution |
| **L8** | Stripline Memory Signals | $15\ \mu\text{m}$ | $30\ \mu\text{m}$ | $50.0\ \Omega$ Single-ended |
| **L9** | $V_{\text{SS}}$ Reference Plane | $15\ \mu\text{m}$ | $30\ \mu\text{m}$ | BGA ball shield |
| **L10 (Bottom)**| BGA Ball Pads ($1.0\text{ mm}$) | $15\ \mu\text{m}$ | Solder Mask | $676\text{ BGA ball landings}$ |

---

## 3. BGA Ball Map & Pin Allocation Matrix

| Signal Group | Ball Count | Voltage / Standard | Functional Description |
|---|---|---|---|
| **$V_{\text{SS}}$ Ground Shield** | $230\text{ balls}$ | $0.0\text{V}$ | Interleaved ground return & thermal dissipation |
| **$V_{\text{DD\_DIG}}$ Core Supply** | $140\text{ balls}$ | $0.90\text{V} \pm 5\%$ | Digital logic, NoC routers, SRAM buffers |
| **$V_{\text{DD\_ANA}}$ Analog Supply**| $90\text{ balls}$ | $1.00\text{V} \pm 5\%$ | ReRAM wordline drivers & SAR ADC converters |
| **PCIe Gen5 x16 SerDes** | $64\text{ balls}$ | $85.0\ \Omega\ \text{Diff}$ | Host interface ($32\text{ GT/s}$ per lane) |
| **LPDDR5 Memory Channels** | $96\text{ balls}$ | LPDDR5 JEDEC | Off-chip model weight streaming |
| **Control / JTAG / References** | $56\text{ balls}$ | $1.8\text{V}$ LVCMOS | JTAG boundary scan, PLL reference clock, $V_{\text{REF}}$ |
| **Total BGA Balls** | **$676\text{ Balls}$** | **$26 \times 26\text{ Grid}$** | **100% Fully Allocated** |

---

## 4. Passive Copper Thermal Heat Spreader & Junction Temperature Signoff

- **Heat Spreader Assembly**:
  - Nickel-plated Copper Integrated Heat Spreader (IHS, $k_{\text{Cu}} = 390\text{ W/m}\cdot\text{K}$).
  - High-performance TIM-1 interface: $k_{\text{TIM1}} = 6.50\text{ W/m}\cdot\text{K}$, bond line thickness $\text{BLT} = 35\ \mu\text{m}$.
- **Thermal Resistance Network**:
  $$\theta_{jc} = \frac{\text{BLT}}{k_{\text{TIM1}} \cdot A_{\text{die}}} + \theta_{\text{IHS}} = \mathbf{0.096^\circ\text{C}/\text{W}}$$
  $$\theta_{ja} = \theta_{jc} + \theta_{ca} = 0.096 + 1.520 = \mathbf{1.616^\circ\text{C}/\text{W}} \le 1.800^\circ\text{C}/\text{W}$$
- **Thermal Dissipation Signoff ($P_{\text{TDP}} = 23.2\text{ W}, T_{\text{ambient}} = 30.0^\circ\text{C}$)**:
  $$\mathbf{T_j = 30.0^\circ\text{C} + (23.2\text{ W} \times 1.616^\circ\text{C}/\text{W}) = 67.49^\circ\text{C}} \le 85.0^\circ\text{C}\ (\text{Thermal Headroom: } +17.51^\circ\text{C})$$

---

## 5. Execution & Artifacts

Run the standalone chapter verification script:
```bash
python book/0067-fcbga676-packaging-thermal-spreader/packaging_thermal_signoff.py
```

Run test suite:
```bash
pytest tests/test_layout_packaging.py
```

Deterministic extract artifact:
`verification/layout/results/packaging-0067-extract.json`
