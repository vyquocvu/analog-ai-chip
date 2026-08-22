# 0066 — GDSII / OASIS Stream-Out & 28nm Foundry Tape-Out Signoff (Gate R17)

> **Bản tiếng Việt:** [`README.vi.md`](README.vi.md)

This chapter opens **Gate R17 (Tape-Out Signoff & Package/PCB Integration)** by executing **CMP dummy metal fill synthesis**, validating **inter-layer density gradients**, streaming out the **binary GDSII/OASIS mask archive**, and achieving formal signoff across the **10-point 28nm foundry tape-out checklist**.

---

## 1. 28nm BEOL GDSII / OASIS Layer Mapping & Mask Synthesis

![28nm Foundry Tape-Out Signoff](diagrams/tapeout-signoff.svg)

- **GDSII / OASIS Layer Map Allocation**:
  - **Metal 1–3**: Layers 1–3 (Logic standard cells & 6T SRAM bitcell routing).
  - **Metal 4 (Wordlines)**: Layer 4 ($60\text{ nm}$ horizontal lines, pitch $160\text{ nm}$).
  - **Via4_RERAM**: Layer 24 ($32\text{ nm} \times 32\text{ nm}$ active oxide switching aperture).
  - **Metal 5 (Bitlines)**: Layer 5 ($60\text{ nm}$ vertical lines, pitch $160\text{ nm}$).
  - **Metal 6 (Power Grid)**: Layer 6 ($600\text{ nm}$ horizontal $V_{\text{DD}}/V_{\text{SS}}$ power straps).
  - **Metal 7 (NoC Interconnect)**: Layer 7 (2D Mesh packet routing channels).
  - **Metal 8 (Top Metal)**: Layer 8 (Clock H-tree, global power ring, FCBGA I/O pads).
  - **Seal Ring Guard Boundary**: Layer 99 ($100\ \mu\text{m}$ stress-relief scribe-line perimeter).

---

## 2. Chemical-Mechanical Planarization (CMP) Dummy Metal Fill

![CMP Dummy Metal Fill](diagrams/dummy-metal-fill.svg)

To satisfy foundry manufacturing rules and prevent dishing/erosion during chemical-mechanical polishing (CMP), staggered floating dummy tiles are inserted into sparse layout regions:

| Metallization Layer | Pre-Fill Density | Post-Fill Density | Spatial Gradient ($\Delta \rho / 50\ \mu\text{m}$) | Foundry Rule Compliance |
|---|---|---|---|---|
| **Metal 1 (Logic Routing)** | $14.2\%$ | **$41.5\%$** | $3.8\%$ | ✓ $20\% \le \rho \le 80\%$, $\Delta \rho \le 15\%$ |
| **Metal 4 (ReRAM Wordlines)** | $37.5\%$ | **$48.2\%$** | $4.1\%$ | ✓ $20\% \le \rho \le 80\%$, $\Delta \rho \le 15\%$ |
| **Metal 5 (ReRAM Bitlines)** | $37.5\%$ | **$48.2\%$** | $4.1\%$ | ✓ $20\% \le \rho \le 80\%$, $\Delta \rho \le 15\%$ |
| **Metal 6 (Power Straps)** | $22.8\%$ | **$43.6\%$** | $4.5\%$ | ✓ $20\% \le \rho \le 80\%$, $\Delta \rho \le 15\%$ |
| **Metal 7 (NoC Channels)** | $18.4\%$ | **$39.2\%$** | $4.0\%$ | ✓ $20\% \le \rho \le 80\%$, $\Delta \rho \le 15\%$ |
| **Metal 8 (Clock & Pads)** | $12.1\%$ | **$35.8\%$** | $4.8\%$ | ✓ $20\% \le \rho \le 80\%$, $\Delta \rho \le 15\%$ |
| **Full Chip Average** | **$23.8\%$** | **$42.5\%$** | **$4.2\%$** | ✓ **100% CMP COMPLIANT** |

---

## 3. 10-Point Master Foundry Tape-Out Signoff Checklist

| # | Signoff Gate | Category | Foundry Specification | Physical Layout Audit | Verdict |
|---|---|---|---|---|---|
| **1** | **DRC Clean** | Physical Verification | 0 violations across 1,008 rules | 0 violations (100% clean) | ✓ PASS |
| **2** | **LVS Match** | Physical Verification | 0 device/net/port discrepancies | 258/258 devices, 14/14 ports | ✓ PASS |
| **3** | **ERC / Antenna** | Reliability | Antenna ratio $\le 250:1$ | Max ratio 48:1 (0 violations) | ✓ PASS |
| **4** | **PEX / SPEF** | Signal Integrity | Crossbar settling $t_{\text{settle}} \le 5.0\text{ ns}$ | 291 nets, $t_{\text{settle}} = 2.45\text{ ns}$ ($2.04\times$) | ✓ PASS |
| **5** | **STA Timing** | Timing Signoff | $\text{WNS} \ge 0.0\text{ ps}, \text{TNS} = 0.0\text{ ps}$ | $\text{WNS} = 0.0\text{ ps}$, CDC MTBF $> 10^9\text{ yr}$ | ✓ PASS |
| **6** | **Dynamic PDN** | Power Integrity | $f_{\text{res}} > 2.5\text{ GHz}, \Delta V \le 50\text{ mV}$ | $f_{\text{res}} = 3.66\text{ GHz}, \Delta V = 12.51\text{ mV}$ | ✓ PASS |
| **7** | **EM Black's Rule**| Reliability | $J \le 1.50\text{ mA}/\mu\text{m}, \text{MTTF} \ge 10\text{ yr}$| $J = 0.42\text{ mA}/\mu\text{m}$, $\text{MTTF} = 25.5\text{ yr}$ | ✓ PASS |
| **8** | **ESD Protection** | I/O & Packaging | $> 2.0\text{ kV}$ HBM / $> 500\text{ V}$ CDM | $2.2\text{ kV}$ HBM / $650\text{ V}$ CDM clamps | ✓ PASS |
| **9** | **CMP Dummy Fill** | DFM Planarity | $20\% \le \rho \le 80\%, \Delta \rho \le 15\%$ | Avg $\rho = 42.5\%, \Delta \rho = 4.2\%$ | ✓ PASS |
| **10**| **Reticle Seal Ring**| Foundry Interface | $100\ \mu\text{m}$ seal ring, valid SHA-256 | Integrated ring, SHA-256 verified | ✓ PASS |

---

## 4. Physical Tape-Out Decision & Shuttle Stream-Out Package

- **Tape-Out Target**: `T0_GPT2_124M` Monolithic Silicon Die ($18.334\text{ mm} \times 18.334\text{ mm} = 336.14\text{ mm}^2$).
- **Foundry Multi-Project Shuttle**: TSMC 28nm HPC+ CyberShuttle.
- **Stream-Out Archive Format**: IEEE GDSII v6.0 / OASIS v1.0.
- **Binary Integrity Checksum**: SHA-256 authenticated stream-out bundle.

---

## 5. Execution & Artifacts

Run the standalone chapter verification script:
```bash
python book/0066-gdsii-streamout-tapeout-signoff/gdsii_tapeout_signoff.py
```

Run test suite:
```bash
pytest tests/test_layout_tapeout.py
```

Deterministic extract artifact:
`verification/layout/results/tapeout-0066-extract.json`
