# 0036 — Sensitivity and Quantization Trade-offs (Gate R7)

> **Bản tiếng Việt:** [`README.vi.md`](README.vi.md)

This chapter formalizes the **multi-dimensional sensitivity and quantization trade-off analysis** across converter bit precision ($2\dots 8$ bits), conductance resolution, and physical non-idealities for **Gate R7 (Transformer and LLM validation)**.

---

## 1. Multi-Dimensional Trade-off Overview

![Sensitivity and Quantization](diagrams/sensitivity-quantization-0036.svg)

- **Design Space Scope**: Explores the trade-offs between hardware cost (ADC/DAC energy and area) and language model inference fidelity (SNR, $L_2$ error, and perplexity) across $416$ physical crossbar tiles.
- **Pareto Operating Point**: Identifies the optimal trade-off boundary balancing energy-per-token against signal-to-noise ratio.

---

## 2. Converter & Conductance Bit-Precision Scaling

![Bit Precision Sweep](diagrams/sensitivity-bit-sweep-0036.svg)

- **2-bit to 4-bit**: Significant quantization noise where logit relative error ranges from $100\%$ to $111\%$.
- **5-bit to 6-bit**: The SNR rapidly climbs from $-0.89\text{ dB}$ ($5\text{-bit}$) to $-0.04\text{ dB}$ ($6\text{-bit}$), reducing perplexity from $129.6$ to $122.2$.
- **7-bit to 8-bit**: Reaches positive SNR ($+0.24\text{ dB}$) with high-fidelity logit reconstruction at the expense of doubling ADC conversion energy per bit.

---

## 3. Non-Ideality Parameter Sensitivity Radar

![Non-Idealities Sensitivity](diagrams/sensitivity-nonidealities-0036.svg)

Marginal sensitivity ranking across physical non-idealities:
1. **Stuck Defects ($p_{\text{stuck}} \in [0.1\%, 5.0\%]$)**: **Most critical**, causing $>80\%$ of total analog distortion. Requires column redundancy or defect-aware remapping in Chapter 0037.
2. **Programming Variation ($\sigma_{\text{prog}} \in [0.5\%, 8.0\%]$)**: High sensitivity; noise degrades SNR significantly if write-verify pulses are loose.
3. **2D Wire Resistance ($R_{\text{wire}} \in [0.1\,\Omega, 5.0\,\Omega]$)**: Moderate sensitivity; causes spatial voltage gradient across partial sum accumulation lines.
4. **Retention Drift ($t \in [1\text{ s}, 1\text{ year}]$)**: Low sensitivity due to slow logarithmic drift exponent ($\nu = 0.08$), making long-term inference viable without frequent refreshes.

---

## 4. Energy vs Accuracy Pareto Frontier

![Pareto Frontier](diagrams/sensitivity-pareto-frontier-0036.svg)

- **Energy-Accuracy Curve**: Compares total tile energy per token against logit reconstruction SNR.
- **Hardware Takeaway**: While 4-bit converters provide the lowest hardware energy floor ($58.6\text{ nJ/token}$), moving to 6-bit or 7-bit converters provides substantial noise margin improvements ($>0\text{ dB}$ SNR) while remaining well below standard digital SIMD baselines ($>25\text{ nJ/token}$).

---

## 5. Execution & Artifacts

Run the deterministic sensitivity and quantization study:
```bash
python book/0036-sensitivity-quantization/sensitivity_quantization.py
```
Committed extract artifact at: `verification/circuit/results/sensitivity-quantization-0036-extract.json`.
