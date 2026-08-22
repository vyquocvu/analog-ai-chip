# 0065 — Dynamic Power Grid Resonance & Electromigration Signoff (Gate R16 Closure)

> **Bản tiếng Việt:** [`README.vi.md`](README.vi.md)

This chapter concludes **Gate R16 (Post-Layout Parasitic Extraction & Static Timing Signoff)** by evaluating **RLC power distribution network (PDN) resonance frequencies**, quantifying **simultaneous switching noise (SSN / $L \cdot di/dt$)**, executing **copper electromigration (EM) lifetime verification via Black's equation**, and formally signing off Gate R16.

---

## 1. RLC Power Distribution Network (PDN) Impedance Profile

![Dynamic Power Grid Signoff](diagrams/dynamic-power-em.svg)
![PDN Impedance Spectrum](diagrams/power-grid-impedance.svg)

- **Anti-Resonance Frequency Isolation**:
  - On-chip decoupling capacitance ($C_{\text{decap}} = 450.0\text{ pF}$ per cluster).
  - Power mesh loop inductance ($L_{\text{grid}} = 4.2\text{ pH}$).
  - Natural RLC resonance frequency:
    $$f_{\text{res}} = \frac{1}{2\pi \sqrt{L_{\text{grid}} \cdot C_{\text{decap}}}} = \mathbf{3.66\text{ GHz}}$$
  - **Frequency Margin Ratio**: **$3.66\times$** above the fundamental NoC clock frequency ($1.0\text{ GHz}$), preventing parametric harmonic excitation and resonant supply collapse.

---

## 2. Simultaneous Switching Noise (SSN) & Inductive Bounce ($L \cdot di/dt$)

| Noise Component | Analytical Model | Physical Value | Verification Budget | Status |
|---|---|---|---|---|
| **Package Loop Inductance** | $L_{\text{pkg\_eff}} = L_{\text{bump}} / N_{\text{pwr}}$ | $1.50\text{ pH}$ | FCBGA-676 Power Grid | ✓ PASS |
| **Peak Transient Switching** | $\Delta I / \Delta t$ | $0.80\text{ A} / 100\text{ ps}$ | Synchronous NoC Clock Edge | ✓ PASS |
| **Inductive Package Bounce**| $V_L = L \cdot (di/dt)$ | **$12.00\text{ mV}$** | $\le 40.0\text{ mV}$ | ✓ PASS |
| **Static Resistive IR Drop**| $\Delta V_{\text{IR}}$ (Chapter 0061) | **$0.51\text{ mV}$** | $\le 30.0\text{ mV}$ | ✓ PASS |
| **Total Dynamic Voltage Drop**| $\Delta V_{\text{dynamic}} = V_L + \Delta V_{\text{IR}}$ | **$12.51\text{ mV}$ ($1.25\%$)**| $\mathbf{\le 50.0\text{ mV}}$ ($\pm 5.0\%\ V_{\text{DD}}$) | **✓ PASS** |

---

## 3. Electromigration (EM) Reliability via Black's Equation

Copper interconnect lifetime is modeled across the operating temperature envelope ($T_{\text{junc}} = 105^\circ\text{C}$):

$$\text{MTTF} = A \cdot J^{-2} \exp\left(\frac{E_a}{k_B T}\right)$$

| EM Parameter | Foundry Rule / Limit | Operating Layout Value | Reliability Margin |
|---|---|---|---|
| **Peak Current Density ($J$)** | $1.50\text{ mA}/\mu\text{m}$ (28nm BEOL Limit) | **$0.42\text{ mA}/\mu\text{m}$** (M6 Power Trunk) | **$3.57\times$ Safety Margin** |
| **Copper Activation Energy ($E_a$)** | $0.90\text{ eV}$ | $0.90\text{ eV}$ | Standard Cu Damascene |
| **Operating Junction Temp ($T_{\text{junc}}$)**| $105.0^\circ\text{C}$ ($378.15\text{ K}$) | $105.0^\circ\text{C}$ | Worst-Case Thermal Profile |
| **Projected Mean Time to Failure** | $\ge 10.0\text{ Years}$ | **$25.5\text{ Years}$** | **$2.55\times$ Lifetime Budget** |

---

## 4. Gate R16 Signoff Matrix & Closure

| Work Package | Chapter Title | Verification Scope | Status |
|---|---|---|---|
| **WP16.1** | [0063: PEX / SPEF & Crossbar Settling](file:///Users/vyquocvu/Develop/analog-ai-chip/book/0063-post-layout-parasitic-extraction/) | SPEF RC extraction, $t_{\text{settle}} = 2.45\text{ ns} \le 5.0\text{ ns}$ ADC aperture | **✓ PASSED** |
| **WP16.2** | [0064: Multi-Corner PVT STA Signoff](file:///Users/vyquocvu/Develop/analog-ai-chip/book/0064-multi-corner-sta-signoff/) | TT/SS/FF timing signoff, $\text{WNS} = 0.0\text{ ps}$, $\text{TNS} = 0.0\text{ ps}$ | **✓ PASSED** |
| **WP16.3** | [0065: Dynamic Power Grid & EM Signoff](file:///Users/vyquocvu/Develop/analog-ai-chip/book/0065-dynamic-power-grid-em-signoff/) | $f_{\text{res}} = 3.66\text{ GHz}$, $\Delta V_{\text{dyn}} = 12.51\text{ mV}$, $\text{MTTF} = 25.5\text{ yr}$ | **✓ PASSED** |
| **GATE R16** | **Post-Layout Parasitic Extraction & Static Timing Signoff** | **Full Interconnect RC, PVT Timing & EM Signoff** | **✓ PASSED (CLOSED)** |

---

## 5. Execution & Artifacts

Run the standalone chapter verification script:
```bash
python book/0065-dynamic-power-grid-em-signoff/power_em_signoff.py
```

Run test suite:
```bash
pytest tests/test_layout_dynamic_em.py
```

Deterministic extract artifact:
`verification/layout/results/dynamic-power-em-0065-extract.json`
