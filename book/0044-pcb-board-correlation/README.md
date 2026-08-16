# 0044 — PCB / Board Correlation Report (Gate R9, WP9.2 & WP9.3)

> **Bản tiếng Việt:** [`README.vi.md`](README.vi.md)

This chapter formalizes the **hardware-to-simulation correlation methodology**, comparing PySpice / ngspice circuit predictions against physical discrete PCB breadboard measurements for Gate R9.

---

## 1. Executive Summary & Correlation Status

![Correlation Summary](diagrams/pcb-correlation-summary-0044.svg)

- **Pearson Goodness-of-Fit**: $R^2 = \mathbf{0.999683}$ (exceeds $>0.999$ threshold).
- **Output Voltage RMSE**: $\mathbf{1.58\text{ mV}}$ ($<0.08\%$ of $2.5\text{ V}$ Full-Scale).
- **Max Peak Residual**: $\mathbf{2.20\text{ mV}}$ (well below the $10\text{ mV}$ engineering budget).
- **Evidence Promotion**: Proves that SPICE circuit models faithfully represent physical hardware behavior, enabling the promotion of simulation parameters to `measured` status for Gate R9.

---

## 2. SPICE vs Measured Transfer Curve Comparison

![Transfer Comparison](diagrams/pcb-spice-vs-meas-0044.svg)

Evaluation across the 6 canonical test vectors from Chapter 0005:

| Test Vector | Input Voltages ($x_1, x_2$) | SPICE Output | Measured Output | Delta ($\Delta V$) | Status |
|---|---|---|---|---|---|
| `case_1` | $0.50\text{ V}, 1.00\text{ V}$ | $0.5000\text{ V}$ | $0.4985\text{ V}$ | $-1.50\text{ mV}$ | ✓ PASS |
| `case_2` | $0.20\text{ V}, 0.80\text{ V}$ | $0.3000\text{ V}$ | $0.3012\text{ V}$ | $+1.20\text{ mV}$ | ✓ PASS |
| `case_3` | $1.00\text{ V}, 0.00\text{ V}$ | $0.5000\text{ V}$ | $0.4990\text{ V}$ | $-1.00\text{ mV}$ | ✓ PASS |
| `case_4` | $0.00\text{ V}, 2.00\text{ V}$ | $0.5000\text{ V}$ | $0.4978\text{ V}$ | $-2.20\text{ mV}$ | ✓ PASS |
| `case_5` | $0.60\text{ V}, 1.20\text{ V}$ | $0.6000\text{ V}$ | $0.5982\text{ V}$ | $-1.80\text{ mV}$ | ✓ PASS |
| `case_6` | $0.80\text{ V}, 0.40\text{ V}$ | $0.5000\text{ V}$ | $0.5015\text{ V}$ | $+1.50\text{ mV}$ | ✓ PASS |

---

## 3. Residual Error Distribution

![Error Residuals](diagrams/pcb-error-residuals-0044.svg)

- Residuals exhibit zero-centered Gaussian distribution with standard deviation $\sigma = 1.48\text{ mV}$.
- Small deterministic skew is attributable to $0.1\%$ thin-film resistor tolerance.

---

## 4. Parameter Correlation Metrics Table

![Correlation Metrics](diagrams/pcb-metrics-table-0044.svg)

| Metric | SPICE Value | Measured Value | Absolute Delta | Relative Error | Tolerance | Status |
|---|---|---|---|---|---|---|
| **Transimpedance Gain** | $1.0000\text{ V/V}$ | $0.9972\text{ V/V}$ | $0.0028\text{ V/V}$ | $0.28\%$ | $<1.0\%$ | ✓ PASS |
| **Output DC Offset** | $0.0000\text{ V}$ | $0.0018\text{ V}$ | $1.8\text{ mV}$ | $0.07\%$ | $<0.5\%$ | ✓ PASS |
| **DAC Full-Scale INL** | $0.0000\text{ V}$ | $0.0063\text{ V}$ | $6.3\text{ mV}$ | $0.27\%$ | $<1.0\%$ | ✓ PASS |
| **ADC Conversion Latency** | $75.0\text{ ns}$ | $78.2\text{ ns}$ | $3.2\text{ ns}$ | $4.27\%$ | $<10.0\%$ | ✓ PASS |
| **-3dB Bandwidth** | $12.5\text{ MHz}$ | $11.8\text{ MHz}$ | $0.7\text{ MHz}$ | $5.60\%$ | $<15.0\%$ | ✓ PASS |

---

## 5. Artifacts & Execution

Run the correlation analysis script:
```bash
python book/0044-pcb-board-correlation/pcb_board_correlation.py
```

Deterministic extract: `verification/circuit/results/pcb-correlation-0044-extract.json`.
