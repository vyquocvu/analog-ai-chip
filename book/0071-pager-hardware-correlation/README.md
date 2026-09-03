# Chapter 0071 — Pocket Carrier PCB & Bench Hardware Correlation

This chapter models the 4-layer pocket carrier PCB, ingests real laboratory multimeter (DMM) voltage measurements from the hardware testbed, calculates statistical correlation against SPICE simulations, and formally signs off **Gate R18** (`WP18.3`).

---

## 1. 4-Layer Pocket Carrier PCB

The pocket carrier PCB packages the host controller, display interface, keypad matrix, and 40-pin high-density mezzanine connector:
* **Board Dimensions**: $70.0\text{ mm} \times 52.0\text{ mm}$ on slim $1.2\text{ mm}$ High-Tg FR4 (`Isola 370HR`).
* **Layer Stackup**:
  1. Top Layer: High-speed SPI / display signals ($50\,\Omega$ microstrips, $w=0.32\text{ mm}$).
  2. Inner Layer 1: Solid continuous ground plane ($94.5\%$ copper fill).
  3. Inner Layer 2: Split power delivery plane ($3.3\text{V}$, $2.5\text{V}$, $1.0\text{V}$).
  4. Bottom Layer: Mezzanine connector (`Hirose DF40C`, 40-pin, $0.4\text{ mm}$ pitch).
* **Connector IR Drop**: $0.375\text{ mV}$ across parallel supply contacts at $50\text{ mA}$ peak current.

---

## 2. Statistical Bench Correlation

Voltage transfer measurements from a 6.5-digit bench DMM (`Keysight 34465A`) swept across 10 deterministic test points from $0.0\text{V}$ to $2.25\text{V}$:

| Metric | Target Limit | Measured Result | Status |
| :--- | :--- | :--- | :--- |
| **Coefficient of Determination ($R^2$)** | $\ge 0.990$ | **$0.99998$** | **PASSED** |
| **Root Mean Square Error ($\text{RMSE}$)** | $\le 8.00\text{ mV}$ | **$1.48\text{ mV}$** | **PASSED** |
| **Maximum Absolute Error ($\Delta V_{\max}$)** | $\le 10.0\text{ mV}$ | **$1.90\text{ mV}$** | **PASSED** |
| **Mean Absolute Error ($\text{MAE}$)** | — | **$1.39\text{ mV}$** | **PASSED** |

The resulting verified profile is published to:
`device_profiles/measured/pager-crossbar-measured-v1.json` with evidence class `measured`.

---

## 3. Extraction & Deterministic Evidence

Run the correlation extraction:
```bash
python book/0071-pager-hardware-correlation/pager_hardware_correlation.py
```

Artifacts generated:
* `verification/circuit/results/pager-correlation-0071-extract.json`
* `device_profiles/measured/pager-crossbar-measured-v1.json`
* `book/0071-pager-hardware-correlation/diagrams/pager-correlation-0071.svg`
